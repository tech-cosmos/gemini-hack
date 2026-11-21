"""Spike 11 · Dream vs Twin (idea 30, act B). The splat (true geometry) grades Genie 4 (invents what is outside its seed).
Pass mark in docs/IDEAS.md (written 13:13, before any model output).
Per pose: splat render at P, h seeds Genie 4; hold arrow_left 2 s; Genie's last frame vs splat at P, h + angle (truth).
Angle calibrated once on a separate pose with one Neon call, then frozen. Baseline: Nano Banana edits the same render.
Judge: one Neon call per pair. Sanity: truth i vs Genie frame of pose i+1 must be "different".
Run: uv run --no-project --with google-genai==3.6.1 --with playwright python spikes/s11_dreamtwin.py <scene.splat> [tag=room]
v2:  S11_HOLD_FRAMES=48 uv run ... spikes/s11_dreamtwin.py <scene.splat> room_v2
Outputs: .context/s11/<tag>/ (renders, frames, strips) and results/s11_dreamtwin[_<tag>].json. Steps cache their files."""
import asyncio, base64, functools, http.server, json, os, pathlib, re, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from google import genai
from playwright.sync_api import sync_playwright

SCENE = pathlib.Path(sys.argv[1]).resolve(); TAG = sys.argv[2] if len(sys.argv) > 2 else "room"
OUT = ROOT / ".context/s11" / TAG; OUT.mkdir(parents=True, exist_ok=True)
RES = ROOT / ("results/s11_dreamtwin.json" if TAG == "room" else f"results/s11_dreamtwin_{TAG}.json")
FF, NEON, NB = "/opt/homebrew/bin/ffmpeg", "gemini-4-neon", "gemini-nano-banana-2.1"
HOLD_S, CAND = 2.0, list(range(15, 181, 15))
# v2 (after the fact, one change): hold arrow_left until HOLD_FRAMES frames arrive (Genie starved to 0-1 frames per 2 s with 4 sessions at once), one session at a time
HOLD_FRAMES = int(os.environ.get("S11_HOLD_FRAMES", 0)); PAR = 1 if HOLD_FRAMES else 4
WORLD = "first-person view of this exact room"
JUDGE = "Do these two images show the same part of the same room with the same objects? Answer yes/no and name what differs."
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 300_000})
b64 = lambda b: base64.b64encode(b).decode()
img = lambda p: {"type": "image", "data": b64(pathlib.Path(p).read_bytes()), "mime_type": "image/jpeg"}
res: dict = json.loads(RES.read_text()) if RES.exists() else {"scene": SCENE.name, "tag": TAG, "pass_mark_written": "13:13"}
save = lambda: (RES.parent.mkdir(exist_ok=True), RES.write_text(json.dumps(res, indent=1)))

def render(jobs):
    """jobs: [(file, pos, yaw)] rendered 1280x720 from the s10 viewer; returns window.info."""
    serve = OUT / "serve"; serve.mkdir(exist_ok=True)
    shutil.copy(ROOT / "spikes/s10_roomsearch/viewer.html", serve / "viewer.html")
    name = "scene" + SCENE.suffix
    if not (serve / name).exists(): os.symlink(SCENE, serve / name)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(serve)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True, args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(f"http://127.0.0.1:{httpd.server_port}/viewer.html?url={name}&w=1280&h=720&fov=60")
        pg.wait_for_function("window.ready === true", timeout=300_000)
        info = pg.evaluate("window.info")
        for f, pos, yaw in jobs:
            (OUT / f).write_bytes(base64.b64decode(pg.evaluate("([p, y]) => window.shot(p, y, 0)", [pos, yaw]).split(",", 1)[1]))
        b.close()
    httpd.shutdown()
    return info

async def genie(seed, name):
    """Seed Genie with the render, hold arrow_left HOLD_S s after the first frame, keep first + last frame."""
    st = {"latest": None, "n": 0}; out = {"name": name}; t0 = time.perf_counter()
    try:
        it = await client.aio.interactions.create(model="genie-4", api_version="v1beta")
        async with client.aio.interactions.connect(it.id, api_version="v1beta") as s:
            await s.send({"event_type": "world_setup", "world_prompt": {"text": WORLD},
                          "reference_image": {"mime_type": "image/jpeg", "data": b64(seed.read_bytes())}})
            async def recv():
                async for ev in s.receive():
                    if ev.event_type == "step.delta" and getattr(ev.delta, "type", None) == "video" and ev.delta.data:
                        st["n"] += 1; st["latest"] = base64.b64decode(ev.delta.data)
                    elif ev.event_type in ("interaction.completed", "error", "interaction.failed"):
                        if ev.event_type != "interaction.completed": out["event"] = str(ev)[:300]
                        return
            async def drive():
                while st["latest"] is None: await asyncio.sleep(0.02)
                out["first_frame_s"] = round(time.perf_counter() - t0, 2)
                (OUT / f"{name}_genie_t0.jpg").write_bytes(st["latest"]); n0 = st["n"]
                await s.send({"event_type": "user_action", "action": "key_down", "input": "arrow_left"})
                if HOLD_FRAMES:
                    th = time.perf_counter()
                    while st["n"] - n0 < HOLD_FRAMES and time.perf_counter() - th < 15: await asyncio.sleep(0.01)
                    out["hold_s"] = round(time.perf_counter() - th, 2)
                else: await asyncio.sleep(HOLD_S)
                await s.send({"event_type": "user_action", "action": "key_up", "input": "arrow_left"})
                await asyncio.sleep(0.3)
                (OUT / f"{name}_genie.jpg").write_bytes(st["latest"]); out["frames_during_hold"] = st["n"] - n0
                await s.complete()  # once only
            rt = asyncio.create_task(recv())
            try: await asyncio.wait_for(drive(), 40)
            except Exception as e:
                out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
                try: await s.complete()
                except Exception: pass
            try: await asyncio.wait_for(rt, 10)
            except Exception: rt.cancel()
    except Exception as e: out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    out |= {"frames": st["n"], "wall_s": round(time.perf_counter() - t0, 2), "ok": (OUT / f"{name}_genie.jpg").exists() and "error" not in out}
    print("genie", json.dumps(out), flush=True); return out

async def genie_all(jobs, par=PAR):
    sem = asyncio.Semaphore(par)
    async def one(seed, name):
        async with sem: return await genie(seed, name)
    return await asyncio.gather(*[one(s, n) for s, n in jobs])

def neon(inp, tries=3):
    txt = ""
    for i in range(tries):
        t = time.perf_counter()
        try:
            txt = (client.interactions.create(model=NEON, input=inp).output_text or "").strip()
            if txt: return txt, round(time.perf_counter() - t, 2)
        except Exception as e: txt = f"ERROR {str(e)[:200]}"
        time.sleep(2 * (i + 1))
    return txt, None

def judge(a, b):
    txt, s = neon([{"type": "text", "text": "Image 1:"}, img(a), {"type": "text", "text": "Image 2:"}, img(b), {"type": "text", "text": JUDGE}])
    m = re.match(r"\W*(yes|no)\b", txt, re.I)
    return {"a": pathlib.Path(a).name, "b": pathlib.Path(b).name, "same": (m.group(1).lower() == "yes") if m else None, "reply": txt[:400], "s": s}

def banana(src, angle, dst):
    t, err = time.perf_counter(), ""
    for i in range(3):
        try:
            r = client.interactions.create(model=NB, input=[img(src), {"type": "text", "text": f"Show the view after turning left by {angle} degrees."}])
            o = r.output_image
            if o is not None and getattr(o, "data", None):
                dst.write_bytes(base64.b64decode(o.data) if isinstance(o.data, str) else o.data)
                return {"file": dst.name, "ok": True, "mime": getattr(o, "mime_type", None), "s": round(time.perf_counter() - t, 1)}
            err = f"no image: {str(r)[:200]}"
        except Exception as e: err = str(e)[:200]
    return {"file": dst.name, "ok": False, "error": err, "s": round(time.perf_counter() - t, 1)}

def strip(files, dst):
    ins = sum((["-i", str(f)] for f in files), [])
    fc = "".join(f"[{i}:v]scale=480:270,setsar=1[s{i}];" for i in range(len(files))) + "".join(f"[s{i}]" for i in range(len(files))) + f"hstack={len(files)}"
    subprocess.run([FF, "-y", "-v", "error", *ins, "-filter_complex", fc, "-frames:v", "1", str(dst)], timeout=60)

if __name__ == "__main__":
    t_all = time.perf_counter()
    # 1. poses by rule (written in the pass mark): 5x2 grid over the p5-p95 box, y = p50, h = 36 deg * i; calibration at centre, h 90
    if "poses" not in res:
        info = render([])
        lo, c, hi = info["p5"], info["p50"], info["p95"]; res["info"] = info
        at = lambda fx, fz: [lo[0] + fx * (hi[0] - lo[0]), c[1], lo[2] + fz * (hi[2] - lo[2])]
        res["poses"] = [{"i": i, "pos": at(fx, fz), "h": 36 * i} for i, (fz, fx) in enumerate((fz, fx) for fz in (0.4, 0.6) for fx in (0.3, 0.4, 0.5, 0.6, 0.7))]
        res["calib_pose"] = {"pos": c, "h": 90}; save()
    P, C = res["poses"], res["calib_pose"]
    # 2. start renders + calibration candidates
    if not (OUT / "p9_start.jpg").exists():
        render([(f"p{q['i']}_start.jpg", q["pos"], q["h"]) for q in P] + [("calib_start.jpg", C["pos"], C["h"])]
               + [(f"calib_h{a:03d}.jpg", C["pos"], C["h"] + a) for a in CAND])
    # 3. Genie: calibration session + 10 poses (4 at once; spike 9 lost 1 of 5 at 5 at once)
    todo = [(OUT / "calib_start.jpg", "calib")] * (not (OUT / "calib_genie.jpg").exists()) + \
           [(OUT / f"p{q['i']}_start.jpg", f"p{q['i']}") for q in P if not (OUT / f"p{q['i']}_genie.jpg").exists()]
    if todo:
        t = time.perf_counter(); runs = asyncio.run(genie_all(todo))
        res.setdefault("genie_runs", []).extend(runs); res["genie_wall_s"] = round(time.perf_counter() - t, 1); save()
    # 4. calibrate the angle once (one Neon call), then frozen
    if "angle" not in res:
        inp = [{"type": "text", "text": "Reference image R (a camera view after turning):"}, img(OUT / "calib_genie.jpg"),
               {"type": "text", "text": "Candidate views of the same room, each labelled with an angle:"}]
        for a in CAND: inp += [{"type": "text", "text": f"Candidate {a}:"}, img(OUT / f"calib_h{a:03d}.jpg")]
        inp.append({"type": "text", "text": "Which candidate shows the most similar view to R (same objects in the same places)? Answer with the candidate number only."})
        txt, s = neon(inp); m = re.search(r"\d+", txt)
        res["calibration"] = {"reply": txt[:300], "s": s}
        res["angle"] = int(m.group(0)) if m and int(m.group(0)) in CAND else None; save()
        print("calibrated angle", res["angle"], txt[:120], flush=True)
    A = res["angle"]; assert A, res["calibration"]
    # 5. truths at h + angle
    if not (OUT / "p9_truth.jpg").exists(): render([(f"p{q['i']}_truth.jpg", q["pos"], q["h"] + A) for q in P])
    # 6. Nano Banana baseline (10 at once, ~80 s each)
    if "banana" not in res:
        with ThreadPoolExecutor(10) as ex: res["banana"] = list(ex.map(lambda q: banana(OUT / f"p{q['i']}_start.jpg", A, OUT / f"p{q['i']}_banana.jpg"), P))
        save()
    # 7. judge: Genie pairs, Nano Banana pairs, sanity pairs (truth i vs Genie frame of pose i+1)
    if "judge" not in res:
        jobs = [("genie", i, OUT / f"p{i}_truth.jpg", OUT / f"p{i}_genie.jpg") for i in range(10) if (OUT / f"p{i}_genie.jpg").exists()]
        jobs += [("banana", i, OUT / f"p{i}_truth.jpg", OUT / f"p{i}_banana.jpg") for i in range(10) if (OUT / f"p{i}_banana.jpg").exists()]
        jobs += [("sanity", i, OUT / f"p{i}_truth.jpg", OUT / f"p{(i + 1) % 10}_genie.jpg") for i in range(10) if (OUT / f"p{(i + 1) % 10}_genie.jpg").exists()]
        with ThreadPoolExecutor(15) as ex: out = list(ex.map(lambda j: {"arm": j[0], "i": j[1]} | judge(j[2], j[3]), jobs))
        res["judge"] = out; save()
    # 7b. added after the pass mark, not part of it: positive control (truth vs splat at h + angle + 5 deg, same place)
    # and seed hold (start render vs Genie's first frame, before any turn)
    if "controls" not in res:
        if not (OUT / "p9_pos5.jpg").exists(): render([(f"p{q['i']}_pos5.jpg", q["pos"], q["h"] + A + 5) for q in P])
        jobs = [("positive", i, OUT / f"p{i}_truth.jpg", OUT / f"p{i}_pos5.jpg") for i in range(10)]
        jobs += [("seed_hold", i, OUT / f"p{i}_start.jpg", OUT / f"p{i}_genie_t0.jpg") for i in range(10) if (OUT / f"p{i}_genie_t0.jpg").exists()]
        with ThreadPoolExecutor(15) as ex: res["controls"] = list(ex.map(lambda j: {"arm": j[0], "i": j[1]} | judge(j[2], j[3]), jobs))
        save()
    J = res["judge"]
    arm = lambda k: [j for j in J if j["arm"] == k]
    ctl = lambda k: [j for j in res["controls"] if j["arm"] == k]
    res["controls_summary"] = {"note": "added after the pass mark, not part of it",
        "positive_same": sum(j["same"] is True for j in ctl("positive")), "positive_n": len(ctl("positive")),
        "seed_hold_same": sum(j["same"] is True for j in ctl("seed_hold")), "seed_hold_n": len(ctl("seed_hold"))}
    res["summary"] = {
        "angle_deg": A, "hold_s": HOLD_S, "hold_frames": HOLD_FRAMES or None,
        "frames_during_hold": {r["name"]: r.get("frames_during_hold") for r in res.get("genie_runs", [])},
        "genie_sessions_measured": sum((OUT / f"p{i}_genie.jpg").exists() for i in range(10)),
        "genie_same": sum(j["same"] is True for j in arm("genie")), "genie_n": len(arm("genie")),
        "banana_same": sum(j["same"] is True for j in arm("banana")), "banana_n": len(arm("banana")),
        "sanity_different": sum(j["same"] is False for j in arm("sanity")), "sanity_n": len(arm("sanity")),
        "unparsed": sum(j["same"] is None for j in J),
        "neon_calls": len(J) + 1, "banana_calls": len(res.get("banana", [])), "genie_sessions": len(res.get("genie_runs", []))}
    s = res["summary"]; s["pass"] = s["sanity_different"] == 10 and s["genie_sessions_measured"] == 10
    # 8. strips: splat start | Genie after turn | splat truth | Nano Banana
    for i in range(10):
        fs = [OUT / f"p{i}_{k}.jpg" for k in ("start", "genie", "truth", "banana")]
        if all(f.exists() for f in fs): strip(fs, OUT / f"strip_p{i}.jpg")
    save(); print(json.dumps(s), "total", round(time.perf_counter() - t_all, 1), "s", flush=True)
