"""Spike 3: Tripwire, online. Can Decision 1 catch a mistake while it happens in a streamed first-person video?
20 ego2act clips (tasks at ranks 30-39 of spike 2's length ranking, correct_1 + wrong_1), cut into prefixes at 2 s
steps; one Decision 1 call per prefix ("tick"); a clip is flagged at the first tick with p >= 0.75 (frozen).
Pass mark (docs/IDEAS.md, written 11:53 before the run): PASS = flags >= 8/10 wrong clips before the clip ends,
<= 1 false alarm on the 10 correct clips, p50 Decision 1 latency per tick < 1.2 s. KILL = more than 3 false alarms.
The question wording was tuned on the FIRST TASK ONLY (see QUESTIONS and results "tuning").
Run: .venv/bin/python spikes/s3_tripwire.py            (full run, question = QUESTIONS[USE])
     .venv/bin/python spikes/s3_tripwire.py tune <key>  (first task only, prints p per tick, writes nothing to results)"""
import base64, concurrent.futures as cf, csv, faulthandler, io, json, os, pathlib, statistics, subprocess, sys, time, urllib.request
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(1200, exit=True)
from google import genai
START, N, STEP, FLAG = 30, 10, 2.0, 0.75
FFMPEG = "/opt/homebrew/bin/ffmpeg"
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE = pathlib.Path(".context/ego2act"); PRE = pathlib.Path(".context/s3_prefix"); TUNE = pathlib.Path(".context/s3_tune.json")
QUESTIONS = {
    "v1": "So far in this video, has the person done something that contradicts this goal (wrong item, wrong place, wrong orientation, swapped or missing items that cannot be fixed by continuing)? Being unfinished is NOT a mistake. Goal: {goal}",
    "v2": "Look only at actions the person has already completed in this video. Has the person already put an object into a final position or state that the goal forbids (wrong object used, object left in the wrong place, covers or items swapped, wrong orientation)? Answer NO if every completed action matches the goal, even if steps remain, items are still being moved, or items rest somewhere temporarily. Goal: {goal}",
}
USE = "v1"
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 60_000})

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
tasks = [c for _, c in pairs[START:START + N]]
seen = set(json.load(open("results/s1_checks.json"))) | set(json.load(open("results/s2_heldout.json"))["summary"]["tasks"])
assert not seen & set(tasks), "tasks overlap spikes 1/2"
mode = sys.argv[1] if len(sys.argv) > 1 else "full"
qkey = sys.argv[2] if mode == "tune" else USE
if mode == "tune": tasks = tasks[:1]
meta = {c: json.loads(fetch(f"cases/{c}/metadata.json").read_text()) for c in tasks}
clips = [(c, lab, f"human/{lab}/{c}/{lab}_1.mp4", dur[(c, lab, f"{lab}_1.mp4")]) for c in tasks for lab in ("correct", "wrong")]
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(lambda x: fetch(x[2]), clips))

def ticks(d):
    ts = []; t = STEP
    while t < d - 0.25: ts.append(t); t += STEP
    return ts + [round(d, 3)]

def prefix(rel, t):
    p = PRE / rel.replace("/", "__").replace(".mp4", f"__{t:g}.mp4")
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(fetch(rel)), "-t", f"{t}", "-vf", "scale=-2:360,fps=10",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", str(p)], check=True, timeout=120)
    return p

def d1(job):
    c, rel, t = job; data = base64.b64encode(prefix(rel, t).read_bytes()).decode(); err = None
    for attempt in range(2):
        t0 = time.perf_counter()
        try:
            r = beta.decisions.create(model="gemini-decision-1", input=[
                {"type": "text", "text": "First-person video of a person doing a task. The video may stop before the task is finished."},
                {"type": "video", "data": data, "mime_type": "video/mp4", "resolution": "low"}],
                questions={"mistake": {"type": "noul", "instructions": QUESTIONS[qkey].format(goal=meta[c]["goal"])}})
            a = r.answers["mistake"]
            return {"t": t, "p": round(a.noul, 3), "conf": round(a.confidence, 3), "s": round(time.perf_counter() - t0, 2), "attempts": attempt + 1}
        except Exception as e: err = str(e)[:300]
    return {"t": t, "error": err}

jobs = [(c, rel, t) for c, lab, rel, d in clips for t in ticks(d)]
print(f"{len(tasks)} tasks, {len(clips)} clips, {len(jobs)} Decision 1 calls planned (question {qkey})", flush=True)
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(lambda j: prefix(j[1], j[2]), jobs))
with cf.ThreadPoolExecutor(4) as ex: R = list(ex.map(d1, jobs))
calls = sum(r.get("attempts", 2) for r in R)

out = []; i = 0
for c, lab, rel, d in clips:
    n = len(ticks(d)); T = R[i:i + n]; i += n
    hit = next((x for x in T if x.get("p", 0) >= FLAG), None)
    o = {"case": c, "label": lab, "length_s": d, "flagged": hit is not None, "first_flag_s": hit["t"] if hit else None,
         "flagged_before_end": bool(hit and hit["t"] < d - 0.25), "lead_s": round(d - hit["t"], 3) if hit else None,
         "max_p": max((x["p"] for x in T if "p" in x), default=None), "ticks": T}
    if lab == "wrong": o["desc_not_sent_to_model"] = meta[c].get("wrong/wrong_1.mp4", {}).get("desc", "")
    out.append(o)
    print(f"{c[:34]:34} {lab:7} {d:5.1f}s flag={o['first_flag_s']}  " + " ".join(f"{x.get('p', 'ERR')}" for x in T), flush=True)

if mode == "tune":
    log = json.loads(TUNE.read_text()) if TUNE.exists() else []
    log.append({"question_key": qkey, "question": QUESTIONS[qkey], "task": tasks[0], "calls": calls,
                "clips": [{k: o[k] for k in ("label", "length_s", "first_flag_s")} | {"p": [x.get("p") for x in o["ticks"]]} for o in out]})
    TUNE.write_text(json.dumps(log, indent=2)); print("calls:", calls); sys.exit()

wrong = [o for o in out if o["label"] == "wrong"]; right = [o for o in out if o["label"] == "correct"]
lat = [x["s"] for o in out for x in o["ticks"] if "s" in x]
leads = [o["lead_s"] for o in wrong if o["flagged_before_end"]]
S = {"question_key": USE, "question": QUESTIONS[USE], "flag_threshold": FLAG, "step_s": STEP,
     "wrong_flagged_before_end": sum(o["flagged_before_end"] for o in wrong), "wrong_flagged_any_tick": sum(o["flagged"] for o in wrong),
     "wrong_n": len(wrong), "median_lead_s_before_end": statistics.median(leads) if leads else None,
     "lead_s": {o["case"]: o["lead_s"] for o in wrong},
     "false_alarms": sum(o["flagged"] for o in right), "correct_n": len(right),
     "false_alarm_cases": [(o["case"], o["first_flag_s"]) for o in right if o["flagged"]],
     "missed_wrong_cases": [o["case"] for o in wrong if not o["flagged_before_end"]],
     "tick_latency_p50_s": statistics.median(lat), "tick_latency_max_s": max(lat), "ticks": len(jobs),
     "decision1_calls": calls, "errors": sum("error" in x for o in out for x in o["ticks"]), "tasks": tasks,
     "first_task_used_for_tuning": tasks[0], "tuning": json.loads(TUNE.read_text()) if TUNE.exists() else []}
S["pass"] = S["wrong_flagged_before_end"] >= 8 and S["false_alarms"] <= 1 and S["tick_latency_p50_s"] < 1.2
S["kill"] = S["false_alarms"] > 3
pathlib.Path("results/s3_tripwire.json").write_text(json.dumps({"summary": S, "clips": out}, indent=2))
print(json.dumps({k: v for k, v in S.items() if k not in ("tasks", "tuning", "question")}, indent=2))
