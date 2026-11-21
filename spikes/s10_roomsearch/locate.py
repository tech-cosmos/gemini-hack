"""Spike 12b · Room Search locate (renumbered from 10b; files keep s10b) (idea 30). Pass mark in docs/IDEAS.md (written 13:14, before the run).
(a) locate: 10 phone-like query photos (splat renders at seeded random poses, cropped/rolled/JPEG q60) -> one Neon call
    with the query + the 40 grid renders -> nearest grid view + turn -> pose. Scored against the true pose.
(b) directions: located pose + target 3D point (ray through one ER 2 point on X) -> distance/bearing in code -> one
    Hydrogen sentence.
(c) baseline(): Hydrogen with the 40 renders as a flat list, "which image shows X, how do I get there from image k?"
Run: uv run --no-project --with google-genai==3.6.1 --with playwright --with pillow python -I spikes/s10_roomsearch/locate.py \
       .context/room.splat [render|run] [--targets "piano=v1_090,potted plant=v0_180,window=v3_000"]
'render' only renders (no model calls) so target views can be picked by eye from .context/s10b/contact.jpg.
Outputs: .context/s10b/ (renders, queries, cache) and results/s10b_locate.json."""
import base64, functools, hashlib, http.server, io, json, math, os, pathlib, random, re, shutil, statistics, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from google import genai
from PIL import Image
from playwright.sync_api import sync_playwright

SCENE, MODE = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
TARGETS = dict(kv.split("=") for kv in sys.argv[sys.argv.index("--targets") + 1].split(",")) if "--targets" in sys.argv else {}
OUT = ROOT / ".context/s10b"; OUT.mkdir(parents=True, exist_ok=True)
NEON, HYD, ER = "gemini-4-neon", "gemini-4-hydrogen", "gemini-robotics-er-2-preview"
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 180_000})
M_PER_EXTENT, STEP_M = 5.0, 0.7  # assumed scale: p5-p95 horizontal extent of the splat = 5 m; one step = 0.7 m
ADJ = {0: {1, 2, 3, 4}, 1: {0, 2, 3}, 2: {0, 1, 4}, 3: {0, 1, 4}, 4: {0, 2, 3}}  # grid positions (centre, 4 corners)
POINT = ('Point to {t}. The answer should follow the json format: [{{"point": <point>, "label": <label1>}}, ...]. '
         'The points are in [y, x] format normalized to 0-1000.')  # same prompt as spikes 8 and 10

CACHE_F = OUT / "cache.json"; CACHE = json.loads(CACHE_F.read_text()) if CACHE_F.exists() else {}
LOCK = threading.Lock()
def call(model, parts, thinking="low"):
    """One interactions call, cached on (model, parts); returns (text, seconds, cached)."""
    key = hashlib.sha256(json.dumps([model, thinking, parts]).encode()).hexdigest()
    if key in CACHE: return CACHE[key]["text"], CACHE[key]["s"], True
    t = time.perf_counter()
    r = client.interactions.create(model=model, input=parts, generation_config={"thinking_level": thinking})
    out = {"text": (r.output_text or "").strip(), "s": round(time.perf_counter() - t, 2)}
    with LOCK: CACHE[key] = out; CACHE_F.write_text(json.dumps(CACHE))
    return out["text"], out["s"], False

def img(path_or_bytes): b = path_or_bytes if isinstance(path_or_bytes, bytes) else pathlib.Path(path_or_bytes).read_bytes(); return {"type": "image", "data": base64.b64encode(b).decode(), "mime_type": "image/jpeg"}
def small(f):  # grid renders go to the models at 480x270 to keep 40 images per call cheap
    bio = io.BytesIO(); Image.open(f).resize((480, 270)).save(bio, "JPEG", quality=80); return bio.getvalue()
def jparse(t, pat=r"\{.*\}"): m = re.search(pat, t, re.S); return json.loads(m.group(0)) if m else None
def ang(a): return (a + 180) % 360 - 180  # wrap to [-180, 180)

def degrade(raw, rng):
    im = Image.open(io.BytesIO(raw)).rotate(rng.uniform(-4, 4), resample=Image.BICUBIC)
    f = rng.uniform(0.88, 0.96); w, h = im.size; cw, ch = int(w * f), int(h * f)
    x0, y0 = rng.randint(0, w - cw), rng.randint(0, h - ch)
    bio = io.BytesIO(); im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h)).save(bio, "JPEG", quality=60); return bio.getvalue()

def bearing(pos, yaw, tgt):
    """Distance (m) and bearing (deg, + = to the right) from a camera at pos/yaw to a 3D point, in the xz plane.
    three.js camera at rotation.y = yaw looks along (-sin, 0, -cos); + yaw turns left."""
    dx, dz = tgt[0] - pos[0], tgt[2] - pos[2]; y = math.radians(yaw)
    fwd = -dx * math.sin(y) - dz * math.cos(y); right = dx * math.cos(y) - dz * math.sin(y)
    return math.hypot(dx, dz) * SCALE, math.degrees(math.atan2(right, fwd))

assert abs(ang(350 - 10) + 20) < 1e-9 and ADJ[1] & ADJ[4] == {0, 2, 3}

def locate_prompt():
    parts = [{"type": "text", "text": "Below are 40 reference views of one room, rendered from a 3D scan, labelled #0 to #39. Then a QUERY photo taken by a person somewhere in the same room."}]
    for i, v in enumerate(VIEWS): parts += [{"type": "text", "text": f"#{i}"}, img(small(OUT / v["file"]))]
    return parts

def locate(query_bytes):
    parts = GRID_PARTS + [{"type": "text", "text": "QUERY:"}, img(query_bytes), {"type": "text", "text":
        "Which reference view was taken from the closest spot AND facing the most similar direction to the QUERY? "
        "Then estimate how many degrees the QUERY camera is turned to the RIGHT of that view (negative = turned left), between -45 and 45. "
        'Reply with JSON only: {"nearest": <index 0-39>, "turn_right_deg": <number>}'}]
    text, s, cached = call(NEON, parts)
    return jparse(text), text, s, cached

def baseline(obj, k):
    """Flat-photo baseline for the eval: Hydrogen sees the 40 renders as a list (no 3D, no poses). Returns dict."""
    parts = [{"type": "text", "text": "40 photos of one room, labelled #0 to #39."}]
    for i, v in enumerate(VIEWS): parts += [{"type": "text", "text": f"#{i}"}, img(small(OUT / v["file"]))]
    parts.append({"type": "text", "text": f"I am standing where photo #{k} was taken, facing the same way. Which photo shows the {obj}, "
                  f"and how do I get there from where I stand? Reply with JSON only: "
                  '{"image": <index>, "directions": "<one spoken sentence>"}'})
    text, s, cached = call(HYD, parts)
    return {"obj": obj, "from": k, "out": jparse(text), "raw": text[:400], "s": s, "cached": cached}

# serve viewer + scene over http (same as spike.py)
serve = OUT / "serve"; serve.mkdir(exist_ok=True)
html = pathlib.Path(__file__).with_name("viewer.html").read_text()
VENDOR = ROOT / ".context/vendor"  # optional local copies of the same versions (the CDN took ~5 s per module at 13:20)
if VENDOR.exists():
    html = html.replace("https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js", "./vendor/three.module.js").replace(
        "https://sparkjs.dev/releases/spark/2.4.0/spark.module.js", "./vendor/spark.module.js").replace(
        "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/", "./vendor/addons/")
    if not (serve / "vendor").exists(): os.symlink(VENDOR, serve / "vendor")
(serve / "viewer.html").write_text(html)
if not (serve / ("scene" + SCENE.suffix)).exists(): os.symlink(SCENE, serve / ("scene" + SCENE.suffix))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): pass
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(serve)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_port}/viewer.html?url=scene{SCENE.suffix}&flip=1"

res = {"scene": SCENE.name, "scale": f"p5-p95 horizontal extent = {M_PER_EXTENT} m (assumed), step = {STEP_M} m", "models": {"locate": NEON, "directions": HYD, "baseline": HYD, "point": ER}, "thinking": "low"}
t0 = time.perf_counter()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 960, "height": 540})
    pg.on("console", lambda m: m.type == "error" and print("console:", m.text[:200], flush=True)); pg.on("pageerror", lambda e: print("pageerror:", str(e)[:200], flush=True))
    pg.goto(url); pg.wait_for_function("window.ready === true", timeout=120_000)
    info = pg.evaluate("window.info"); c, lo, hi = info["p50"], info["p5"], info["p95"]
    dx, dz = 0.2 * (hi[0] - lo[0]), 0.2 * (hi[2] - lo[2])
    SCALE = M_PER_EXTENT / max(hi[0] - lo[0], hi[2] - lo[2])
    positions = [c, [c[0] + dx, c[1], c[2] + dz], [c[0] - dx, c[1], c[2] + dz], [c[0] + dx, c[1], c[2] - dz], [c[0] - dx, c[1], c[2] - dz]]
    VIEWS = [{"file": f"v{pi}_{yaw:03d}.jpg", "pi": pi, "pos": pos, "yaw": yaw} for pi, pos in enumerate(positions) for yaw in range(0, 360, 45)]
    shoot = lambda pos, yaw, pitch=0: base64.b64decode(pg.evaluate("([p, y, t]) => window.shot(p, y, t)", [pos, yaw, pitch]).split(",", 1)[1])
    for v in VIEWS:
        if not (OUT / v["file"]).exists(): (OUT / v["file"]).write_bytes(shoot(v["pos"], v["yaw"]))
    # query poses fixed by seed before any model call
    rng = random.Random(10); QUERIES = []
    for qi in range(10):
        yaw = rng.uniform(0, 360)
        while min(abs(ang(yaw - g)) for g in range(0, 360, 45)) < 10: yaw = rng.uniform(0, 360)
        pos = [c[0] + rng.uniform(-dx, dx), c[1] + rng.uniform(-0.05, 0.05) * (hi[1] - lo[1]), c[2] + rng.uniform(-dz, dz)]
        pitch = rng.uniform(-8, 8)
        f = OUT / f"q{qi}.jpg"
        if not f.exists(): f.write_bytes(degrade(shoot(pos, yaw, pitch), rng))
        else: degrade(b"" or f.read_bytes(), rng)  # keep the rng stream identical on reruns
        tp = min(range(5), key=lambda i: math.hypot(pos[0] - positions[i][0], pos[2] - positions[i][2]))
        QUERIES.append({"q": f.name, "pos": pos, "yaw": round(yaw % 360, 2), "pitch": round(pitch, 2), "true_pi": tp, "true_gyaw": round(yaw / 45) % 8 * 45})
    if not (OUT / "contact.jpg").exists():
        sheet = Image.new("RGB", (8 * 240, 5 * 135))
        for i, v in enumerate(VIEWS): sheet.paste(Image.open(OUT / v["file"]).resize((240, 135)), (i % 8 * 240, i // 8 * 135))
        sheet.save(OUT / "contact.jpg", quality=85)
    res["queries"] = QUERIES
    if MODE == "render":
        print(json.dumps(QUERIES, indent=1)); b.close(); sys.exit(0)

    # (a) locate, all 10 in parallel
    GRID_PARTS = locate_prompt()
    with ThreadPoolExecutor(10) as ex: outs = list(ex.map(lambda q: locate((OUT / q["q"]).read_bytes()), QUERIES))
    for q, (o, raw, s, cached) in zip(QUERIES, outs):
        q.update(raw=raw[:300], s=s, cached=cached)
        if not o or not isinstance(o.get("nearest"), int) or not 0 <= o["nearest"] < 40: q.update(ok=False, error="unparseable"); continue
        v = VIEWS[o["nearest"]]; turn = float(o.get("turn_right_deg") or 0)
        pred_yaw = (v["yaw"] - turn) % 360  # turned right = lower yaw
        view_ok = (v["pi"] == q["true_pi"] and abs(ang(v["yaw"] - q["true_gyaw"])) <= 45) or (v["pi"] in ADJ[q["true_pi"]] and v["yaw"] == q["true_gyaw"])
        herr = abs(ang(pred_yaw - q["yaw"]))
        q.update(pred_view=v["file"], pred_pi=v["pi"], pred_yaw=round(pred_yaw, 1), heading_err=round(herr, 1), view_ok=view_ok,
                 exact_pos=v["pi"] == q["true_pi"], ok=view_ok and herr <= 45)
        print(q["q"], "true", q["true_pi"], q["true_gyaw"], q["yaw"], "| pred", v["file"], round(pred_yaw), "| err", round(herr), "| ok", q["ok"], "|", s, "s", flush=True)
    lat = [q["s"] for q in QUERIES if "s" in q]
    res["locate"] = {"pass_n": sum(q.get("ok", False) for q in QUERIES), "n": 10, "neon_p50_s": statistics.median(lat), "neon_max_s": max(lat),
                     "exact_pos_n": sum(q.get("exact_pos", False) for q in QUERIES),
                     "heading_err_p50": statistics.median(q["heading_err"] for q in QUERIES if "heading_err" in q)}
    res["locate"]["PASS"] = res["locate"]["pass_n"] >= 8 and res["locate"]["neon_p50_s"] <= 10
    print("LOCATE", res["locate"], flush=True)

    # (b) directions: target point = ray through one ER point on X in a grid view picked by eye; start = query i
    res["directions"] = []
    for i, (obj, vf) in enumerate(TARGETS.items()):
        v = next(x for x in VIEWS if x["file"] == vf + ".jpg"); q = QUERIES[i]
        t = time.perf_counter(); text, er_s, _ = call(ER, [img(OUT / v["file"]), {"type": "text", "text": POINT.format(t=obj)}])
        pt = jparse(text, r"\[.*\]")[0]["point"]
        shoot(v["pos"], v["yaw"]); hit = pg.evaluate("([x, y]) => window.ray(x, y)", [pt[1] / 1000, pt[0] / 1000])
        d = {"obj": obj, "target_view": vf, "er_point_yx": pt, "er_s": er_s, "hit": hit, "from_query": q["q"]}
        if not isinstance(hit, list): d["error"] = f"no ray hit: {hit}"; res["directions"].append(d); continue
        true_m, true_b = bearing(q["pos"], q["yaw"], hit)
        d.update(true_m=round(true_m, 2), true_bearing=round(true_b, 1))
        if q.get("pred_view"):
            pv = next(x for x in VIEWS if x["file"] == q["pred_view"])
            m, br = bearing(pv["pos"], q["pred_yaw"], hit)
            side = "right" if br > 0 else "left"
            facts = (f"Target: the {obj}. From where the person stands it is {abs(br):.0f} degrees to their {side} "
                     f"({'roughly straight ahead' if abs(br) < 20 else 'behind them' if abs(br) > 150 else 'turn ' + side}), about {m / STEP_M:.0f} steps away (~{m:.1f} m).")
            sent, hs, _ = call(HYD, [img(OUT / v["file"]), {"type": "text", "text": facts + " The image shows the target. "
                "Write ONE short spoken sentence of walking directions using these facts, and name one landmark next to the target that is visible in the image. Sentence only."}])
            d.update(pred_m=round(m, 2), pred_bearing=round(br, 1), dist_err_m=round(abs(m - true_m), 2), bearing_err=round(abs(ang(br - true_b)), 1),
                     facts=facts, sentence=sent, hydrogen_s=hs)
        print("DIR", json.dumps(d), flush=True); res["directions"].append(d)

    # (c) baseline smoke: same 3 objects, start = the same query's true nearest grid view
    jobs = [(obj, VIEWS.index(next(x for x in VIEWS if x["pi"] == QUERIES[i]["true_pi"] and x["yaw"] == QUERIES[i]["true_gyaw"]))) for i, obj in enumerate(TARGETS)]
    with ThreadPoolExecutor(3) as ex: res["baseline"] = list(ex.map(lambda j: baseline(*j), jobs))
    for r in res["baseline"]:
        if r["out"] and isinstance(r["out"].get("image"), int) and 0 <= r["out"]["image"] < 40: r["image_file"] = VIEWS[r["out"]["image"]]["file"]
        print("BASE", json.dumps(r), flush=True)
    b.close()
res["total_s"] = round(time.perf_counter() - t0, 1)
(ROOT / "results").mkdir(exist_ok=True)
json.dump(res, open(ROOT / "results/s10b_locate.json", "w"), indent=1)
print("wrote results/s10b_locate.json", res["total_s"], "s")
