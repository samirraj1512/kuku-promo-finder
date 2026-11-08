"""Steps 8-9: combine judgments (API or human-in-loop file) with rule scores -> gates -> pairwise -> diversity -> tiers -> promos.json/csv/md.
No judgments file => rules-only floor (still a valid output). Timestamps always come from candidate segments (block IDs), never from the judge."""
from __future__ import annotations
import csv, json
from pathlib import Path
from .baselines import fmt
from .validate import check, check_final, overlap_frac
from .schemas import Judgment, PairResult

WTS = dict(hook=.35, cliff=.35, clarity=.20, intensity=.10)


def llm_score(j: Judgment) -> float:
    return (WTS["hook"] * j.hook.score + WTS["cliff"] * j.cliffhanger.score + WTS["clarity"] * j.clarity.score
            + WTS["intensity"] * j.intensity) / 5.0


def gates(j: Judgment, g) -> list[str]:
    bad = []
    if j.hook.score < g["hook_min"]: bad.append("hook<min")
    if j.cliffhanger.score < g["cliffhanger_min"]: bad.append("cliff<min")
    if not j.cold.passes or len(j.clarity.confusions) > g["confusions_max"]: bad.append("cold_viewer_fail")
    if j.flags.resolved_in_clip: bad.append("resolved_in_clip")
    return bad


def _snip(blocks, c, which):
    sg = c["segments"][0 if which == "first" else -1]
    inc = [b for b in blocks[sg["episode"]] if sg["start"] - 1e-6 <= b["start"] < sg["end"]]
    if which == "first":
        b = next((b for b in inc if b["kind"] in ("action", "speech", "audio_cue")), inc[0] if inc else None)
    else:
        b = next((b for b in reversed(inc) if b["kind"] in ("speech", "action")), inc[-1] if inc else None)
    return (b["id"], (b["speaker"] + ": " if b["kind"] == "speech" else "") + b["text"][:140]) if b else (None, "")


def load_judgments(path):
    p = Path(path)
    if not p.exists(): return {}, [], {}
    raw = json.loads(p.read_text())
    J = {k: Judgment(**v) for k, v in raw.get("judgments", {}).items()}
    P = [PairResult(**x) for x in raw.get("pairwise", [])]
    return J, P, raw.get("post_first_reason", {})


def pair_winrates(P):
    wins, n = {}, {}
    for p in P:
        for x in (p.a, p.b): n[x] = n.get(x, 0) + 2; wins.setdefault(x, 0)
        for w in (p.winner_a_first, p.winner_b_first):
            if w in (p.a, p.b): wins[w] += 1
            else: wins[p.a] += .5; wins[p.b] += .5       # tie
    return {k: wins[k] / n[k] for k in n}


def select_and_write(eps, cfg, out, short, baseline, judgments_path="scores/judgments_v1.json"):
    out = Path(out)
    blocks = {e.number: [b.__dict__ for b in e.blocks] for e in eps}
    ep_dur = {e.number: e.duration for e in eps}
    J, P, pfr = load_judgments(judgments_path)
    wr = pair_winrates(P)
    sel = cfg["select"]
    ranked, excluded = [], []
    for c in short:
        j = J.get(c["cand_id"])
        if J and j is None: continue                         # judged run: only judged candidates are eligible
        if j:
            g = gates(j, cfg["scoring"]["gates"])
            if g: excluded.append({"cand_id": c["cand_id"], "gates": g}); continue
            key = llm_score(j) + 0.20 * wr.get(c["cand_id"], 0.5 if P else 0) * (1 if P else 0) + 0.05 * c["rule_score"]
        else:
            key = c["rule_score"]
        ranked.append((key, c, j))
    ranked.sort(key=lambda t: -t[0])
    final, cnt = [], {}
    for key, c, j in ranked:                                 # diversity: <=2 per episode, HC6 overlap <=30%
        ep = c["segments"][0]["episode"]
        if cnt.get(ep, 0) >= sel["max_per_episode"]: continue
        if any(overlap_frac(c, f[1]) > sel["max_overlap"] for f in final): continue
        final.append((key, c, j)); cnt[ep] = cnt.get(ep, 0) + 1
        if len(final) >= sel["final_n"]: break
    promos = []
    for i, (key, c, j) in enumerate(final, 1):
        tier = "A" if i <= sel["tiers"]["A"] else "B" if i <= sel["tiers"]["A"] + sel["tiers"]["B"] else "C"
        hid, ht = _snip(blocks, c, "first"); cid, ct = _snip(blocks, c, "last")
        promos.append({
            "rank": i, "tier": tier, "promo_id": f"P{i:03d}", "cand_id": c["cand_id"], "duration_sec": c["duration"],
            "segments": [{"episode": s["episode"], "start": fmt(s["start"]), "end": fmt(s["end"]), "start_s": s["start"],
                          "end_s": s["end"], "start_id": s["start_id"], "end_id": s["end_id"]} for s in c["segments"]],
            "hook": {"text": (j.hook_text if j else ht), "type": (j.hook.type if j else None), "at": (j.hook.evidence_ids[0] if j and j.hook.evidence_ids else hid)},
            "cliffhanger": {"text": (j.cliff_text if j else ct), "type": (j.cliffhanger.type if j else None),
                            "at": (j.cliffhanger.evidence_ids[0] if j and j.cliffhanger.evidence_ids else cid),
                            "unanswered_question": (j.cliffhanger.unanswered_question if j else None)},
            "why_it_works": (j.why_it_works if j else "rules-only: opening/ending structure signals (no LLM judge)"),
            "post_first_reason": pfr.get(c["cand_id"]) if i <= 5 else None,
            "source": c["source"], "judge": ("claude-chat (human-in-loop file)" if j else "none (rules only)"),
            "scores": ({"hook": j.hook.score, "cliffhanger": j.cliffhanger.score, "clarity": j.clarity.score, "intensity": j.intensity,
                        "llm_score": round(llm_score(j), 3), "pairwise_winrate": (round(wr[c["cand_id"]], 2) if c["cand_id"] in wr else None),
                        "rule_score": c["rule_score"]} if j else {"rule_score": c["rule_score"]}),
            "flags": (j.flags.model_dump() if j else None), "rank_key": round(key, 4)})
    final_c = [c for _, c, _ in final]
    hc = {"hc1_5_violations": sum(1 for c in final_c if check(c, blocks, ep_dur, cfg["cuts"])),
          "hc6_violations": len(check_final(final_c, sel["max_overlap"]))}
    (out / "promos.json").write_text(json.dumps(promos, indent=1, ensure_ascii=False))
    with open(out / "promos.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["rank", "tier", "promo_id", "episode(s)", "segments", "duration_sec", "hook", "cliffhanger", "why_it_works", "source"])
        for p in promos:
            w.writerow([p["rank"], p["tier"], p["promo_id"], "+".join(str(s["episode"]) for s in p["segments"]),
                        " | ".join(f"E{s['episode']} {s['start']}-{s['end']}" for s in p["segments"]), p["duration_sec"],
                        p["hook"]["text"], p["cliffhanger"]["text"], p["why_it_works"], p["source"]])
    (out / "run_summary.json").write_text(json.dumps({"n_final": len(promos), "n_shortlist": len(short), "n_judged": len(J),
                                                      "n_pairwise": len(P), "gate_exclusions": excluded, "hard_checks": hc}, indent=1))
    return promos
