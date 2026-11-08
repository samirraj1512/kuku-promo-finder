"""Source 3a: sliding windows cut only at valid cut points (HC4); block-level; end-of-episode windows extend to the final beat (F3)."""
from __future__ import annotations
from .cuts import speech_spans, is_valid_cut
from .score_rules import blocks_in

LENGTHS = [20, 25, 30, 35, 40, 45, 50, 55, 60]


def cut_points(blocks, ep_dur, margin):
    sp = speech_spans(blocks)
    starts = sorted({round(b["start"], 2) for b in blocks if is_valid_cut(b["start"], sp, margin)})
    ends = sorted({round(b["end"], 2) for b in blocks if b["end"] <= ep_dur + 1e-6} | {round(ep_dur, 2)})
    ends = [e for e in ends if is_valid_cut(e, sp, margin)]
    return starts, ends


def make_seg(ep, blocks, s, e):
    inc = blocks_in(blocks, s, e)
    return {"episode": ep, "start": round(s, 2), "end": round(e, 2),
            "start_id": inc[0]["id"] if inc else None, "end_id": inc[-1]["id"] if inc else None}


def window_candidates(ep, blocks, ep_dur, cfg):
    cu, spacing = cfg["cuts"], cfg["candidates"]["min_start_spacing_sec"]
    starts, ends = cut_points(blocks, ep_dur, cu["cut_margin_sec"])
    out, last_s, seen = [], -1e9, set()
    for s in starts:
        if s - last_s < spacing: continue
        last_s = s
        for L in LENGTHS:
            cand_e = [e for e in ends if s + 19.99 <= e <= s + L + 1e-6]
            if not cand_e: continue
            e = max(cand_e)
            if (s, e) in seen or e - s > cu["max_len"] + 1e-6: continue
            seen.add((s, e))
            out.append({"cand_id": f"W-E{ep:02d}-{int(s*100):05d}-{int(e*100):05d}", "source": "window",
                        "segments": [make_seg(ep, blocks, s, e)], "duration": round(e - s, 2)})
    return out
