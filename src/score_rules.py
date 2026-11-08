"""Rule features + rule score (plan Appendix D). Weights are a starting guess (config-free constants here, reported as such).
Script-only signals: no audio/video exist in the pack (finding F11)."""
from __future__ import annotations
import re, statistics

W = dict(speech3=.08, action3=.08, short_high=.10, nonest=.05, accuse=.05, ends_ep=.14, interrupted=.08,
         reaction_sting=.06, high_last=.06, reveal=.03, density=.05, few_speakers=.05, unintro=-.06,
         calm_last=-.08, exposition=-.06, length=.07)
REVEAL = re.compile(r"\b(secret|truth|lied|lie|pregnan|dead|alive|identity|betray\w*|never told|who are you|impossible|"
                    r"you're not|you are not|married|wife|husband|duke|duchess|heir|illegitimate|blood|murder\w*|poison\w*|"
                    r"kill\w*|divorce|annul\w*|traitor|king|crown)\b", re.I)
IMPERATIVE = re.compile(r"^(get|stop|don't|do not|leave|listen|look|tell|let|give|take|come|go|answer|say|speak|how dare|"
                        r"you |your |who |what |why |where |how )", re.I)
CLOSE = re.compile(r"close-up|close up|extreme close|insert|reaction|tight on|push[- ]in|pushes in|slow zoom", re.I)
WIDE = re.compile(r"\b(wide|establishing|aerial|tracking|panoram\w*|drone|exterior)\b", re.I)


def words(t): return len(re.findall(r"[A-Za-z0-9']+", t))


def blocks_in(blocks, s, e):
    return [b for b in blocks if b["start"] >= s - 1e-6 and b["start"] < e - 1e-6]


def seg_features(blocks_by_ep, segs, ep_dur, intro_idx=None):
    """segs: list of dicts {episode,start,end}. Returns feature dict (0/1 or small numbers)."""
    first, last = segs[0], segs[-1]
    fb = blocks_in(blocks_by_ep[first["episode"]], first["start"], first["end"])
    lb = blocks_in(blocks_by_ep[last["episode"]], last["start"], last["end"])
    f3 = [b for b in fb if b["start"] < first["start"] + 3]
    f8 = [b for b in fb if b["start"] < first["start"] + 8]
    l5 = [b for b in lb if b["end"] > last["end"] - 5 or b["start"] > last["end"] - 5]
    all_b = [b for sg in segs for b in blocks_in(blocks_by_ep[sg["episode"]], sg["start"], sg["end"])]
    sp3 = [b for b in f3 if b["kind"] in ("speech", "audio_cue")]
    first_speech = next((b for b in fb if b["kind"] == "speech"), None)
    first_speech3 = next((b for b in f3 if b["kind"] == "speech"), None)
    cams = [b for b in fb if b["kind"] == "camera"]
    l_speech = [b for b in l5 if b["kind"] == "speech"]
    last_speech = max((b for b in lb if b["kind"] == "speech"), key=lambda b: b["start"], default=None)
    dur = sum(sg["end"] - sg["start"] for sg in segs)
    spk = {b["speaker"] for b in all_b if b["kind"] == "speech"}
    f = {}
    f["speech3"] = bool(sp3)
    f["action3"] = any(b["kind"] == "action" for b in f3)
    f["short_high"] = bool(first_speech3 and words(first_speech3["text"]) <= 8 and first_speech3["intensity"] == "high")
    f["nonest"] = bool(cams and CLOSE.search(cams[0]["text"]) and not WIDE.search(cams[0]["text"][:80]))
    f["accuse"] = bool(first_speech3 and ("?" in first_speech3["text"] or IMPERATIVE.search(first_speech3["text"].strip(" \"'“"))))
    f["ends_ep"] = last["end"] >= ep_dur[last["episode"]] - 0.05
    lt = last_speech["text"].strip() if last_speech else ""
    f["interrupted"] = bool(last_speech and last_speech["start"] > last["end"] - 8 and (lt.endswith(("?", "—", "-", "...", "…"))))
    last_blk = max(lb, key=lambda b: b["end"], default=None)
    f["reaction_sting"] = bool(any(b["kind"] == "audio_cue" for b in l5) or
                               (last_blk and last_blk["kind"] in ("camera", "action") and CLOSE.search(last_blk["text"])))
    f["high_last"] = bool(last_speech and last_speech["intensity"] == "high")
    f["reveal"] = bool(REVEAL.search(" ".join(b["text"] for b in all_b)))
    f["wps"] = sum(words(b["text"]) for b in all_b if b["kind"] == "speech") / max(dur, 1)
    f["few_speakers"] = 1 <= len(spk) <= 3
    unintro = 0
    if intro_idx:
        for sp in spk:
            fe = intro_idx.get(sp)
            if fe and (fe["first_episode"], fe["first_time"]) < (first["episode"], first["start"] - 0.01):
                unintro += 1
    f["unintro_n"] = unintro
    f["calm_last"] = bool(last_speech and last_speech["intensity"] == "low")
    f["exposition"] = bool(first_speech and first_speech["start"] < first["start"] + 8 and words(first_speech["text"]) >= 22
                           and first_speech["intensity"] != "high" and "?" not in first_speech["text"])
    f["length"] = 35 <= dur <= 60
    f["n_speakers"] = len(spk)
    return f


def rule_score(f, median_wps=None):
    s = 0.0
    for k in ("speech3", "action3", "short_high", "nonest", "accuse", "ends_ep", "interrupted", "reaction_sting",
              "high_last", "reveal", "few_speakers", "length", "calm_last", "exposition"):
        if f[k]: s += W[k]
    if median_wps and abs(f["wps"] - median_wps) <= 0.3 * median_wps: s += W["density"]
    s += W["unintro"] * min(1.0, f["unintro_n"] / 2)
    return round(s, 4)


def show_median_wps(cands):
    return statistics.median(c["features"]["wps"] for c in cands if c["features"]["wps"] > 0)
