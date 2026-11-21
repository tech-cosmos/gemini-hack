"""Spike 6b: Done Gate (idea 19). Can one Decision 1 question tell "the person has finished and stopped" from "still working"?
The 20 spike 3 clips (ego2act ranks 30-39, correct_1 + wrong_1), each as the FULL clip and as its HALF-length prefix,
both cut the spike 3 way (360p, 10 fps). 40 Decision 1 calls (plus at most one retry each).
Pass mark (docs/IDEAS.md, written 12:30 before the run): p >= 0.75 on >= 16/20 full clips and on <= 2/20 half clips.
Run: .venv/bin/python spikes/s6_donegate.py"""
import base64, concurrent.futures as cf, faulthandler, json, os, pathlib, statistics, subprocess, time, urllib.request
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(600, exit=True)
from google import genai
FLAG = 0.75
Q = "Has the person finished working on the task and stopped (hands withdrawn or idle at the end), regardless of whether it was done correctly?"
FFMPEG = "/opt/homebrew/bin/ffmpeg"
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE = pathlib.Path(".context/ego2act"); PRE = pathlib.Path(".context/s3_prefix")
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 60_000})

def fetch(rel):
    p = CACHE / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{BASE}/{rel}", timeout=120) as r: p.write_bytes(r.read())
    return p

def prefix(rel, t):  # same cut as spike 3
    p = PRE / rel.replace("/", "__").replace(".mp4", f"__{t:g}.mp4")
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(fetch(rel)), "-t", f"{t}", "-vf", "scale=-2:360,fps=10",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", str(p)], check=True, timeout=120)
    return p

def d1(job):
    c, lab, rel, kind, t = job; data = base64.b64encode(prefix(rel, t).read_bytes()).decode(); err = None
    for attempt in range(2):
        t0 = time.perf_counter()
        try:
            r = beta.decisions.create(model="gemini-decision-1", input=[
                {"type": "text", "text": "First-person video of a person doing a task. The video may stop before the task is finished."},
                {"type": "video", "data": data, "mime_type": "video/mp4", "resolution": "low"}],
                questions={"done": {"type": "noul", "instructions": Q}})
            a = r.answers["done"]
            return {"p": round(a.noul, 3), "conf": round(a.confidence, 3), "s": round(time.perf_counter() - t0, 2), "attempts": attempt + 1}
        except Exception as e: err = str(e)[:300]
    return {"error": err}

s3 = json.load(open("results/s3_tripwire.json"))["clips"]
jobs = []
for o in s3:
    rel = f"human/{o['label']}/{o['case']}/{o['label']}_1.mp4"; d = o["length_s"]
    jobs += [(o["case"], o["label"], rel, "full", round(d, 3)), (o["case"], o["label"], rel, "half", round(d / 2, 3))]
print(f"{len(s3)} clips, {len(jobs)} Decision 1 calls planned", flush=True)
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(lambda j: prefix(j[2], j[4]), jobs))
with cf.ThreadPoolExecutor(4) as ex: R = list(ex.map(d1, jobs))
out = [{"case": c, "label": lab, "kind": kind, "t_s": t} | r for (c, lab, rel, kind, t), r in zip(jobs, R)]
for o in out: print(f"{o['case'][:34]:34} {o['label']:7} {o['kind']:4} {o['t_s']:6.2f}s p={o.get('p', 'ERR')}", flush=True)
full = [o for o in out if o["kind"] == "full"]; half = [o for o in out if o["kind"] == "half"]
lat = [o["s"] for o in out if "s" in o]
S = {"question": Q, "flag_threshold": FLAG,
     "full_done": sum(o.get("p", 0) >= FLAG for o in full), "full_n": len(full),
     "half_done": sum(o.get("p", 0) >= FLAG for o in half), "half_n": len(half),
     "full_done_correct": sum(o.get("p", 0) >= FLAG for o in full if o["label"] == "correct"),
     "full_done_wrong": sum(o.get("p", 0) >= FLAG for o in full if o["label"] == "wrong"),
     "full_p_median": statistics.median(o["p"] for o in full if "p" in o), "half_p_median": statistics.median(o["p"] for o in half if "p" in o),
     "full_missed": [(o["case"], o["label"], o.get("p")) for o in full if o.get("p", 0) < FLAG],
     "half_false_done": [(o["case"], o["label"], o.get("p")) for o in half if o.get("p", 0) >= FLAG],
     "latency_p50_s": statistics.median(lat), "latency_max_s": max(lat),
     "decision1_calls": sum(o.get("attempts", 2) for o in out), "errors": sum("error" in o for o in out)}
S["pass"] = S["full_done"] >= 16 and S["half_done"] <= 2
pathlib.Path("results/s6_donegate.json").write_text(json.dumps({"summary": S, "clips": out}, indent=2))
print(json.dumps(S, indent=2))
