"""Step 2: parse screenplay files into a flat, time-ordered table of blocks.

Plain code, no AI. Fails loudly (file + line number) on anything unexpected.
Block kinds: camera | action | speech | audio_cue.  Times are seconds, episode-relative.
"""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

HEADER_RE = re.compile(r"^\*\*(.+?):\*\*\s*$")                      # trap T8: strict header
TIME_LINE_RE = re.compile(r"^Start:\s*\((\d+):(\d+(?:\.\d+)?)\)\s*\|\s*End:\s*\((\d+):(\d+(?:\.\d+)?)\)\s*$")
SPEAKER_RE = re.compile(r"^(.*?)\s*\((.*?)\)$")                     # trap T1
SCENE_RE = re.compile(r"^SCENE\s+(\d+)\s*$", re.I)
SCENE_TIME_RE = re.compile(r"^Scene (start|end):\s*(\d+):(\d+(?:\.\d+)?)\s*$", re.I)  # ep 6 is upper-case (W-008)
FILE_RE = re.compile(r"^episode-(\d+)-")
KIND_ORDER = {"camera": 0, "action": 1, "speech": 2, "audio_cue": 2}


class ParseError(Exception):
    pass


@dataclass
class Block:
    id: str = ""
    episode: int = 0
    scene: int = 0
    kind: str = ""
    speaker: str = ""
    speaker_raw: str = ""
    emotion_raw: str = ""
    intensity: str = "none"
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    line_no: int = 0


@dataclass
class Episode:
    number: int
    file: str
    logline: str = ""
    continuity: str = ""
    scenes: list = field(default_factory=list)   # dicts: no, heading, start, end
    blocks: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        ends = [s["end"] for s in self.scenes] or [b.end for b in self.blocks]
        return max(ends) if ends else 0.0


def _secs(mm: str, ss: str) -> float:
    return int(mm) * 60 + float(ss)


def parse_episode_text(text: str, fname: str) -> Episode:
    m = FILE_RE.match(Path(fname).name)
    if not m:
        raise ParseError(f"{fname}: file name must start with episode-NNN-")
    file_no = int(m.group(1))
    lines = text.splitlines()

    def err(i, msg):
        raise ParseError(f"{fname}:{i + 1}: {msg}")

    # ---- header
    ep_no = None
    logline = continuity = ""
    script_start = None
    for i, ln in enumerate(lines):
        if ln.startswith("EPISODE NUMBER:"):
            mm = re.search(r"(\d+)", ln)
            if not mm:
                err(i, "cannot read episode number")
            ep_no = int(mm.group(1))
        elif ln.startswith("EPISODE LOGLINE:"):
            logline = ln.split(":", 1)[1].strip()
        elif ln.startswith("CONTINUITY NOTES:"):
            continuity = ln.split(":", 1)[1].strip()
        elif ln.strip() == "--- SCRIPT START ---":
            script_start = i + 1
            break
    if ep_no is None:
        raise ParseError(f"{fname}: no EPISODE NUMBER header")
    if script_start is None:
        raise ParseError(f"{fname}: no --- SCRIPT START --- marker")
    ep = Episode(number=ep_no, file=Path(fname).name, logline=logline, continuity=continuity)
    if ep_no != file_no:  # trap T6
        ep.anomalies.append(f"header episode {ep_no} != file prefix {file_no}")

    # ---- body
    scene = None
    cur = None  # block being built: dict
    seen_time = False

    def close_block():
        nonlocal cur
        if cur is None:
            return
        if not seen_time_for(cur):
            raise ParseError(f"{fname}:{cur['line_no']}: block '{cur['header']}' has no Start/End line")
        ep.blocks.append(cur_to_block(cur))
        cur = None

    def seen_time_for(c):
        return c.get("start") is not None

    def cur_to_block(c) -> Block:
        header = c["header"]
        text_ = " ".join(c["text"]).strip()
        b = Block(episode=ep.number, scene=c["scene"], start=c["start"], end=c["end"],
                  text=text_, line_no=c["line_no"])
        if c["end"] < c["start"]:
            ep.anomalies.append(f"line {c['line_no']}: end before start")
        h = header.strip()
        up = h.upper()
        if up == "CAMERA":
            b.kind = "camera"
        elif up == "ACTION":
            b.kind = "action"
        elif up == "SOUND FX":                     # trap T2
            b.kind, b.speaker, b.speaker_raw = "audio_cue", "SOUND FX", "SOUND FX"
        else:
            b.kind = "speech"
            sm = SPEAKER_RE.match(h)
            if sm:
                b.speaker_raw, b.emotion_raw = sm.group(1).strip(), sm.group(2).strip()
            else:
                b.speaker_raw = h
            b.speaker = b.speaker_raw
            b.text = b.text.strip().strip('"').strip("\u201c\u201d").strip()
        return b

    for i in range(script_start, len(lines)):
        ln = lines[i]
        s = ln.strip()
        if s == "--- SCRIPT END ---":
            close_block()
            break
        sm = SCENE_RE.match(s)
        if sm:
            close_block()
            scene = {"no": int(sm.group(1)), "heading": "", "start": None, "end": None}
            ep.scenes.append(scene)
            continue
        if scene is not None and cur is None:
            if s.lower().startswith("scene heading:"):
                scene["heading"] = s.split(":", 1)[1].strip()
                continue
            st = SCENE_TIME_RE.match(s)
            if st:
                scene[st.group(1).lower()] = _secs(st.group(2), st.group(3))
                continue
            if s.lower().startswith("actions and dialogue"):
                continue
        hm = HEADER_RE.match(s)
        if hm:
            close_block()
            if scene is None:
                err(i, "block before any SCENE")
            cur = {"header": hm.group(1), "scene": scene["no"], "line_no": i + 1,
                   "start": None, "end": None, "text": []}
            continue
        if cur is not None:
            tm = TIME_LINE_RE.match(s)
            if tm and cur["start"] is None:
                cur["start"], cur["end"] = _secs(tm.group(1), tm.group(2)), _secs(tm.group(3), tm.group(4))
            elif s:
                if cur["start"] is None:
                    err(i, f"expected Start/End line, got: {s[:60]!r}")
                cur["text"].append(s)
        elif s:
            err(i, f"unexpected text outside a block: {s[:60]!r}")
    else:
        raise ParseError(f"{fname}: no --- SCRIPT END --- marker")

    for sc in ep.scenes:
        if sc["start"] is None or sc["end"] is None:
            raise ParseError(f"{fname}: scene {sc['no']} missing start/end")

    # ---- assign ids in time order (ties: camera, action, speech)
    ep.blocks.sort(key=lambda b: (b.start, KIND_ORDER[b.kind], b.end, b.line_no))
    for n, b in enumerate(ep.blocks, 1):
        b.id = f"E{ep.number:02d}-L{n:03d}"
    return ep


def load_show(path: str | Path) -> list[Episode]:
    """Load every episode-*.txt from a folder or a zip. Raises ParseError loudly."""
    path = Path(path)
    items: list[tuple[str, str]] = []
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if Path(n).name.startswith("episode-") and n.endswith(".txt"):
                    items.append((n, z.read(n).decode("utf-8")))
    else:
        for f in path.rglob("episode-*.txt"):
            items.append((str(f), f.read_text(encoding="utf-8")))
    if not items:
        raise ParseError(f"no episode-*.txt files found in {path}")
    eps = [parse_episode_text(t, n) for n, t in items]
    eps.sort(key=lambda e: e.number)
    nums = [e.number for e in eps]
    if len(set(nums)) != len(nums):
        raise ParseError(f"duplicate episode numbers: {nums}")
    return eps


def write_outputs(eps: list[Episode], outdir: str | Path) -> None:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "blocks.jsonl", "w", encoding="utf-8") as f:
        for e in eps:
            for b in e.blocks:
                f.write(json.dumps(asdict(b), ensure_ascii=False) + "\n")
    meta = [{"number": e.number, "file": e.file, "logline": e.logline, "continuity": e.continuity,
             "scenes": e.scenes, "duration": e.duration, "n_blocks": len(e.blocks),
             "anomalies": e.anomalies} for e in eps]
    (outdir / "episodes.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def load_blocks(outdir: str | Path) -> list[dict]:
    with open(Path(outdir) / "blocks.jsonl", encoding="utf-8") as f:
        return [json.loads(x) for x in f]


if __name__ == "__main__":
    import sys
    eps = load_show(sys.argv[1])
    write_outputs(eps, sys.argv[2] if len(sys.argv) > 2 else "parsed")
    print(f"{len(eps)} episodes, {sum(len(e.blocks) for e in eps)} blocks")
