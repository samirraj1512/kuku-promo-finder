#!/usr/bin/env python3
"""One command: parse -> (candidates -> scoring -> ranking, built step by step) -> outputs.
Currently implemented: Step 1 (plumbing + stub LLM) and Step 2 (parse + audit) + baseline S1.
Usage:  python run.py --input data/show1 --episodes 1-3 --model stub --out outputs/smoke
"""
import argparse, json, sys, collections
from pathlib import Path
import yaml
from src.parse import load_show, write_outputs
from src.report_parse import write_parse_report
from src.baselines import last45, fmt
from src.llm_client import LLMClient
from src.normalise import run_step3
from src.build_candidates import build


def parse_range(s, allx):
    if not s:
        return allx
    out = set()
    for part in s.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return sorted(out & set(allx))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--input")
    ap.add_argument("--episodes", help="e.g. 1-10 or 1,5,9")
    ap.add_argument("--provider"); ap.add_argument("--model"); ap.add_argument("--base-url")
    ap.add_argument("--out", default="outputs/run")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--judge", choices=["file", "api"], default="file", help="file = scores/judgments_v1.json if present (else rules only); api = call the LLM provider")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    llm_cfg = cfg["llm"]
    if a.model == "stub":
        llm_cfg["provider"] = "stub"
    if a.provider: llm_cfg["provider"] = a.provider
    if a.model and a.model != "stub": llm_cfg["model"] = a.model
    if a.base_url: llm_cfg["base_url"] = a.base_url
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    eps = load_show(a.input or cfg["run"]["input"])            # fails loudly on bad format (T9)
    keep = parse_range(a.episodes, [e.number for e in eps])
    eps = [e for e in eps if e.number in keep]
    ov = "overrides/show1.yaml"  # TODO(next): pick overrides by --show flag
    chars = run_step3(eps, cfg, out / "parsed", ov if Path(ov).exists() else None)   # Step 3: aliases (apply=yes rows only), intensity
    write_outputs(eps, out / "parsed")
    stats = write_parse_report(eps, out / "parse_report.md")
    print("parsed:", stats["episodes"], "episodes,", stats["blocks"], "blocks")

    client = LLMClient(llm_cfg, cache_dir=".cache/llm" if not a.no_cache else str(out / ".nocache"),
                       usage_path=str(out / "usage.csv"), rubric_version=cfg["run"]["rubric_version"])
    print("llm:", client.provider, client.model)

    # TODO(next): Steps 3-10. For now emit the S1 baseline in the final schema so the pipeline is end-to-end.
    blocks_by_ep = {e.number: [b.__dict__ for b in e.blocks] for e in eps}
    promos = []
    for i, c in enumerate(last45(eps, blocks_by_ep, margin=cfg["cuts"]["cut_margin_sec"]), 1):
        s = c["segments"][0]
        promos.append({"rank": i, "tier": "baseline", "promo_id": c["cand_id"], "duration_sec": c["duration"],
                       "segments": [{"episode": s["episode"], "start": fmt(s["start"]), "end": fmt(s["end"])}],
                       "hook": None, "cliffhanger": None, "why_it_works": "baseline: last 45 s of episode",
                       "source": c["source"], "scores": None, "flags": None})
    (out / "baseline_last45.json").write_text(json.dumps(promos, indent=1))
    cands, short, rand, stats = build(eps, cfg, out, chars)            # Steps 4-5
    print("candidates:", json.dumps(stats))
    from src.select_final import select_and_write
    jpath = "scores/judgments_v1.json"
    if a.judge == "api":
        from src.score_pointwise import judge_all
        n_ok, n_bad = judge_all(client, short, {e.number: [b.__dict__ for b in e.blocks] for e in eps}, str(out / "judgments_api.json"))
        print("api judge: ok", n_ok, "invalid/hallucinated", n_bad); jpath = str(out / "judgments_api.json")
    select_and_write(eps, cfg, out, short, promos, jpath)                      # Steps 8-9 (judgments file if present, else rules only)
    print("done; see", out / "promos.json", out / "run_summary.json")


if __name__ == "__main__":
    main()
