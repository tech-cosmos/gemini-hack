"""Spike 9: Genie 4 closed loop. A real photo seeds a Genie world; Decision 1 looks at the latest frame every tick and
picks a key (turn left / turn right / forward / arrived); then we look away and back (Trust Horizon).
Pass mark in docs/IDEAS.md (written 12:56). Media in .context/s9/ (gitignored). Result: results/s9_genie_loop.json
Run: .venv/bin/python spikes/s9_genie_loop.py [parallel=5]   (registered run -> results/s9_genie_loop.json)
     S9_PULSE=0.15 .venv/bin/python spikes/s9_genie_loop.py   (after-the-fact v2, tapped turns -> results/s9_genie_loop_v2.json, media .context/s9/v2/)"""
import asyncio, base64, faulthandler, json, os, pathlib, statistics, subprocess, sys, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(600, exit=True)
from google import genai
PULSE = float(os.environ.get("S9_PULSE", 0))  # v2 (after the fact): tap turn keys for PULSE s instead of holding them until the next tick
TAG = "_v2" if PULSE else ""
SEED_DIR = pathlib.Path(".context/s9"); OUT = SEED_DIR / "v2" if PULSE else SEED_DIR; OUT.mkdir(parents=True, exist_ok=True); FF = "/opt/homebrew/bin/ffmpeg"
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 60_000})
SEEDS = [("stack_blocks", "the yellow toy block"), ("book_miniature", "the blue-grey book standing on the right"),
         ("kendama_can", "the yellow drink can lying on the table"), ("bag_shoe_rack", "the black shoe rack"),
         ("three_cups_and_water", "the green mug")]
APPROACH_S, LOOK_S, MIN_TICK = 15.0, 3.0, 0.5
KEY = {"left": "arrow_left", "right": "arrow_right", "forward": "key_w"}
b64 = lambda b: base64.b64encode(b).decode()
img = lambda b: {"type": "image", "data": b64(b), "mime_type": "image/jpeg", "resolution": "low"}

def d1_dir(frame, target):
    t = time.perf_counter()
    r = client.decisions.create(model="gemini-decision-1", input=[
        {"type": "text", "text": f"First-person camera view. We are walking towards {target}."}, img(frame)],
        questions={"dir": {"type": "choice", "instructions": f"Where is {target} relative to the centre of the image, and how close is it?", "criteria": {
            "left": "The target is visible and clearly left of the image centre.",
            "right": "The target is visible and clearly right of the image centre.",
            "forward": "The target is roughly centred horizontally but still small or far: it fills less than half of the image width.",
            "arrived": "The target is centred and close: it fills about half of the image width or more.",
            "other": "The target is not visible in the image."}}})
    a = r.answers["dir"]
    return a.choice, round(a.confidence, 3), round(time.perf_counter() - t, 3)

def d1_visible(frame, target):
    r = client.decisions.create(model="gemini-decision-1", input=[img(frame)],
        questions={"vis": {"type": "noul", "instructions": f"Is {target} clearly visible?"}})
    return round(r.answers["vis"].noul, 3)

def d1_size(first, later, target):
    r = client.decisions.create(model="gemini-decision-1", input=[
        {"type": "text", "text": "Two images of the same scene: the first frame, then a later frame."}, img(first), img(later)],
        questions={"size": {"type": "choice", "instructions": f"In the second image, how large does {target} appear compared with the first image?", "criteria": {
            "larger": "It takes up clearly more of the image in the second image.", "same": "About the same size in both.",
            "smaller": "It takes up clearly less of the image in the second image.", "gone": "It is not visible in the second image."}}})
    a = r.answers["size"]; return a.choice, round(a.confidence, 3)

async def session(case, target):
    d = OUT / case; d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("f*.jpg"): f.unlink()
    seed = (SEED_DIR / f"seed_{case}.jpg").read_bytes()
    st = {"latest": None, "n": 0, "t_first": None, "t_last": None, "events": {}}
    out = {"case": case, "target": target, "ticks": []}
    t0 = time.perf_counter()
    it = await client.aio.interactions.create(model="genie-4", api_version="v1beta")
    async with client.aio.interactions.connect(it.id, api_version="v1beta") as s:
        t_conn = time.perf_counter()
        await s.send({"event_type": "world_setup", "world_prompt": {"text": "first-person view of this exact scene"},
                      "reference_image": {"mime_type": "image/jpeg", "data": b64(seed)}})
        act = lambda a, k: s.send({"event_type": "user_action", "action": a, "input": k})

        async def recv():
            async for ev in s.receive():
                if ev.event_type == "step.delta":
                    if getattr(ev.delta, "type", None) == "video" and ev.delta.data:
                        st["n"] += 1; st["t_last"] = time.perf_counter(); st["t_first"] = st["t_first"] or st["t_last"]
                        st["latest"] = base64.b64decode(ev.delta.data); (d / f"f{st['n']:04d}.jpg").write_bytes(st["latest"])
                else:
                    st["events"][ev.event_type] = st["events"].get(ev.event_type, 0) + 1
                    if ev.event_type in ("interaction.completed", "error", "interaction.failed"):
                        if ev.event_type != "interaction.completed": st["events"]["detail"] = str(ev)[:500]
                        return

        async def snap(name, settle=0.3):
            await asyncio.sleep(settle); (OUT / f"{case}_{name}.jpg").write_bytes(st["latest"]); out[f"frame_{name}"] = st["n"]; return st["latest"]

        async def drive():
            while st["latest"] is None: await asyncio.sleep(0.02)
            out["first_frame_s"] = round(st["t_first"] - t_conn, 2)
            f0 = await snap("t0", 0); held = None; t_a = time.perf_counter()
            while time.perf_counter() - t_a < APPROACH_S:
                tk = time.perf_counter()
                try: choice, conf, lat = await asyncio.to_thread(d1_dir, st["latest"], target)
                except Exception as e: out["ticks"].append({"error": str(e)[:200]}); await asyncio.sleep(0.5); continue
                out["ticks"].append({"t": round(tk - t_a, 2), "frame": st["n"], "choice": choice, "conf": conf, "d1_s": lat})
                want = KEY.get(choice)
                if PULSE and choice in ("left", "right"):
                    if held: await act("key_up", held); held = None
                    await act("key_down", want); await asyncio.sleep(PULSE); await act("key_up", want); await asyncio.sleep(0.25)
                    continue
                if want != held:
                    if held: await act("key_up", held)
                    if want: await act("key_down", want)
                    held = want
                if choice == "arrived": break
                await asyncio.sleep(max(0, MIN_TICK - (time.perf_counter() - tk)))
            if held: await act("key_up", held)
            out["approach_s"] = round(time.perf_counter() - t_a, 2); out["arrived"] = bool(out["ticks"]) and out["ticks"][-1].get("choice") == "arrived"
            f1 = await snap("end")
            await act("key_down", "arrow_left"); await asyncio.sleep(LOOK_S); await act("key_up", "arrow_left"); await snap("away")
            await act("key_down", "arrow_right"); await asyncio.sleep(LOOK_S); await act("key_up", "arrow_right"); f2 = await snap("back", 0.5)
            await s.complete()   # once only
            return f0, f1, f2

        rt = asyncio.create_task(recv())
        try: f0, f1, f2 = await asyncio.wait_for(drive(), 70)
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {str(e)[:300]}"; f0 = f1 = f2 = None
            try: await s.complete()
            except Exception: pass
        try: await asyncio.wait_for(rt, 10)
        except Exception: rt.cancel()
    out |= {"connect_s": round(t_conn - t0, 2), "frames": st["n"], "events": st["events"],
            "stream_fps": round((st["n"] - 1) / max(st["t_last"] - st["t_first"], 1e-6), 1) if st["n"] > 1 else None}
    if f0 and f1 and f2:
        v0, v1, v2, (sz, szc), (szb, szbc) = await asyncio.gather(*[asyncio.to_thread(*a) for a in (
            (d1_visible, f0, target), (d1_visible, f1, target), (d1_visible, f2, target), (d1_size, f0, f1, target), (d1_size, f0, f2, target))])
        out |= {"vis_t0": v0, "vis_end": v1, "vis_back": v2, "size_end_vs_t0": sz, "size_conf": szc, "size_back_vs_t0": szb, "size_back_conf": szbc,
                "auto_approach_ok": v1 >= 0.5 and sz == "larger", "auto_lookback_ok": v2 >= 0.5}
        subprocess.run([FF, "-y", "-v", "error", "-framerate", "24", "-i", str(d / "f%04d.jpg"), "-pix_fmt", "yuv420p", str(OUT / f"{case}.mp4")])
    print(json.dumps({k: v for k, v in out.items() if k != "ticks"} | {"n_ticks": len(out["ticks"]), "choices": "".join(t.get("choice", "E")[0] for t in out["ticks"])}), flush=True)
    return out

def sheet(rows):
    ins, parts = [], []
    for i, r in enumerate(rows):
        for n in ("t0", "end", "back"): ins += ["-i", str(OUT / f"{r['case']}_{n}.jpg")]
        parts.append("".join(f"[{3*i+j}:v]scale=640:360[s{i}{j}];" for j in range(3)) + f"[s{i}0][s{i}1][s{i}2]hstack=3[r{i}];")
    fc = "".join(parts) + "".join(f"[r{i}]" for i in range(len(rows))) + f"vstack={len(rows)}"
    subprocess.run([FF, "-y", "-v", "error", *ins, "-filter_complex", fc, "-frames:v", "1", str(OUT / "sheet.png")])

async def main():
    par = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sem = asyncio.Semaphore(par)
    async def one(c, t):
        async with sem:
            try: return await session(c, t)
            except Exception as e: return {"case": c, "target": t, "error": f"{type(e).__name__}: {str(e)[:400]}", "ticks": []}
    rows = await asyncio.gather(*[one(c, t) for c, t in SEEDS])
    lat = [t["d1_s"] for r in rows for t in r["ticks"] if "d1_s" in t]
    ok = [r for r in rows if "vis_end" in r]
    summ = {"n_seeds": len(rows), "n_scored": len(ok), "turn_pulse_s": PULSE or "held until next tick", "parallel_sessions": par,
            "auto_approach_ok": sum(r["auto_approach_ok"] for r in ok), "auto_lookback_ok": sum(r["auto_lookback_ok"] for r in ok),
            "arrived": sum(bool(r.get("arrived")) for r in rows), "ticks": len(lat),
            "d1_tick_p50_s": round(statistics.median(lat), 3) if lat else None, "d1_tick_max_s": max(lat) if lat else None,
            "first_frame_s": [r.get("first_frame_s") for r in rows], "stream_fps": [r.get("stream_fps") for r in rows],
            "eye_check": "filled in by hand after viewing .context/s9/sheet.png"}
    pathlib.Path(f"results/s9_genie_loop{TAG}.json").write_text(json.dumps({"summary": summ, "seeds": rows}, indent=1))
    if ok: sheet(ok)
    print(json.dumps(summ))

if __name__ == "__main__": asyncio.run(main())
