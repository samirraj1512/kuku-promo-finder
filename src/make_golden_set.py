"""Blind golden set: ours top-5 + last45 (4 random eps) + random windows (3), shuffled, labels L01.. . Key stays in eval/golden_key.json (do NOT show the labeller)."""
import json, random, sys
sys.path.insert(0, ".")
from src.render_clips import render


def main(out="outputs/final", seed=7):
    out_dir = out; rnd = random.Random(seed)
    blocks = {}
    for l in open(f"{out_dir}/parsed/blocks.jsonl"):
        b = json.loads(l); blocks.setdefault(b["episode"], []).append(b)
    promos = json.load(open(f"{out_dir}/promos.json")); short = {c["cand_id"]: c for c in json.load(open(f"{out_dir}/candidates/shortlist.json"))}
    base = json.load(open(f"{out_dir}/baseline_last45.json")); rand = json.load(open(f"{out_dir}/candidates/random_baseline.json"))
    items = [("ours", short[p["cand_id"]]) for p in promos[:5]]
    items += [("last45", {"cand_id": b["promo_id"], "segments": [{"episode": b["segments"][0]["episode"], "start": float(b["segments"][0]["start"][:2]) * 60 + float(b["segments"][0]["start"][3:]),
                                                                  "end": float(b["segments"][0]["end"][:2]) * 60 + float(b["segments"][0]["end"][3:])}], "duration": b["duration_sec"]}) for b in rnd.sample(base, 4)]
    items += [("random", c) for c in rnd.sample(rand, 3)]
    rnd.shuffle(items)
    key, md = {}, ["# Blind labelling sheet (12 clips, script text only)\n",
                   "For each clip answer: **POST** (I would post this as a promo), **MAYBE**, or **NO**. Judge as a scrolling stranger would: strong first 3 s? ends on an unresolved question? makes sense alone? "
                   "Fill `eval/golden_labels.csv` (columns: label_id,label) - or just reply in chat like `L01 POST, L02 NO, ...`.\n"]
    for i, (sysname, c) in enumerate(items, 1):
        lid = f"L{i:02d}"; key[lid] = {"system": sysname, "cand_id": c["cand_id"], "segments": c["segments"]}
        md.append(f"\n## {lid}  ({c['duration']:.0f} s)\n```\n{render(c, blocks, camera_chars=160, ids=False, compact=False)}\n```")
    open("eval/blind_labelling_sheet.md", "w").write("\n".join(md)); json.dump(key, open("eval/golden_key.json", "w"), indent=1)
    print("clips:", len(items), "chars:", len("\n".join(md)))


if __name__ == "__main__":
    main()
