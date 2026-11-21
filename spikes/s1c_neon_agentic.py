"""Spike 1c: Neon with agentic video processing on the same 20 ego2act clips as spike 1.
Pass mark in docs/IDEAS.md (written 11:42). Run: .venv/bin/python spikes/s1c_neon_agentic.py"""
import concurrent.futures as cf, faulthandler, json, os, pathlib, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(1500, exit=True)
from google import genai
client = genai.Client(http_options={"timeout": 300_000})
clips = json.load(open("results/s1_ego2act.json"))["clips"]
goals = {}
for o in clips:
    goals[o["case"]] = json.loads(pathlib.Path(f".context/ego2act/cases/{o['case']}/metadata.json").read_text())["goal"]

def run(o):
    path = pathlib.Path(f".context/ego2act/human/{o['label']}/{o['case']}/{o['label']}_1.mp4")
    t = time.perf_counter()
    try:
        f = client.files.upload(file=str(path))
        for _ in range(60):
            f = client.files.get(name=f.name)
            if str(getattr(f, "state", "ACTIVE")).upper().endswith("ACTIVE"): break
            time.sleep(2)
        r = client.interactions.create(model="gemini-4-neon", input=[
            {"type": "video", "uri": f.uri, "mime_type": "video/mp4", "processing": "agentic"},
            {"type": "text", "text": f"Goal for the final state: {goals[o['case']]}\nBy the end of this first-person video, is the goal fully reached? Answer YES or NO on the first line, then one sentence why."}])
        txt = (r.output_text or "").strip()
        return {"case": o["case"], "label": o["label"], "s": round(time.perf_counter() - t, 1),
                "success": txt.upper().startswith("YES"), "answer": txt[:200]}
    except Exception as e:
        return {"case": o["case"], "label": o["label"], "error": str(e)[:300]}

with cf.ThreadPoolExecutor(5) as ex:
    out = list(ex.map(run, clips))
ok = [o for o in out if "error" not in o]
pos = [o for o in ok if o["label"] == "correct"]; neg = [o for o in ok if o["label"] == "wrong"]
tpr = sum(o["success"] for o in pos) / max(len(pos), 1); tnr = sum(not o["success"] for o in neg) / max(len(neg), 1)
summary = {"balanced_acc": round((tpr + tnr) / 2, 3), "tpr": round(tpr, 3), "tnr": round(tnr, 3),
           "false_success": sum(o["success"] for o in neg), "n": len(ok), "errors": len(out) - len(ok),
           "latency_s": sorted(o["s"] for o in ok)}
pathlib.Path("results/s1c_neon_agentic.json").write_text(json.dumps({"summary": summary, "clips": out}, indent=2))
print(json.dumps(summary, indent=2)); [print(o.get("error")) for o in out if "error" in o][:3]
