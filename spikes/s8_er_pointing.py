"""Spike 8: Gemini Robotics-ER 2 pointing on 5 real ego2act frames + 5 generated frames.
3 calls per frame with the documented pointing prompt, each timed; points drawn with ffmpeg into .context/s8/.
Hit or miss is judged by eye afterwards (HITS below is filled in by hand after looking at the PNGs).
Pass mark in docs/IDEAS.md (written 12:52). Run: .venv/bin/python spikes/s8_er_pointing.py
Then, after looking: .venv/bin/python spikes/s8_er_pointing.py judge (no API calls, adds the by-eye verdicts to the JSON)."""
import base64, faulthandler, json, os, pathlib, re, statistics, subprocess, sys, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(900, exit=True)
from google import genai
MODEL, LEVEL, FF = "gemini-robotics-er-2-preview", "low", "/opt/homebrew/bin/ffmpeg"
D = pathlib.Path(".context/s8"); IN = D / "in"
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 60_000})  # 404 "model not found" without v1beta
# targets fixed before any model output; genie frames are the left 640x360 view of the 3-view strip
FRAMES = [("real_banknote_card_coin", "the wallet"), ("real_butter_candy_mug", "the metal spoon"),
          ("real_coffee_plate_bottle", "the grey lid of the coffee container"), ("real_eyedrop_chapstick", "the chapstick"),
          ("real_headphone_mouse_book", "the headphone stand"), ("gen_genie", "the blue water bottle"),
          ("gen_genie_seed", "the black coffee can"), ("gen_matryoshka", "the largest matryoshka doll"),
          ("gen_t2v", "the white mug"), ("gen_eyeshadow", "the eyeshadow palette")]
POINT = ('Point to {t}. The answer should follow the json format: [{{"point": <point>, "label": <label1>}}, ...]. '
         'The points are in [y, x] format normalized to 0-1000.')
TRAJ = ('Generate a trajectory for the hand to move from the bottom centre of the image to {t}. Return a list of at most 5 '
        'waypoints as JSON: [{{"step": <int>, "point": [y, x], "action": <description>}}, ...] where coordinates are normalized to 0-1000.')

# by-eye verdicts, filled in after the run from .context/s8/<name>.png: calls (of 3) whose point lies on the target
HITS = {"real_banknote_card_coin": 3, "real_butter_candy_mug": 3, "real_coffee_plate_bottle": 3, "real_eyedrop_chapstick": 3,
        "real_headphone_mouse_book": 3, "gen_genie": 3, "gen_genie_seed": 3, "gen_matryoshka": 3, "gen_t2v": 3, "gen_eyeshadow": 3}
if sys.argv[1:] == ["judge"]:
    res = json.load(open("results/s8_er_pointing.json"))
    for k, f in res["frames"].items(): f["calls_on_target_by_eye"] = HITS[k]; f["hit"] = HITS[k] >= 2
    n = sum(f["hit"] for f in res["frames"].values())
    res["judged"] = {"frames_on_target": n, "of": len(res["frames"]), "how": "by eye on the annotated PNGs, majority of 3 calls",
                     "pass": n >= 8 and res["latency"]["p50"] <= 2.5}
    json.dump(res, open("results/s8_er_pointing.json", "w"), indent=1); print(res["judged"], res["latency"]); sys.exit()

def call(name, prompt, level=LEVEL):
    img = base64.b64encode((IN / f"{name}.png").read_bytes()).decode(); t = time.perf_counter()
    try:
        r = client.interactions.create(model=MODEL, input=[{"type": "image", "data": img, "mime_type": "image/png"},
            {"type": "text", "text": prompt}], generation_config={"thinking_level": level})
        s = round(time.perf_counter() - t, 2); txt = r.output_text or ""
        m = re.search(r"\[.*\]", txt, re.S)
        return {"s": s, "out": json.loads(m.group(0)) if m else None, "raw": txt[:400]}
    except Exception as e: return {"s": round(time.perf_counter() - t, 2), "error": str(e)[:160]}

def draw(name, pts, out):
    cols = ["red", "lime", "cyan", "yellow", "magenta"]
    vf = ",".join(f"drawbox=x=iw*{x}/1000-9:y=ih*{y}/1000-9:w=18:h=18:color={cols[i % 5]}:t=4,"
                  f"drawbox=x=iw*{x}/1000-2:y=ih*{y}/1000-2:w=4:h=4:color={cols[i % 5]}:t=fill" for i, (y, x) in enumerate(pts)) or "null"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", str(IN / f"{name}.png"), "-vf", vf, str(out)], check=True, timeout=60)

res = {"model": MODEL, "thinking_level": LEVEL, "api": "client.interactions.create", "frames": {}}
for name, tgt in FRAMES:
    calls = [call(name, POINT.format(t=tgt)) for _ in range(3)]
    pts = [c["out"][0]["point"] for c in calls if c.get("out")]
    draw(name, pts, D / f"{name}.png")
    res["frames"][name] = {"target": tgt, "calls": calls}
    print(name, tgt, [(c["s"], (c.get("out") or [{}])[0].get("point"), c.get("error")) for c in calls], flush=True)
lat = [c["s"] for f in res["frames"].values() for c in f["calls"] if "error" not in c]
res["latency"] = {"n": len(lat), "p50": round(statistics.median(lat), 2), "max": max(lat), "min": min(lat),
                  "errors": sum("error" in c for f in res["frames"].values() for c in f["calls"])}
t = call("real_eyedrop_chapstick", TRAJ.format(t="the chapstick")); res["trajectory"] = t
if t.get("out"): draw("real_eyedrop_chapstick", [w["point"] for w in t["out"]], D / "traj_real_eyedrop_chapstick.png")
res["levels_probe"] = {lv: call("real_eyedrop_chapstick", POINT.format(t="the chapstick"), lv) for lv in ("minimal", "medium", "high")}
print(json.dumps({k: res[k] for k in ("latency", "trajectory", "levels_probe")}, indent=1)[:2500])
json.dump(res, open("results/s8_er_pointing.json", "w"), indent=1)
