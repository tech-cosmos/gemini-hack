"""Spike 10 · Room Search (idea 30). Pass mark in docs/IDEAS.md (written 13:08, before the run).
Render 40 views of a Gaussian splat headless (5 positions x 8 headings), then per named object:
Decision 1 "is <X> clearly visible?" on all 40 in parallel -> top view -> Robotics-ER 2 points 3x -> dots drawn for an
eye check -> ray to the splat surface for a 3D spot.
Run: uv run --no-project --with google-genai==3.6.1 --with playwright python -I spikes/s10_roomsearch/spike.py \
       <scene.splat|.ply|.spz> <tag> "<object 1>" "<object 2>" "<object 3>" [--flip0] [--headed]
Outputs: .context/s10/<tag>/ (renders, dotted top views) and results/s10_roomsearch_<tag>.json."""
import base64, functools, http.server, json, os, pathlib, re, shutil, statistics, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from google import genai
from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SCENE, TAG, OBJECTS = pathlib.Path(args[0]).resolve(), args[1], args[2:]
FLIP, HEADED = "--flip0" not in sys.argv, "--headed" in sys.argv
OUT = ROOT / ".context/s10" / TAG; OUT.mkdir(parents=True, exist_ok=True)
FF, ER = "/opt/homebrew/bin/ffmpeg", "gemini-robotics-er-2-preview"
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 60_000})
POINT = ('Point to {t}. The answer should follow the json format: [{{"point": <point>, "label": <label1>}}, ...]. '
         'The points are in [y, x] format normalized to 0-1000.')  # same prompt as spike 8

# serve viewer + scene from one temp dir (the browser needs http, not file://)
serve = OUT / "serve"; serve.mkdir(exist_ok=True)
shutil.copy(pathlib.Path(__file__).with_name("viewer.html"), serve / "viewer.html")
scene_name = "scene" + SCENE.suffix
if not (serve / scene_name).exists(): os.symlink(SCENE, serve / scene_name)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): pass
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(serve)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_port}/viewer.html?url={scene_name}&flip={int(FLIP)}"

res = {"scene": SCENE.name, "tag": TAG, "objects": OBJECTS, "headed": HEADED, "views": [], "queries": {}}
t0 = time.perf_counter()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=not HEADED, args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 960, "height": 540})
    pg.on("console", lambda m: m.type == "error" and print("console:", m.text[:200]))
    pg.goto(url); pg.wait_for_function("window.ready === true", timeout=300_000)
    info = pg.evaluate("window.info"); res["load_s"] = round(time.perf_counter() - t0, 2); res["info"] = info
    print("loaded", info, res["load_s"], "s", flush=True)
    c, lo, hi = info["p50"], info["p5"], info["p95"]
    dx, dz = 0.2 * (hi[0] - lo[0]), 0.2 * (hi[2] - lo[2])
    positions = [c, [c[0] + dx, c[1], c[2] + dz], [c[0] - dx, c[1], c[2] + dz], [c[0] + dx, c[1], c[2] - dz], [c[0] - dx, c[1], c[2] - dz]]
    t1 = time.perf_counter()
    for pi, pos in enumerate(positions):
        for yaw in range(0, 360, 45):
            data = pg.evaluate("([p, y]) => window.shot(p, y, 0)", [pos, yaw])
            f = OUT / f"v{pi}_{yaw:03d}.jpg"; f.write_bytes(base64.b64decode(data.split(",", 1)[1]))
            res["views"].append({"file": f.name, "pos": pos, "yaw": yaw})
    res["render_s"] = round(time.perf_counter() - t1, 2); print("rendered 40 views in", res["render_s"], "s", flush=True)
    subprocess.run([FF, "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", str(OUT / "v*_*.jpg"),
                    "-vf", "scale=240:-1,tile=8x5", "-frames:v", "1", str(OUT / "contact.jpg")], timeout=60)

    def jpg(name): return base64.b64encode((OUT / name).read_bytes()).decode()

    def visible(view, obj):
        t = time.perf_counter()
        try:
            r = client.decisions.create(model="gemini-decision-1",
                input=[{"type": "text", "text": "One camera view of a room."}, {"type": "image", "data": jpg(view["file"]), "mime_type": "image/jpeg", "resolution": "low"}],
                questions={"vis": {"type": "noul", "instructions": f"Is {obj} clearly visible in this image?"}})
            return {"file": view["file"], "p": round(r.answers["vis"].noul, 3), "s": round(time.perf_counter() - t, 2)}
        except Exception as e: return {"file": view["file"], "p": -1, "error": str(e)[:160], "s": round(time.perf_counter() - t, 2)}

    def point(name, obj):
        t = time.perf_counter()
        try:
            r = client.interactions.create(model=ER, input=[{"type": "image", "data": jpg(name), "mime_type": "image/jpeg"},
                {"type": "text", "text": POINT.format(t=obj)}], generation_config={"thinking_level": "low"})
            m = re.search(r"\[.*\]", r.output_text or "", re.S)
            return {"s": round(time.perf_counter() - t, 2), "out": json.loads(m.group(0)) if m else None, "raw": (r.output_text or "")[:300]}
        except Exception as e: return {"s": round(time.perf_counter() - t, 2), "error": str(e)[:160]}

    for obj in OBJECTS:
        tq = time.perf_counter()
        with ThreadPoolExecutor(20) as ex: scores = list(ex.map(lambda v: visible(v, obj), res["views"]))
        t_dec = time.perf_counter() - tq
        top = max(scores, key=lambda s: s["p"])
        with ThreadPoolExecutor(3) as ex: calls = list(ex.map(lambda _: point(top["file"], obj), range(3)))
        t_query = t_dec + calls[0]["s"]  # pass mark: Decision 1 over 40 views + one ER call
        pts = [cl["out"][0]["point"] for cl in calls if cl.get("out")]
        # ray needs the camera at the top view again
        v = next(x for x in res["views"] if x["file"] == top["file"]); pg.evaluate("([p, y]) => window.shot(p, y, 0, 2)", [v["pos"], v["yaw"]])
        rays = [pg.evaluate("([x, y]) => window.ray(x, y)", [pt[1] / 1000, pt[0] / 1000]) for pt in pts]
        cols = ["red", "lime", "cyan"]
        vf = ",".join(f"drawbox=x=iw*{x}/1000-10:y=ih*{y}/1000-10:w=20:h=20:color={cols[i]}:t=4" for i, (y, x) in enumerate(pts)) or "null"
        slug = re.sub(r"\W+", "_", obj).strip("_")
        subprocess.run([FF, "-loglevel", "error", "-y", "-i", str(OUT / top["file"]), "-vf", vf, str(OUT / f"top_{slug}.jpg")], timeout=60)
        ranked = sorted(scores, key=lambda s: -s["p"])
        res["queries"][obj] = {"top": top, "top5": ranked[:5], "decision_wall_s": round(t_dec, 2), "query_s": round(t_query, 2),
                               "er_calls": calls, "rays": rays, "errors": sum("error" in s for s in scores), "dotted": f"top_{slug}.jpg"}
        print(obj, "| top", top["file"], top["p"], "| next", [(s["file"], s["p"]) for s in ranked[1:3]], "| query", round(t_query, 2), "s | pts", pts, "| rays", rays, flush=True)
    b.close()
qs = [q["query_s"] for q in res["queries"].values()]
res["query_p50_s"] = round(statistics.median(qs), 2) if qs else None
res["total_s"] = round(time.perf_counter() - t0, 2)
(ROOT / "results").mkdir(exist_ok=True)
json.dump(res, open(ROOT / f"results/s10_roomsearch_{TAG}.json", "w"), indent=1)
print("query p50", res["query_p50_s"], "s; total", res["total_s"], "s; eye-check", OUT)
