"""Spike 1d: replay a cascade on spike 1 + 1c results. Decision 1 decides when it is sure
(p_goal <= 0.25 or >= 0.75); otherwise escalate to Neon agentic. Band fixed at 0.25 as a round
number, but chosen after seeing spike 1, so this is NOT a held-out result: it needs a fresh split.
Run: .venv/bin/python spikes/s1d_cascade.py"""
import json, pathlib, statistics
d1 = {(o["case"], o["label"]): o for o in json.load(open("results/s1_ego2act.json"))["clips"]}
ne = {(o["case"], o["label"]): o for o in json.load(open("results/s1c_neon_agentic.json"))["clips"]}
rows = []
for k, o in d1.items():
    sure = o["p_goal"] <= 0.25 or o["p_goal"] >= 0.75
    pred = (o["p_goal"] >= 0.75) if sure else ne[k]["success"]
    lat = o["s"] + (0 if sure else ne[k]["s"])
    rows.append({"case": k[0], "label": k[1], "escalated": not sure, "pred_success": pred, "latency_s": round(lat, 2)})
pos = [r for r in rows if r["label"] == "correct"]; neg = [r for r in rows if r["label"] == "wrong"]
tpr = sum(r["pred_success"] for r in pos) / len(pos); tnr = sum(not r["pred_success"] for r in neg) / len(neg)
lat = [r["latency_s"] for r in rows]
neon_lat = [o["s"] for o in ne.values()]
out = {"balanced_acc": round((tpr + tnr) / 2, 3), "tpr": round(tpr, 3), "tnr": round(tnr, 3),
       "escalated": sum(r["escalated"] for r in rows), "n": len(rows),
       "p50_latency_s": round(statistics.median(lat), 2), "neon_alone_p50_latency_s": round(statistics.median(neon_lat), 2),
       "decided_under_2s": sum(l < 2 for l in lat), "rows": rows}
pathlib.Path("results/s1d_cascade.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
