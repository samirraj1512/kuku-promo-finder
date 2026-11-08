"""Render shortlist clips as compact text for the judge (API or human-in-loop). Camera lines trimmed; IDs kept so the judge cites evidence."""
from __future__ import annotations
import json, sys
from pathlib import Path


def mmss(t): return f"{int(t//60):02d}:{t%60:04.1f}"


def render(c, blocks, camera_chars=75, ids=True, compact=True):
    lines = []
    for si, sg in enumerate(c["segments"]):
        if len(c["segments"]) > 1: lines.append(f"--- segment {si+1}/{len(c['segments'])} (cut) ---")
        inc = [b for b in blocks[sg["episode"]] if sg["start"] - 1e-6 <= b["start"] < sg["end"]]
        cams = [b["id"] for b in inc if b["kind"] == "camera"]
        keep_cam = set(cams[:2] + cams[-1:]) if compact else set(cams)      # compact: first 2 + last camera line only
        for b in inc:
            if b["kind"] == "camera" and b["id"] not in keep_cam: continue
            if True:
                k = {"camera": "CAM", "action": "ACT", "speech": "SAY", "audio_cue": "SFX"}[b["kind"]]
                t = b["text"][:170] if b["kind"] != "camera" else b["text"][:camera_chars]
                who = f"{b['speaker']}({b['emotion_raw']}): " if b["kind"] == "speech" else ""
                lines.append((f"{b['id']} " if ids else "") + f"[{mmss(b['start'] - sg['start'])}] {k} {who}{t}")
    return "\n".join(lines)


if __name__ == "__main__":
    out = Path(sys.argv[1]); lo, hi = int(sys.argv[2]), int(sys.argv[3])
    short = json.loads((out / "candidates/shortlist.json").read_text())
    blocks = {}
    for l in open(out / "parsed/blocks.jsonl"):
        b = json.loads(l); blocks.setdefault(b["episode"], []).append(b)
    for i, c in enumerate(short[lo:hi], lo):
        print(f"\n=== #{i} {c['cand_id']} | {c['source']} | {c['duration']}s | rule={c['rule_score']} ===")
        print(render(c, blocks))
