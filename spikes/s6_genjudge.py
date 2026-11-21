"""Spike 6a: can Decision 1 judge GENERATED video? (decides idea 18, "Show Me Right")
10 fresh ego2act tasks (ranks 40-49 of the length ranking; none in spikes 1, 2, 3). Seed = first frame of correct_1.
Omni 1.2 Flash image->video, 6 s, two clips per task: RIGHT (goal done) and WRONG (one mistake, WRONG_ACT below, written from
the goal text before any output). 20 generations (cached in .context/s6_gen/, gitignored), at most 4 at once.
Every clip is scored by the frozen Decision 1 goal question from spike 2 (low resolution). 20 Decision 1 calls.
Pass mark (docs/IDEAS.md, written 12:30 before the run): AUROC >= 0.85 RIGHT vs WRONG, and >= 7/10 RIGHT clips at p >= 0.75.
Run: .venv/bin/python spikes/s6_genjudge.py"""
import base64, concurrent.futures as cf, csv, faulthandler, io, json, os, pathlib, statistics, subprocess, time, urllib.request
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(1200, exit=True)
from google import genai
START, N, HI = 40, 10, 0.75
FFMPEG = "/opt/homebrew/bin/ffmpeg"
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE = pathlib.Path(".context/ego2act"); OUT = pathlib.Path(".context/s6_gen"); OUT.mkdir(parents=True, exist_ok=True)
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 300_000})
WRONG_ACT = {  # one specific mistake per task, written from the goal text only
    "matryoshka": "nest the three larger matryoshka dolls inside one another, but leave the smallest doll standing outside on the table",
    "toothbrush_case": "put the folded toothbrush inside the travel case and close the case, but leave the toothpaste outside on the table",
    "eyedrop_chapstick": "put the eye drops and the bandage inside the blue bag, but leave the chapstick outside on the table",
    "banknote_card_coin": "put the coin inside the wallet and the banknote in the small bowl (swapped), with the card in the wallet's card compartment",
    "prepare_camera_power_storage": "install the SD card in the camera, but leave the battery on the table and the battery compartment open",
    "headphone_mouse_book": "hang the cable-connected headphones on the headphone stand, but put the other headphones on the table next to the yellow notebook, not on top of it",
    "eyeshadow_palette": "put the makeup items inside the large black pouch on the left, but leave the palette open on the table outside both pouches",
    "toilet_broom_towel": "position the broom beside the standing wiper, but drop the orange towel on the floor instead of on the metal toilet tissue holder",
    "remote_marker_stand": "put the marker inside the standing remote holder and the white AC remote inside the red stationery case (swapped), with the green notebook on the laptop stand",
    "makeup_red_container": "put the cosmetic items inside the red container, but leave one cosmetic item outside on the table",
}

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
seen = (set(json.load(open("results/s1_checks.json"))) | set(json.load(open("results/s2_heldout.json"))["summary"]["tasks"])
        | set(json.load(open("results/s3_tripwire.json"))["summary"]["tasks"]))
assert not seen & set(tasks), "tasks overlap spikes 1/2/3"
assert set(tasks) == set(WRONG_ACT), set(tasks) ^ set(WRONG_ACT)
goals = {c: json.loads(fetch(f"cases/{c}/metadata.json").read_text())["goal"] for c in tasks}

def seed(c):
    p = OUT / f"{c}__seed.jpg"
    if not p.exists():
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(fetch(f"human/correct/{c}/correct_1.mp4")), "-frames:v", "1", "-q:v", "2", str(p)], check=True, timeout=120)
    return p

def prompt(c, kind):
    if kind == "right": return f"Continue from this exact scene, first-person view, one hand: {goals[c]} Finish with the goal fully achieved."
    return f"Continue from this exact scene, first-person view, one hand: {WRONG_ACT[c]}. Finish with the scene left exactly like that."

def generate(job):
    c, kind = job; p = OUT / f"{c}__{kind}.mp4"; meta = OUT / f"{c}__{kind}.json"
    if p.exists() and meta.exists(): return json.loads(meta.read_text()) | {"cached": True}
    img = {"type": "image", "data": base64.b64encode(seed(c).read_bytes()).decode(), "mime_type": "image/jpeg"}
    t = time.perf_counter()
    try:
        r = beta.interactions.create(model="gemini-omni-1.2-flash", input=[img, {"type": "text", "text": prompt(c, kind)}],
                                     response_format={"type": "video", "duration": "6s"})
        wall = round(time.perf_counter() - t, 1); v = r.output_video
        if v is None or not getattr(v, "data", None):
            return {"gen_ok": False, "gen_s": wall, "status": str(r.status), "raw": str(r)[:600]}
        p.write_bytes(base64.b64decode(v.data))
        m = {"gen_ok": True, "gen_s": wall, "status": str(r.status), "bytes": p.stat().st_size, "mp4": str(p)}
        meta.write_text(json.dumps(m)); return m
    except Exception as e: return {"gen_ok": False, "gen_s": round(time.perf_counter() - t, 1), "error": str(e)[:400]}

def d1(job, g):
    c, kind = job
    if not g.get("gen_ok"): return {"error": "no clip"}
    data = base64.b64encode(pathlib.Path(g["mp4"]).read_bytes()).decode(); err = None
    for attempt in range(2):
        t = time.perf_counter()
        try:
            r = beta.decisions.create(model="gemini-decision-1", input=[
                {"type": "text", "text": "First-person video of a person doing a task."},
                {"type": "video", "data": data, "mime_type": "video/mp4", "resolution": "low"}],
                questions={"goal_reached": {"type": "noul", "instructions": f"By the end of the video, is this goal fully reached? Goal: {goals[c]}"}})
            a = r.answers["goal_reached"]
            return {"p": round(a.noul, 3), "conf": round(a.confidence, 3), "s": round(time.perf_counter() - t, 2), "attempts": attempt + 1}
        except Exception as e: err = str(e)[:300]
    return {"error": err}

jobs = [(c, k) for c in tasks for k in ("right", "wrong")]
for c in tasks: seed(c)
print(f"{len(tasks)} tasks, {len(jobs)} generations planned", flush=True)
t0 = time.perf_counter()
with cf.ThreadPoolExecutor(4) as ex: G = list(ex.map(generate, jobs))
print(f"generation done in {time.perf_counter() - t0:.0f} s", flush=True)
with cf.ThreadPoolExecutor(4) as ex: D = list(ex.map(lambda x: d1(*x), zip(jobs, G)))
out = [{"case": c, "kind": k, "prompt": prompt(c, k), "gen": g, "d1": d} for (c, k), g, d in zip(jobs, G, D)]
for o in out: print(f"{o['case'][:30]:30} {o['kind']:5} gen={o['gen'].get('gen_s')}s p={o['d1'].get('p', 'ERR')}", flush=True)
R = [o["d1"]["p"] for o in out if o["kind"] == "right" and "p" in o["d1"]]; W = [o["d1"]["p"] for o in out if o["kind"] == "wrong" and "p" in o["d1"]]
auroc = sum((r > w) + 0.5 * (r == w) for r in R for w in W) / (len(R) * len(W)) if R and W else None
gs = [o["gen"]["gen_s"] for o in out if o["gen"].get("gen_ok") and not o["gen"].get("cached")] or [o["gen"]["gen_s"] for o in out if o["gen"].get("gen_ok")]
ds = [o["d1"]["s"] for o in out if "s" in o["d1"]]
by = {c: {o["kind"]: o["d1"].get("p") for o in out if o["case"] == c} for c in tasks}
S = {"auroc_right_vs_wrong": auroc, "right_n": len(R), "wrong_n": len(W),
     "right_at_or_above_0.75": sum(p >= HI for p in R), "wrong_at_or_above_0.75": sum(p >= HI for p in W), "wrong_at_or_below_0.25": sum(p <= 0.25 for p in W),
     "pairs_right_above_wrong": sum(1 for v in by.values() if v.get("right") is not None and v.get("wrong") is not None and v["right"] > v["wrong"]),
     "p_by_task": by, "gen_ok": sum(bool(o["gen"].get("gen_ok")) for o in out), "gen_planned": len(jobs),
     "gen_failures": [{"case": o["case"], "kind": o["kind"]} | {k: v for k, v in o["gen"].items()} for o in out if not o["gen"].get("gen_ok")],
     "gen_s_p50": statistics.median(gs) if gs else None, "gen_s_max": max(gs) if gs else None,
     "d1_s_p50": statistics.median(ds) if ds else None, "d1_errors": sum("error" in o["d1"] for o in out), "tasks": tasks}
S["pass"] = bool(auroc is not None and auroc >= 0.85 and S["right_at_or_above_0.75"] >= 7)
pathlib.Path("results/s6_genjudge.json").write_text(json.dumps({"summary": S, "clips": out}, indent=2))
print(json.dumps({k: v for k, v in S.items() if k != "tasks"}, indent=2))
