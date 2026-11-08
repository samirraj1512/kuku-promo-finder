"""Source 3c: joined promos inside ONE episode: hook segment (3-12 s) [+ bridge 5-15 s] + cliffhanger segment (5-20 s), chronological.
User's ground truth (4 of 5 real promos were joined) keeps this in the MVP. Cross-episode joins are NOT built (stated limit)."""
from __future__ import annotations
from .cand_windows import cut_points, make_seg
from .score_rules import blocks_in, seg_features, rule_score


def _sub(ep, blocks, ep_dur, intro, s, e, which):
    segs = [{"episode": ep, "start": s, "end": e}]
    f = seg_features({ep: blocks}, segs, {ep: ep_dur}, intro)
    if which == "hook":
        return sum(w for k, w in (("speech3", .08), ("action3", .08), ("short_high", .10), ("nonest", .05), ("accuse", .05)) if f[k]) \
            + (.04 if f["reveal"] else 0)
    return sum(w for k, w in (("ends_ep", .14), ("interrupted", .08), ("reaction_sting", .06), ("high_last", .06)) if f[k]) \
        - (.08 if f["calm_last"] else 0)


def stitched_candidates(ep, blocks, ep_dur, scenes, cfg, intro=None, top_hooks=5, top_cliffs=4):
    cu = cfg["candidates"]["stitched"]
    starts, ends = cut_points(blocks, ep_dur, cfg["cuts"]["cut_margin_sec"])
    hooks = []
    for s in starts:
        if s > ep_dur * 0.65: break
        for L in (6, 9, 12):
            es = [e for e in ends if s + cu["hook_len"][0] <= e <= s + L + 1e-6]
            if es:
                e = max(es); hooks.append((_sub(ep, blocks, ep_dur, intro, s, e, "hook"), s, e))
    hooks = sorted(set(hooks), reverse=True)
    sel_h = []
    for sc, s, e in hooks:
        if all(abs(s - x[1]) >= 6 for x in sel_h): sel_h.append((sc, s, e))
        if len(sel_h) >= top_hooks: break
    cl_ends = [round(ep_dur, 2)] + [round(sc["end"], 2) for sc in scenes[:-1] if sc["end"] in ends]
    cliffs = []
    for e in cl_ends:
        for L in (8, 12, 16, 20):
            ss = [s for s in starts if e - L - 1e-6 <= s <= e - cu["cliff_len"][0]]
            if ss:
                s = min(ss); cliffs.append((_sub(ep, blocks, ep_dur, intro, s, e, "cliff"), s, e))
    cliffs = sorted(set(cliffs), reverse=True)[:top_cliffs]
    out, seen = [], set()
    for hs, h0, h1 in sel_h:
        for cs, c0, c1 in cliffs:
            if c0 - h1 < 1.5: continue                       # would be one continuous clip: windows already cover that
            tot = (h1 - h0) + (c1 - c0)
            variants = []
            if tot >= 20: variants.append([(h0, h1), (c0, c1)])
            # optional bridge: highest-intensity 5-15 s beat between hook and cliff, keeping total <= 60
            best = None
            for b0 in [s for s in starts if h1 + 1.0 <= s <= c0 - 6]:
                for L in (8, 12, 15):
                    es = [e for e in ends if b0 + 5 <= e <= min(b0 + L, c0 - 1.0)]
                    if es:
                        b1 = max(es)
                        inten = sum({"high": 2, "medium": 1}.get(b["intensity"], 0) for b in blocks_in(blocks, b0, b1))
                        if tot + (b1 - b0) <= 60 and (best is None or inten > best[0]): best = (inten, b0, b1)
            if best and tot + (best[2] - best[1]) >= 20: variants.append([(h0, h1), (best[1], best[2]), (c0, c1)])
            for v in variants:
                key = tuple(v)
                if key in seen: continue
                seen.add(key)
                segs = [make_seg(ep, blocks, a, b) for a, b in v]
                dur = sum(b - a for a, b in v)
                if 20 <= dur <= 60:
                    out.append({"cand_id": f"S-E{ep:02d}-" + "-".join(f"{int(a*100):05d}" for a, _ in v), "source": "stitched",
                                "segments": segs, "duration": round(dur, 2)})
    return out
