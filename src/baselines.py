"""Baseline S1 'last45': the final ~45 s of each episode (strong because episodes end on built-in cliffhangers)."""
from __future__ import annotations
from .cuts import speech_spans, is_valid_cut


def fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def last45(episodes, blocks_by_ep: dict, length: float = 45.0, margin: float = 0.15) -> list[dict]:
    out = []
    for ep in episodes:
        blocks = blocks_by_ep[ep.number]
        spans = speech_spans(blocks)
        end = ep.duration
        target = max(0.0, end - length)
        # earliest block start at/after target that is a valid cut (so total <= length)
        starts = sorted({b["start"] for b in blocks if b["start"] >= target - 1e-6})
        start = next((s for s in starts if is_valid_cut(s, spans, margin)), None)
        if start is None or end - start < 20:
            continue
        out.append({"cand_id": f"B-last45-E{ep.number:02d}", "source": "baseline_last45",
                    "segments": [{"episode": ep.number, "start": round(start, 2), "end": round(end, 2)}],
                    "duration": round(end - start, 2)})
    return out
