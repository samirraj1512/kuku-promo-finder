from __future__ import annotations
from .validate import overlap_frac


def nms(cands, key="rule_score", max_overlap=0.6, per_episode=None, limit=None):
    """Greedy non-max suppression: best first; drop anything overlapping a kept one by > max_overlap."""
    kept = []
    cnt = {}
    for c in sorted(cands, key=lambda x: -x[key]):
        ep = c["segments"][0]["episode"]
        if per_episode and cnt.get(ep, 0) >= per_episode: continue
        if any(overlap_frac(c, k) > max_overlap for k in kept): continue
        kept.append(c); cnt[ep] = cnt.get(ep, 0) + 1
        if limit and len(kept) >= limit: break
    return kept
