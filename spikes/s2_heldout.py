"""Spike 2: the Decision 1 -> Neon cascade on held-out ego2act clips, with the rule frozen from spike 1d.
Tasks are ranked by clip length like spike 1; spike 1 used ranks 0-9, this uses ranks 10-29 by default.
Pass mark in docs/IDEAS.md (written 11:39). Run: .venv/bin/python spikes/s2_heldout.py [start=10] [n_tasks=20]"""
import base64, concurrent.futures as cf, csv, faulthandler, io, json, os, pathlib, statistics, sys, time, urllib.request
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(2400, exit=True)
from google import genai
START = int(sys.argv[1]) if len(sys.argv) > 1 else 10
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
LO, HI = 0.25, 0.75  # frozen from spike 1d
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE = pathlib.Path(".context/ego2act")
gen = genai.Client(http_options={"timeout": 300_000})
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 180_000})

def fetch(rel):
    p = CACHE / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{BASE}/{rel}", timeout=120) as r: p.write_bytes(r.read())
    return p

rows = list(csv.DictReader(io.StringIO(fetch("human/metadata.csv").read_text())))
dur = {(r["case_id"], r["label"], r["file_name"].rsplit("/", 1)[-1]): float(r["duration_s"]) for r in rows}
pairs = sorted((max(a, b), c) for c in sorted({r["case_id"] for r in rows})
               for a, b in [(dur.get((c, "correct", "correct_1.mp4")), dur.get((c, "wrong", "wrong_1.mp4")))] if a and b)
seen = {c for c in json.load(open("results/s1_checks.json"))}
tasks = [c for _, c in pairs[START:START + N]]
assert not seen & set(tasks), "held-out tasks overlap spike 1"
goals = {c: json.loads(fetch(f"cases/{c}/metadata.json").read_text())["goal"] for c in tasks}
clips = [(c, lab, f"human/{lab}/{c}/{lab}_1.mp4") for c in tasks for lab in ("correct", "wrong")]
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(lambda x: fetch(x[2]), clips))
print(f"{len(tasks)} held-out tasks, {len(clips)} clips, longest {pairs[START+N-1][0]:.1f} s", flush=True)

def d1(item):
    c, lab, rel = item; t = time.perf_counter()
    try:
        r = beta.decisions.create(model="gemini-decision-1", input=[
            {"type": "text", "text": "First-person video of a person doing a task."},
            {"type": "video", "data": base64.b64encode(fetch(rel).read_bytes()).decode(), "mime_type": "video/mp4", "resolution": "low"}],
            questions={"goal_reached": {"type": "noul", "instructions": f"By the end of the video, is this goal fully reached? Goal: {goals[c]}"}})
        a = r.answers["goal_reached"]
        return {"p": round(a.noul, 3), "conf": round(a.confidence, 3), "s": round(time.perf_counter() - t, 2)}
    except Exception as e: return {"error": str(e)[:300]}

def neon(item):
    c, lab, rel = item; t = time.perf_counter()
    try:
        f = gen.files.upload(file=str(fetch(rel)))
        for _ in range(60):
            f = gen.files.get(name=f.name)
            if str(getattr(f, "state", "ACTIVE")).upper().endswith("ACTIVE"): break
            time.sleep(2)
        r = gen.interactions.create(model="gemini-4-neon", input=[
            {"type": "video", "uri": f.uri, "mime_type": "video/mp4", "processing": "agentic"},
            {"type": "text", "text": f"Goal for the final state: {goals[c]}\nBy the end of this first-person video, is the goal fully reached? Answer YES or NO on the first line, then one sentence why."}])
        txt = (r.output_text or "").strip()
        return {"success": txt.upper().startswith("YES"), "answer": txt[:200], "s": round(time.perf_counter() - t, 1)}
    except Exception as e: return {"error": str(e)[:300]}

with cf.ThreadPoolExecutor(6) as ex:
    D = list(ex.map(d1, clips)); print("decision 1 done", flush=True)
    M = list(ex.map(neon, clips)); print("neon done", flush=True)

out = []
for (c, lab, _), d, m in zip(clips, D, M):
    o = {"case": c, "label": lab, "d1": d, "neon": m}
    if "error" not in d:
        o["d1_success"] = d["p"] > 0.5
        sure = d["p"] <= LO or d["p"] >= HI
        o["escalated"] = not sure
        if sure: o["cascade_success"], o["cascade_s"] = d["p"] >= HI, d["s"]
        elif "error" not in m: o["cascade_success"], o["cascade_s"] = m["success"], round(d["s"] + m["s"], 2)
    if "error" not in m: o["neon_success"] = m["success"]
    out.append(o)

def score(key, lat=None):
    ok = [o for o in out if key in o]
    pos = [o for o in ok if o["label"] == "correct"]; neg = [o for o in ok if o["label"] == "wrong"]
    tpr = sum(o[key] for o in pos) / max(len(pos), 1); tnr = sum(not o[key] for o in neg) / max(len(neg), 1)
    r = {"balanced_acc": round((tpr + tnr) / 2, 3), "tpr": round(tpr, 3), "tnr": round(tnr, 3),
         "false_success": sum(o[key] for o in neg), "n": len(ok)}
    if lat: ls = [lat(o) for o in ok]; r["p50_s"] = round(statistics.median(ls), 2); r["max_s"] = round(max(ls), 2)
    return r

S = {"decision1_alone": score("d1_success", lambda o: o["d1"]["s"]),
     "neon_alone": score("neon_success", lambda o: o["neon"]["s"]),
     "cascade": score("cascade_success", lambda o: o["cascade_s"]),
     "escalated": sum(o.get("escalated", False) for o in out),
     "errors": {"d1": sum("error" in o["d1"] for o in out), "neon": sum("error" in o["neon"] for o in out)},
     "tasks": tasks}
c, n, d = S["cascade"], S["neon_alone"], S["decision1_alone"]
S["pass"] = c["balanced_acc"] >= n["balanced_acc"] - 0.05 and c["balanced_acc"] >= d["balanced_acc"] + 0.10 and c["p50_s"] <= 3
pathlib.Path("results/s2_heldout.json").write_text(json.dumps({"summary": S, "clips": out}, indent=2))
print(json.dumps({k: v for k, v in S.items() if k != "tasks"}, indent=2))
