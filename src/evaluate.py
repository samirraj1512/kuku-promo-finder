"""Golden-set metrics: precision of POST labels (strict) and POST+MAYBE (lenient) per system, Wilson 95% intervals. Honest about n."""
import csv, json, math, sys, collections


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0, c - h), 2), round(min(1, c + h), 2)


def main(labels_csv="eval/golden_labels.csv", key_json="eval/golden_key.json", out="eval/metrics.json"):
    key = json.load(open(key_json)); lab = {r["label_id"].strip().upper(): r["label"].strip().upper() for r in csv.DictReader(open(labels_csv))}
    by = collections.defaultdict(list)
    for lid, v in lab.items(): by[key[lid]["system"]].append(v)
    res = {}
    for s, v in by.items():
        n = len(v); strict = sum(x == "POST" for x in v); lenient = sum(x in ("POST", "MAYBE") for x in v)
        res[s] = {"n": n, "post": strict, "post_or_maybe": lenient, "precision_strict": round(strict / n, 2), "wilson95_strict": wilson(strict, n),
                  "precision_lenient": round(lenient / n, 2), "wilson95_lenient": wilson(lenient, n)}
    json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1))
    ours, base = res.get("ours"), res.get("last45")
    if ours and base: print("VERDICT:", "ours beats last45 on strict precision" if ours["precision_strict"] > base["precision_strict"] else
                            "ours does NOT beat last45 (say so in the doc)", "- n is tiny, intervals overlap heavily")


if __name__ == "__main__":
    main()
