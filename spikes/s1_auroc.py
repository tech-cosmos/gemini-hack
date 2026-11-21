"""Threshold-free view of spike 1: AUROC and within-task pair wins for each score.
Run: .venv/bin/python spikes/s1_auroc.py  (reads results/s1_ego2act.json, writes results/s1_auroc.json)"""
import json, pathlib, statistics
d = json.load(open("results/s1_ego2act.json"))["clips"]
def auroc(key):
    pos = [o[key] for o in d if o["label"] == "correct"]; neg = [o[key] for o in d if o["label"] == "wrong"]
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 3)
for o in d: o["mean_check"] = statistics.mean(o["p_checks"])
def pairs(key):
    by = {}
    for o in d: by.setdefault(o["case"], {})[o["label"]] = o[key]
    return sum(v["correct"] > v["wrong"] for v in by.values()), len(by)
out = {k: {"auroc": auroc(k), "pair_wins": "%d/%d" % pairs(k)} for k in ["p_goal", "min_check", "mean_check"]}
pathlib.Path("results/s1_auroc.json").write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))
