"""API judge path: one pointwise+cold call per shortlisted clip via the swappable LLMClient. Output has the SAME schema as the human-in-loop
judgments file, so select_final.py does not care who judged. Run:  python run.py --judge api --provider gemini --model <model>
NOTE: written and exercised with the stub provider only (sandbox had no route to any LLM API). Not yet run live."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from .render_clips import render
from .schemas import Judgment

SYSTEM = Path("prompts/rubric_v1.md").read_text() if Path("prompts/rubric_v1.md").exists() else ""


def judge_all(client, short, blocks, out_path="scores/judgments_api.json"):
    J, bad = {}, 0
    ph = hashlib.sha256(SYSTEM.encode()).hexdigest()[:10]
    for c in short:
        j = client.complete(SYSTEM, "CLIP:\n" + render(c, blocks, compact=False), Judgment, stage="pointwise", tag=c["cand_id"])
        if j is None: bad += 1; continue
        ids = {b["id"] for sg in c["segments"] for b in blocks[sg["episode"]]}
        ev = [e for e in j.hook.evidence_ids + j.cliffhanger.evidence_ids if e not in ids]
        if ev: bad += 1                                                # hallucinated block IDs are counted, clip dropped
        else: J[c["cand_id"]] = json.loads(j.model_dump_json())
    Path(out_path).write_text(json.dumps({"judge": f"{client.provider}/{client.model}", "rubric": "v1", "prompt_hash": ph,
                                          "judgments": J, "pairwise": [], "post_first_reason": {}}, indent=1))
    return len(J), bad
