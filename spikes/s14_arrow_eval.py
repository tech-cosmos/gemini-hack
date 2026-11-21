"""Spike 14: arrow eval for Ghost Hands (idea 25, issue #16). Can Robotics-ER 2 point at WHERE an item should go?
20 ego2act correct_1 clips (ranks 60-79 of spike 2's length ranking). Prediction on the FIRST frame (ER 2, and
Hydrogen as baseline); truth = ER 2 pointing at the object on the LAST frame, checked by eye. Error in 0-1000 units.
Pass mark in docs/IDEAS.md (written before the run).
Run: .venv/bin/python spikes/s14_arrow_eval.py prep   (fetch clips, cut frames, print goals; no model calls)
     .venv/bin/python spikes/s14_arrow_eval.py        (model calls, cached in .context/s14/cache.json)
     .venv/bin/python spikes/s14_arrow_eval.py judge  (no calls: applies the by-eye DROP / SHIFT lists, scores, draws)"""
import base64, concurrent.futures as cf, csv, faulthandler, glob, io, json, math, os, pathlib, re, statistics, subprocess, sys, time, urllib.request
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(900, exit=True)
ER, HY, FF = "gemini-robotics-er-2-preview", "gemini-4-hydrogen", "/opt/homebrew/bin/ffmpeg"
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE, D = pathlib.Path(".context/ego2act"), pathlib.Path(".context/s14"); D.mkdir(parents=True, exist_ok=True)
START, N, HIT = 60, 20, 120
MODE = sys.argv[1] if len(sys.argv) > 1 else "run"

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
seen = set(json.load(open("results/s1_checks.json")))
for f in ["results/s2_heldout.json", "results/s3_tripwire.json"] + glob.glob("results/s6_*.json") + glob.glob("results/s7_*.json"):
    j = json.load(open(f)); seen |= set(j.get("summary", {}).get("tasks", [])) | {c.get("case") for c in j.get("clips", []) if isinstance(c, dict)}
assert not seen & set(tasks), f"overlap with earlier spikes: {seen & set(tasks)}"
with cf.ThreadPoolExecutor(8) as ex:
    list(ex.map(lambda c: (fetch(f"cases/{c}/metadata.json"), fetch(f"human/correct/{c}/correct_1.mp4")), tasks))
goals = {c: json.loads(fetch(f"cases/{c}/metadata.json").read_text())["goal"] for c in tasks}
for c in tasks:
    v = str(fetch(f"human/correct/{c}/correct_1.mp4"))
    if not (D / f"{c}_first.png").exists():
        subprocess.run([FF, "-loglevel", "error", "-y", "-i", v, "-frames:v", "1", str(D / f"{c}_first.png")], check=True, timeout=60)
    if not (D / f"{c}_last.png").exists():
        subprocess.run([FF, "-loglevel", "error", "-y", "-sseof", "-0.3", "-i", v, "-update", "1", str(D / f"{c}_last.png")], check=True, timeout=60)
if MODE == "prep":
    for i, c in enumerate(tasks): print(START + i, c, "|", goals[c])
    print(len(seen), "earlier tasks checked, no overlap"); sys.exit()

# FROZEN before any pointing call: (object that moves, destination) read from the goal text only
TARGETS = {}
# (object, destination, what ER 2 points at on the last frame, kind). kind "visible" = the object itself should be
# visible at the end; "proxy" = the object ends hidden/poured/ambiguous, so truth is its container (weaker truth).
# 65's object name comes from the case id (the goal only says "all items").
TARGETS = {
 "sanitary_face_wash": ("the white tube", "inside the pink pouch", "the pink pouch", "proxy"),
 "mug_kitchen": ("the metal lid", "on the yellow mug", "the metal lid", "visible"),
 "pour_milk": ("the milk", "into the cup", "the cup", "proxy"),
 "figurine_toy_box": ("the cat figurine", "on top of the bowl", "the cat figurine", "visible"),
 "desk_mat_tablet": ("the book", "on top of the tablet", "the book", "visible"),
 "controller_watch_ring": ("the game controller", "on top of the closed aqua green container", "the game controller", "visible"),
 "air_freshener_dispenser": ("the green air freshener", "in the automatic dispenser", "the automatic dispenser", "proxy"),
 "toiletries_container": ("the toothbrush", "left compartment of the grey container", "the grey container", "proxy"),
 "paper_binder_book": ("the red book", "on top of the closed ring binder", "the red book", "visible"),
 "trophy_luggage": ("the racket", "on top of the piano table", "the racket", "visible"),
 "racket_backpack": ("the tennis racket", "inside the front backpack compartment", "the tennis racket", "visible"),
 "sauce_tissue": ("the fork", "on the plate", "the fork", "visible"),
 "three_caps": ("the loose marker caps", "on the markers", "the markers", "proxy"),
 "toothbrush_trimmer": ("the toothbrush", "inside the white basket", "the toothbrush", "visible"),
 "egg_candy_air_fryer": ("the bowl", "inside the air fryer", "the air fryer", "proxy"),
 "cutlery_sorting": ("the cutlery from inside the container", "the outside compartments", "the cutlery in the outside compartments", "proxy"),
 "hanger_grouping": ("the black hangers", "right side of the pole", "the group of black hangers", "visible"),
 "hat_sorting": ("the green hat", "third hook from the left", "the green hat", "visible"),
 "coffee_beans": ("the coffee beans", "inside the orange jar", "the orange jar", "proxy"),
 "screwdriver_wrench": ("the orange glove", "on top of the closed green container", "the orange glove", "visible"),
}
assert set(TARGETS) == set(tasks)
FMT = (' The answer should follow the json format: [{{"point": <point>, "label": <label1>}}, ...]. '
       'The points are in [y, x] format normalized to 0-1000.')
PRED = "Point to the spot where {o} should be placed to achieve: {g}. Return exactly one point." + FMT
TRUTH = "Point to {o}." + FMT
# by-eye lists, filled in after looking at .context/s14/sheet.png (judge mode); empty during the run
DROP = {}    # case -> why the truth point is wrong
SHIFT = []   # cases with a big first->last camera shift

CJ = D / "cache.json"; cache = json.loads(CJ.read_text()) if CJ.exists() else {}
def call(key, model, img, prompt):
    if key in cache and "error" not in cache[key]: return cache[key]
    from google import genai
    client = genai.Client(http_options={"api_version": "v1beta", "timeout": 90_000})
    b = base64.b64encode((D / img).read_bytes()).decode(); t = time.perf_counter()
    try:
        r = client.interactions.create(model=model, input=[{"type": "image", "data": b, "mime_type": "image/png"},
            {"type": "text", "text": prompt}], generation_config={"thinking_level": "low"})
        s = round(time.perf_counter() - t, 2); txt = r.output_text or ""
        m = re.search(r"\[.*\]", txt, re.S); out = json.loads(m.group(0)) if m else None
        pt = out[0]["point"] if out and isinstance(out[0], dict) else (out if out and len(out) == 2 and not isinstance(out[0], (list, dict)) else None)
        return {"s": s, "point": pt, "raw": txt[:300]}
    except Exception as e: return {"s": round(time.perf_counter() - t, 2), "error": str(e)[:200]}

if MODE == "run":
    jobs = []
    for c in tasks:
        o, dest, tr, _ = TARGETS[c]
        jobs += [(f"{c}|er_pred", ER, f"{c}_first.png", PRED.format(o=o, g=goals[c])),
                 (f"{c}|hy_pred", HY, f"{c}_first.png", PRED.format(o=o, g=goals[c])),
                 (f"{c}|truth", ER, f"{c}_last.png", TRUTH.format(o=tr))]
    with cf.ThreadPoolExecutor(4) as ex:
        for (k, *_), r in zip(jobs, ex.map(lambda j: call(*j), jobs)):
            cache[k] = r; print(k, r.get("s"), r.get("point"), r.get("error", ""), flush=True)
    CJ.write_text(json.dumps(cache, indent=1))

from PIL import Image, ImageDraw
def dot(dr, im, pt, col):
    if not pt: return
    y, x = pt[0] * im.height / 1000, pt[1] * im.width / 1000
    dr.ellipse([x - 14, y - 14, x + 14, y + 14], outline=col, width=5); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=col)
def dist(a, b): return round(math.hypot(a[0] - b[0], a[1] - b[1]), 1) if a and b else None
per, tiles = [], []
for i, c in enumerate(tasks):
    o, dest, tr, kind = TARGETS[c]; e, h, t = (cache.get(f"{c}|{k}", {}) for k in ("er_pred", "hy_pred", "truth"))
    r = {"rank": START + i, "case": c, "goal": goals[c], "object": o, "destination": dest, "truth_target": tr, "kind": kind,
         "er_pred": e, "hy_pred": h, "truth": t, "er_err": dist(e.get("point"), t.get("point")), "hy_err": dist(h.get("point"), t.get("point")),
         "truth_dropped": DROP.get(c), "camera_shift": c in SHIFT}
    per.append(r)
    a = Image.open(D / f"{c}_first.png").convert("RGB"); b = Image.open(D / f"{c}_last.png").convert("RGB")
    da, db = ImageDraw.Draw(a), ImageDraw.Draw(b)
    dot(da, a, t.get("point"), "lime"); dot(da, a, h.get("point"), "yellow"); dot(da, a, e.get("point"), "red"); dot(db, b, t.get("point"), "lime")
    a.save(D / f"ann_{c}_first.png")
    W = 480; a = a.resize((W, W * a.height // a.width)); b = b.resize((W, W * b.height // b.width))
    tile = Image.new("RGB", (2 * W, a.height + 34), "black"); tile.paste(a, (0, 34)); tile.paste(b, (W, 34))
    ImageDraw.Draw(tile).text((4, 2), f"{START+i} {c}: {o} -> {dest}\nred=ER2 {r['er_err']}  yellow=Hydrogen {r['hy_err']}  lime=truth ({tr}, last frame at right)"
                              + ("  DROPPED" if c in DROP else "") + ("  SHIFT" if c in SHIFT else ""), fill="white")
    tiles.append(tile)
th = max(t.height for t in tiles); sheet = Image.new("RGB", (1920, th * 10), "black")
for i, t in enumerate(tiles): sheet.paste(t, ((i % 2) * 960, (i // 2) * th))
sheet.save(D / "sheet.png")
for k in range(4): sheet.crop((0, k * th * 10 // 4, 1920, (k + 1) * th * 10 // 4)).save(D / f"sheet_part{k}.png")

def score(rs):
    o = {"n": len(rs)}
    for m in ("er", "hy"):
        es = [r[f"{m}_err"] for r in rs if r[f"{m}_err"] is not None]
        o[m] = {"n_scored": len(es), "hits": sum(x <= HIT for x in es), "hit_rate": (sum(x <= HIT for x in es) / len(rs)) if rs else None,
                "median_err": statistics.median(es) if es else None}
    return o
kept = [r for r in per if not r["truth_dropped"] and r["truth"].get("point")]
lat = lambda k: [r[k]["s"] for r in per if "s" in r[k] and "error" not in r[k]]
S = {"hit_threshold": HIT, "n_tasks": len(per), "n_dropped": len(per) - len(kept), "dropped": {r["case"]: r["truth_dropped"] or "no truth point" for r in per if r not in kept},
     "camera_shift_cases": SHIFT, "all_kept": score(kept), "no_camera_shift": score([r for r in kept if not r["camera_shift"]]),
     "visible_truth_only": score([r for r in kept if r["kind"] == "visible"]),
     "visible_no_shift": score([r for r in kept if r["kind"] == "visible" and not r["camera_shift"]]),
     "latency_s": {k: {"n": len(lat(k)), "p50": statistics.median(lat(k)), "min": min(lat(k)), "max": max(lat(k))} for k in ("er_pred", "hy_pred", "truth") if lat(k)},
     "errors": {k: sum("error" in r[k] for r in per) for k in ("er_pred", "hy_pred", "truth")},
     "judged_by_eye": MODE == "judge", "models": {"er": ER, "baseline": HY}, "thinking_level": "low", "tasks": tasks}
a = S["all_kept"]; er, hy = a["er"]["hit_rate"], a["hy"]["hit_rate"]
S["pass"] = bool(er >= 0.65 and er - hy >= 0.15 and S["latency_s"]["er_pred"]["p50"] <= 3); S["kill"] = bool(er <= hy)
pathlib.Path("results/s14_arrow_eval.json").write_text(json.dumps({"summary": S, "tasks": per}, indent=1))
print(json.dumps({k: v for k, v in S.items() if k != "tasks"}, indent=1))
