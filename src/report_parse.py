"""Write reports/parse_report.md from parsed episodes (Step 2 audit)."""
from __future__ import annotations
import collections, statistics
from pathlib import Path
from .parse import Episode


def write_parse_report(eps: list[Episode], path: str | Path) -> dict:
    kinds = collections.Counter(b.kind for e in eps for b in e.blocks)
    durs = [e.duration for e in eps]
    stats = {
        "episodes": len(eps), "scenes": sum(len(e.scenes) for e in eps),
        "blocks": sum(kinds.values()), "kinds": dict(kinds),
        "runtime_sec": round(sum(durs), 1),
        "ep_len_median": round(statistics.median(durs), 1),
        "ep_len_min": round(min(durs), 1), "ep_len_max": round(max(durs), 1),
        "anomalies": sum(len(e.anomalies) for e in eps),
    }
    lines = ["# Parse report", "", "| measure | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in stats.items()]
    lines += ["", "## Per episode", "", "| ep | duration s | scenes | blocks | est. tokens | anomalies |", "|---|---|---|---|---|---|"]
    for e in eps:
        chars = sum(len(b.text) for b in e.blocks)
        lines.append(f"| {e.number} | {e.duration:.1f} | {len(e.scenes)} | {len(e.blocks)} | {chars // 4} | {len(e.anomalies)} |")
    any_anom = [(e.number, a) for e in eps for a in e.anomalies]
    lines += ["", "## Anomalies", ""] + ([f"- ep {n}: {a}" for n, a in any_anom] or ["none"])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return stats
