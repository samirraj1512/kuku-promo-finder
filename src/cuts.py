"""Valid cut points (HC4): a clip may start/end only where no speech or audio cue is in progress."""
from __future__ import annotations


def speech_spans(blocks: list[dict]) -> list[tuple[float, float]]:
    return sorted((b["start"], b["end"]) for b in blocks if b["kind"] in ("speech", "audio_cue"))


def is_valid_cut(t: float, spans: list[tuple[float, float]], margin: float = 0.15) -> bool:
    return not any(s + margin < t < e - margin for s, e in spans)
