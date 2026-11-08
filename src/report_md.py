import json, sys
from pathlib import Path


def write(out):
    p = json.load(open(Path(out) / "promos.json")); L = ["# Ranked promos (judge: Claude chat, human-in-loop; script-only, no audio/video)\n"]
    for x in p:
        seg = " + ".join(f"E{s['episode']} {s['start']}-{s['end']}" for s in x["segments"])
        L += [f"## {x['rank']}. [{x['tier']}] {x['promo_id']}  {seg}  ({x['duration_sec']} s, {x['source']})",
              f"- **Hook** ({x['hook']['type']}, {x['hook']['at']}): {x['hook']['text']}",
              f"- **Cliffhanger** ({x['cliffhanger']['type']}, {x['cliffhanger']['at']}): {x['cliffhanger']['text']}  \n  Open question: {x['cliffhanger'].get('unanswered_question')}",
              f"- **Why it works:** {x['why_it_works']}"]
        if x.get("post_first_reason"): L.append(f"- **Why post early:** {x['post_first_reason']}")
        L.append(f"- Scores: {x['scores']}\n")
    (Path(out) / "ranked_promos.md").write_text("\n".join(L))


if __name__ == "__main__": write(sys.argv[1])
