"""Steps 4-5: candidates (windows + stitched) -> validate HC1-HC5 -> rule score -> NMS shortlist. Also random baseline."""
from __future__ import annotations
import json, random, collections
from pathlib import Path
from .cand_windows import window_candidates, make_seg, cut_points
from .cand_stitched import stitched_candidates
from .score_rules import seg_features, rule_score, show_median_wps
from .validate import check
from .dedupe import nms
from .validate import overlap_frac
from .cuts import speech_spans


def build(eps, cfg, out: Path, chars=None):
    out = Path(out); (out / "candidates").mkdir(parents=True, exist_ok=True)
    blocks_by_ep = {e.number: [b.__dict__ for b in e.blocks] for e in eps}
    ep_dur = {e.number: e.duration for e in eps}
    intro = {k: {"first_episode": v["first_episode"], "first_time": v["first_time"]} for k, v in (chars or {}).items()}
    cands, rejected = [], collections.Counter()
    n_gen = collections.Counter()
    for e in eps:
        bl = blocks_by_ep[e.number]
        gen = window_candidates(e.number, bl, ep_dur[e.number], cfg) + \
              stitched_candidates(e.number, bl, ep_dur[e.number], e.scenes, cfg, intro)
        for c in gen:
            n_gen[c["source"]] += 1
            v = check(c, blocks_by_ep, ep_dur, cfg["cuts"])
            if v:
                for x in v: rejected[x] += 1
                continue
            c["features"] = seg_features(blocks_by_ep, c["segments"], ep_dur, intro)
            cands.append(c)
    med = show_median_wps(cands)
    for c in cands: c["rule_score"] = rule_score(c["features"], med)
    # shortlist: stratified, NMS. Pass 1 = best 2 per episode (<=1 from each source first), cap overlap 0.3
    K = cfg["shortlist"]["k"]
    short, seen_ids = [], set()
    per_ep = {}
    for e in eps:
        mine = [c for c in cands if c["segments"][0]["episode"] == e.number]
        per_ep[e.number] = {"window": nms([c for c in mine if c["source"] == "window"], max_overlap=0.3, limit=2),
                            "stitched": nms([c for c in mine if c["source"] == "stitched"], max_overlap=0.3, limit=2)}
    # pass 1: best candidate of any source per episode (every episode represented); pass 2: best of the other source; fill by score
    for e in eps:
        both = per_ep[e.number]["window"][:1] + per_ep[e.number]["stitched"][:1]
        top = max(both, key=lambda c: c["rule_score"]); short.append(top); seen_ids.add(top["cand_id"])
    rest = [c for e in eps for src in ("window", "stitched") for c in per_ep[e.number][src] if c["cand_id"] not in seen_ids]
    for c in sorted(rest, key=lambda c: -c["rule_score"]):
        if len(short) >= K: break
        if all(overlap_frac(c, x) <= 0.3 for x in short): short.append(c)
    short = sorted(short, key=lambda c: -c["rule_score"])
    # random baseline (seeded): random valid window per episode, fixed N
    rnd = random.Random(cfg["run"]["seed"])
    wins = [c for c in cands if c["source"] == "window"]
    rand = rnd.sample(wins, min(cfg["candidates"]["baselines"]["random"], len(wins)))
    stats = {"generated": dict(n_gen), "kept_valid": len(cands), "rejected_by_rule": dict(rejected),
             "kept_by_source": dict(collections.Counter(c["source"] for c in cands)),
             "shortlist": len(short), "shortlist_by_source": dict(collections.Counter(c["source"] for c in short)),
             "shortlist_end_of_episode": sum(1 for c in short if c["features"]["ends_ep"]),
             "episodes_with_shortlist": len({c["segments"][0]["episode"] for c in short}),
             "median_wps": round(med, 3), "hc_pass_rate_of_kept": 1.0}
    (out / "candidates" / "all_candidates.jsonl").write_text("\n".join(json.dumps(c) for c in cands))
    (out / "candidates" / "shortlist.json").write_text(json.dumps(short, indent=1))
    (out / "candidates" / "random_baseline.json").write_text(json.dumps(rand, indent=1))
    (out / "candidates" / "stats.json").write_text(json.dumps(stats, indent=1))
    return cands, short, rand, stats
