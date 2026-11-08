"""Hard checks HC1-HC6 (plan 1.x). Everything invalid is COUNTED, never silently repaired."""
from __future__ import annotations
from .cuts import speech_spans, is_valid_cut


def check(c, blocks_by_ep, ep_dur, cfg_cuts, spans_cache=None):
    """Returns list of violated rule codes for one candidate."""
    v = []
    segs = c["segments"]
    dur = sum(s["end"] - s["start"] for s in segs)
    if not (cfg_cuts["min_len"] - 1e-6 <= dur <= cfg_cuts["max_len"] + 1e-6): v.append("HC1")
    if len(segs) > cfg_cuts["max_segments"]: v.append("HC5")
    prev = None
    for s in segs:
        ep = s["episode"]
        if ep not in ep_dur or s["start"] < 0 or s["end"] > ep_dur[ep] + 1e-6 or s["end"] <= s["start"]: v.append("HC2")
        sp = (spans_cache or {}).get(ep) or speech_spans(blocks_by_ep[ep])
        m = cfg_cuts["cut_margin_sec"]
        if not (is_valid_cut(s["start"], sp, m) and is_valid_cut(s["end"], sp, m)): v.append("HC4")
        key = (ep, s["start"])
        if prev and (key < prev[0] or (ep == prev[0][0] and s["start"] < prev[1] - 1e-6)): v.append("HC3")
        prev = (key, s["end"])
    return sorted(set(v))


def overlap_frac(a, b):
    """Overlap seconds / shorter total duration, same-episode segments only (HC6)."""
    ov = 0.0
    for x in a["segments"]:
        for y in b["segments"]:
            if x["episode"] == y["episode"]:
                ov += max(0.0, min(x["end"], y["end"]) - max(x["start"], y["start"]))
    da = sum(s["end"] - s["start"] for s in a["segments"]); db = sum(s["end"] - s["start"] for s in b["segments"])
    return ov / max(min(da, db), 1e-6)


def check_final(promos_as_cands, max_overlap=0.30):
    bad = []
    for i, a in enumerate(promos_as_cands):
        for b in promos_as_cands[:i]:
            if overlap_frac(a, b) > max_overlap: bad.append(("HC6", a["cand_id"], b["cand_id"]))
    return bad
