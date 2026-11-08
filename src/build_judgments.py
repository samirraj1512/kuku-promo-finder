"""Builds scores/judgments_v1.json from human-in-loop (Claude-chat) judge notes in scores/judge_notes/*.txt.
Line format (| separated):  idx | hook_score | hook_type | hook_at | cliff_score | cliff_type | cliff_at | clarity | confusions(;) | intensity | flags | cold(1/0) | why | hook_text | cliff_text | unanswered_question
flags: letters R=resolved_in_clip N=needs_prior_context S=spoiler_high s=spoiler_low (or '-')
Same Judgment schema as the API path, validated with pydantic. Timestamps are NOT here: they come from candidate block IDs."""
from __future__ import annotations
import json, sys, glob
from pathlib import Path
from .schemas import Judgment


def parse_line(l):
    p = [x.strip() for x in l.split("|")]
    idx, hs, ht, hat, cs, ct, cat, cl, conf, it, fl, cold, why, htx, ctx, q = p[:16]
    conf = [x for x in conf.split(";") if x and x != "-"]
    return int(idx), Judgment(
        reasoning=why, hook={"score": int(hs), "type": ht, "evidence_ids": [hat]},
        cliffhanger={"score": int(cs), "type": ct, "evidence_ids": [cat], "unanswered_question": q},
        clarity={"score": int(cl), "confusions": conf}, intensity=int(it),
        flags={"resolved_in_clip": "R" in fl, "needs_prior_context": "N" in fl,
               "spoiler_risk": "high" if "S" in fl else "low" if "s" in fl else "none"},
        why_it_works=why, cold={"passes": cold == "1", "confusions": conf, "who_is_in_conflict": htx, "why": "", "open_question": q},
        hook_text=htx, cliff_text=ctx)


def build(short_path, notes_glob="scores/judge_notes/*.txt", out_path="scores/judgments_v1.json", pairwise_path="scores/pairwise_v1.json"):
    short = json.loads(Path(short_path).read_text())
    J = {}
    for f in sorted(glob.glob(notes_glob)):
        for l in open(f):
            l = l.strip()
            if not l or l.startswith("#"): continue
            i, j = parse_line(l)
            J[short[i]["cand_id"]] = json.loads(j.model_dump_json())
    pw = json.loads(Path(pairwise_path).read_text()) if Path(pairwise_path).exists() else {"pairwise": [], "post_first_reason": {}}
    Path(out_path).write_text(json.dumps({"judge": "claude-chat (human-in-loop)", "rubric": "v1", "judgments": J,
                                          "pairwise": pw["pairwise"], "post_first_reason": pw["post_first_reason"]}, indent=1, ensure_ascii=False))
    return len(J)


if __name__ == "__main__":
    print("judged:", build(sys.argv[1]))
