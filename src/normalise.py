"""Step 3: speakers, emotion intensity, first appearances, episode continuity. Generic code; show specifics in overrides/."""
from __future__ import annotations
import collections, csv, json, re
from pathlib import Path
import yaml

PREFIXES = ("LADY ", "LORD ", "DUKE ", "SIR ", "DAME ")


def suggest_aliases(eps, overrides: dict | None = None) -> list[dict]:
    """Return alias rows. confidence: self | safe (auto-applied) | likely | story (need user apply=yes)."""
    cnt = collections.Counter(); first = {}
    for e in eps:
        for b in e.blocks:
            if b.kind == "speech":
                cnt[b.speaker_raw] += 1; first.setdefault(b.speaker_raw, e.number)
    labels = set(cnt)
    story = (overrides or {}).get("story_alias_suggestions", {})
    rows = []
    for lab in sorted(labels, key=lambda x: -cnt[x]):
        canon, rule, conf = lab, "self", "self"
        base = lab[4:] if lab.startswith("THE ") else lab
        if base != lab and base in labels:
            canon, rule, conf = base, "strip THE", "safe"
        elif base != lab and not any(l != lab and l.endswith(base) for l in labels):
            canon, rule, conf = base, "strip THE (no clash)", "safe"
        for p in PREFIXES:                                            # LADY JULIANA -> JULIANA (only if JULIANA exists)
            if base.startswith(p) and base[len(p):] in labels:
                canon, rule, conf = base[len(p):], f"strip {p.strip()} (base label exists)", "safe"
        if conf == "self":                                            # CONSTABLE inside POLICE CONSTABLE etc.
            toks = lab.replace("THE ", "").split()
            for other in labels:
                ot = other.replace("THE ", "").split()
                if other != lab and cnt[other] > cnt[lab] and toks and ot and toks[-1] == ot[-1] \
                        and (set(toks) < set(ot)) and toks[0] not in ("LADY", "LORD"):
                    canon, rule, conf = other, "token subset, same head word", "likely"
        if lab in story and conf == "self":
            canon, rule, conf = story[lab], "override suggestion (story-level)", "story"
        rows.append({"raw": lab, "canonical": canon, "rule": rule, "confidence": conf, "count": cnt[lab],
                     "first_episode": first[lab], "apply": "yes" if conf in ("safe", "self") else "no"})
    return rows


def write_alias_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def read_alias_map(path) -> dict:
    """Only rows with apply=yes are used. User edits the CSV (apply, canonical) to confirm."""
    m = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["raw"]] = r["canonical"] if r["apply"].strip().lower() == "yes" else r["raw"]
    return m


def intensity_of(emotion_raw: str, stems: dict) -> str:
    if not emotion_raw:
        return "none"
    t = emotion_raw.lower()
    if any(s in t for s in stems.get("high", [])):
        return "high"
    if any(s in t for s in stems.get("low", [])):
        return "low"
    return "medium"


def location_of(heading: str) -> str:
    h = re.sub(r"^(INT\.|EXT\.|INT/EXT\.?)\s*", "", heading.strip(), flags=re.I)
    return re.split(r"\s+[–—-]\s+", h)[0].strip().upper()


def continuity_links(eps) -> dict:
    out = {}
    for a, b in zip(eps, eps[1:]):
        same_loc = bool(a.scenes and b.scenes and location_of(a.scenes[-1]["heading"]) == location_of(b.scenes[0]["heading"]))
        note = bool(re.search(r"picks up immediately|immediately (after|following)|continues directly|moments after", b.continuity, re.I))
        out[b.number] = {"prev": a.number, "same_location": same_loc, "notes_say_continuous": note,
                         "continuous": same_loc or note}
    return out


def normalise(eps, stems: dict, alias_map: dict | None = None):
    """Mutates blocks in place: speaker (canonical), intensity. Returns characters index."""
    chars = {}
    for e in eps:
        for b in e.blocks:
            if b.kind == "speech":
                b.speaker = (alias_map or {}).get(b.speaker_raw, b.speaker_raw)
                b.intensity = intensity_of(b.emotion_raw, stems)
                c = chars.setdefault(b.speaker, {"first_episode": e.number, "first_time": b.start, "lines": 0, "eps": set()})
                c["lines"] += 1; c["eps"].add(e.number)
            elif b.kind == "audio_cue":
                b.intensity = "none"
    return {k: {**v, "eps": sorted(v["eps"])} for k, v in chars.items()}


def run_step3(eps, cfg: dict, outdir, overrides_path=None, alias_csv=None):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    ov = yaml.safe_load(open(overrides_path)) if overrides_path and Path(overrides_path).exists() else {}
    alias_csv = Path(alias_csv or outdir / "alias_map.csv")
    if not alias_csv.exists():                       # never overwrite the user's confirmed edits
        write_alias_csv(suggest_aliases(eps, ov), alias_csv)
    amap = read_alias_map(alias_csv)
    chars = normalise(eps, cfg["rules"]["intensity_stems"], amap)
    (outdir / "characters.json").write_text(json.dumps(chars, indent=1, ensure_ascii=False))
    (outdir / "continuity.json").write_text(json.dumps(continuity_links(eps), indent=1))
    return chars
