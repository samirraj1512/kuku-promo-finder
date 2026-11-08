"""Swappable LLM client. One interface: complete(system, user, schema) -> validated pydantic object | None.

- OpenAI-compatible adapter (Groq, Gemini compat layer, Cerebras, OpenRouter, any custom base_url)
- provider 'stub' returns canned schema-valid JSON, so the whole pipeline runs with no key / no network
- disk cache keyed by (provider, model, rubric, prompt) -> reruns are free and runs are resumable
- token-bucket rate limit, backoff on 429/5xx, validation-error feedback retries, call budget, usage.csv
- never raises on bad model output: returns None and logs (caller falls back to rule score)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Type

from pydantic import BaseModel, ValidationError

PRESETS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def _stub_value(node: dict, defs: dict):
    """Build a schema-valid placeholder from a JSON schema."""
    if "$ref" in node:
        return _stub_value(defs[node["$ref"].split("/")[-1]], defs)
    if "enum" in node:
        return node["enum"][0]
    if "anyOf" in node:
        non_null = [n for n in node["anyOf"] if n.get("type") != "null"]
        return _stub_value(non_null[0], defs) if non_null else None
    t = node.get("type")
    if t == "object":
        return {k: _stub_value(v, defs) for k, v in node.get("properties", {}).items()}
    if t == "array":
        return []
    if t == "integer":
        return max(int(node.get("minimum", 3)), 3) if node.get("maximum", 5) >= 3 else int(node.get("minimum", 0))
    if t == "number":
        return float(node.get("minimum", 0.5))
    if t == "boolean":
        return False
    return "stub"


class LLMClient:
    def __init__(self, cfg: dict, cache_dir: str = ".cache/llm", usage_path: str | None = None,
                 rubric_version: str = "v1"):
        self.cfg = cfg
        self.provider = cfg.get("provider", "stub")
        self.model = cfg.get("model", "stub")
        self.rubric = rubric_version
        self.temperature = cfg.get("temperature", 0)
        self.json_mode = cfg.get("json_mode", True)
        self.retries = int(cfg.get("retries", 2))
        self.max_calls = int(cfg.get("max_calls", 900))
        self.min_interval = 60.0 / max(float(cfg.get("rpm", 25)), 1)
        self._last_call = 0.0
        self.calls = 0
        self.cache_hits = 0
        self.failures = 0
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.usage_path = Path(usage_path) if usage_path else None
        self._client = None
        if self.provider != "stub":
            from openai import OpenAI
            base = cfg.get("base_url") or PRESETS.get(self.provider, (None, None))[0]
            keyenv = cfg.get("api_key_env") or PRESETS.get(self.provider, (None, "LLM_API_KEY"))[1]
            key = os.environ.get(keyenv)
            if not key:
                raise RuntimeError(f"environment variable {keyenv} is not set (see .env.example)")
            self._client = OpenAI(base_url=base, api_key=key, max_retries=0)

    # ---------------------------------------------------------------- helpers
    def pin(self, system: str, user: str) -> dict:
        h = hashlib.sha256((system + "\n" + user).encode()).hexdigest()[:12]
        return {"provider": self.provider, "model": self.model, "rubric": self.rubric, "prompt_hash": h}

    def _key(self, system, user, schema, temperature, tag):
        raw = json.dumps([self.provider, self.model, self.rubric, schema.__name__, temperature, tag, system, user])
        return hashlib.sha256(raw.encode()).hexdigest()

    def _log(self, stage, tin, tout, latency, cached, ok):
        if not self.usage_path:
            return
        new = not self.usage_path.exists()
        with open(self.usage_path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ts", "stage", "provider", "model", "tokens_in", "tokens_out", "latency_s", "cached", "ok"])
            w.writerow([int(time.time()), stage, self.provider, self.model, tin, tout, round(latency, 2), int(cached), int(ok)])

    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    @staticmethod
    def _extract_json(text: str):
        text = text.strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                return json.loads(m.group(0))
            raise

    # ---------------------------------------------------------------- main API
    def complete(self, system: str, user: str, schema: Type[BaseModel], temperature: float | None = None,
                 stage: str = "", tag: str = "") -> BaseModel | None:
        temperature = self.temperature if temperature is None else temperature
        key = self._key(system, user, schema, temperature, tag)
        cfile = self.cache / f"{key}.json"
        if cfile.exists():
            self.cache_hits += 1
            self._log(stage, 0, 0, 0, True, True)
            return schema.model_validate_json(cfile.read_text())

        if self.provider == "stub":
            js = schema.model_json_schema()
            obj = schema.model_validate(_stub_value(js, js.get("$defs", {})))
            cfile.write_text(obj.model_dump_json())
            self._log(stage, 0, 0, 0, False, True)
            return obj

        sys_full = system + "\n\nReturn ONLY a JSON object matching this JSON schema, no prose, no code fences:\n" \
            + json.dumps(schema.model_json_schema())
        messages = [{"role": "system", "content": sys_full}, {"role": "user", "content": user}]
        last_err = ""
        for attempt in range(self.retries + 1):
            if self.calls >= self.max_calls:
                raise BudgetExceeded(f"max_calls={self.max_calls} reached; rerun with --resume (cache keeps progress)")
            msgs = list(messages)
            if last_err:
                msgs.append({"role": "user", "content": f"Your previous reply was invalid: {last_err}. Return corrected JSON only."})
            t0 = time.time()
            resp = self._call_with_backoff(msgs, temperature)
            self.calls += 1
            text = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            tin, tout = (usage.prompt_tokens, usage.completion_tokens) if usage else (0, 0)
            try:
                obj = schema.model_validate(self._extract_json(text))
                cfile.write_text(obj.model_dump_json())
                self._log(stage, tin, tout, time.time() - t0, False, True)
                return obj
            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                last_err = str(e)[:400]
                self._log(stage, tin, tout, time.time() - t0, False, False)
        self.failures += 1
        return None

    def _call_with_backoff(self, msgs, temperature, max_tries: int = 6):
        delay = 2.0
        for i in range(max_tries):
            self._throttle()
            try:
                kw = dict(model=self.model, messages=msgs, temperature=temperature)
                if self.json_mode:
                    kw["response_format"] = {"type": "json_object"}
                return self._client.chat.completions.create(**kw)
            except Exception as e:  # 429 / 5xx / json_mode unsupported
                status = getattr(e, "status_code", None)
                if self.json_mode and status == 400:
                    self.json_mode = False  # provider rejects response_format; fall back to prompt-only JSON
                    continue
                if status in (429, 500, 502, 503, 504) or status is None:
                    ra = getattr(getattr(e, "response", None), "headers", {}) or {}
                    wait = float(ra.get("retry-after", delay)) if hasattr(ra, "get") else delay
                    time.sleep(min(wait, 60) + (i * 0.5))
                    delay *= 2
                    continue
                raise
        raise RuntimeError("LLM call failed after backoff")

    def list_models(self) -> list[str]:
        if self._client is None:
            return ["stub"]
        try:
            return [m.id for m in self._client.models.list().data]
        except Exception:
            return []


class BudgetExceeded(RuntimeError):
    pass
