"""Spike 10: Dream Run steering, held out. Spike 9's v2 controller (turn keys tapped 0.15 s, same Decision 1 choice
question, same Genie 4 client, imported from spikes/s9_genie_loop.py) on 6 fresh ego2act seeds, with a stricter arrival
rule: stop only when Decision 1 says "arrived" on 2 consecutive ticks. The final approach frame is scored by one
Robotics-ER 2 pointing call + one Decision 1 noul. Then look away and back (Trust Horizon, no pass mark).
Pass mark in docs/IDEAS.md (written 13:24, before the run). Media in .context/s10/ (gitignored).
Run: .venv/bin/python spikes/s10_dreamrun_heldout.py [parallel=3]  -> results/s10_dreamrun_heldout.json  (registered run)
     S10_TAG=_rerun .venv/bin/python spikes/s10_dreamrun_heldout.py   (after-the-fact repeat, not registered)"""
import asyncio, base64, faulthandler, json, os, pathlib, re, statistics, subprocess, sys, time
os.environ["S9_PULSE"] = "0.15"                       # v2 controller
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import s9_genie_loop as s9                            # loads .env, builds the client, defines d1_dir / d1_visible / KEY
faulthandler.dump_traceback_later(900, exit=True)
client, KEY, b64, img, PULSE = s9.client, s9.KEY, s9.b64, s9.img, s9.PULSE
APPROACH_S, LOOK_S, MIN_TICK, FF = s9.APPROACH_S, s9.LOOK_S, s9.MIN_TICK, s9.FF
TAG = os.environ.get("S10_TAG", "")   # after-the-fact repeats: S10_TAG=_rerun -> results/..._rerun.json, media .context/s10/_rerun/
OUT = pathlib.Path(".context/s10") / TAG; OUT.mkdir(parents=True, exist_ok=True)
ER_MODEL, LO, HI, NOUL_MIN = "gemini-robotics-er-2-preview", 300, 700, 0.75
# fresh cases (none is a spike 9 seed), targets fixed before any model output
SEEDS = [("double_shoe_box", "the blue plastic stool"), ("lava_toast_microwave", "the white microwave oven"),
         ("pantry_jar_sachet", "the dark teal mug"), ("plastic_trash_bin", "the orange trash bin"),
         ("racket_table_floor", "the orange folding table"), ("remote_marker_stand", "the red stationery case")]
S9_CASES = {c for c, _ in s9.SEEDS}; assert not S9_CASES & {c for c, _ in SEEDS}
POINT = ('Point to {t}. The answer should follow the json format: [{{"point": <point>, "label": <label1>}}, ...]. '
         'The points are in [y, x] format normalized to 0-1000.')   # spike 8 prompt

def make_seed(case):
    p = OUT / f"seed_{case}.jpg"
    if not p.exists():
        subprocess.run([FF, "-y", "-v", "error", "-i", f".context/ego2act/human/correct/{case}/correct_1.mp4", "-frames:v", "1",
                        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", "-q:v", "2", str(p)], check=True, timeout=60)
    return p.read_bytes()

def er_point(frame, target):
    t = time.perf_counter()
    try:
        r = client.interactions.create(model=ER_MODEL, input=[{"type": "image", "data": b64(frame), "mime_type": "image/jpeg"},
            {"type": "text", "text": POINT.format(t=target)}], generation_config={"thinking_level": "low"})
        txt = r.output_text or ""; m = re.search(r"\[.*\]", txt, re.S); pts = json.loads(m.group(0)) if m else []
        pt = pts[0]["point"] if pts else None
        return {"s": round(time.perf_counter() - t, 2), "point_yx": pt, "raw": txt[:300]}
    except Exception as e: return {"s": round(time.perf_counter() - t, 2), "point_yx": None, "error": str(e)[:200]}

def d1_large(frame, target):
    r = client.decisions.create(model="gemini-decision-1", input=[img(frame)],
        questions={"big": {"type": "noul", "instructions": f"Is {target} clearly visible and large in this frame?"}})
    return round(r.answers["big"].noul, 3)

async def session(case, target):
    d = OUT / case; d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("f*.jpg"): f.unlink()
    seed = make_seed(case)
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
            f0 = await snap("t0", 0); held = None; t_a = time.perf_counter(); streak = 0; out["arrived"] = False
            while time.perf_counter() - t_a < APPROACH_S:
                tk = time.perf_counter()
                try: choice, conf, lat = await asyncio.to_thread(s9.d1_dir, st["latest"], target)
                except Exception as e: out["ticks"].append({"error": str(e)[:200]}); streak = 0; await asyncio.sleep(0.5); continue
                out["ticks"].append({"t": round(tk - t_a, 2), "frame": st["n"], "choice": choice, "conf": conf, "d1_s": lat})
                streak = streak + 1 if choice == "arrived" else 0      # the one change to the loop: 2 consecutive "arrived"
                want = KEY.get(choice)
                if PULSE and choice in ("left", "right"):
                    if held: await act("key_up", held); held = None
                    await act("key_down", want); await asyncio.sleep(PULSE); await act("key_up", want); await asyncio.sleep(0.25)
                    continue
                if want != held:
                    if held: await act("key_up", held)
                    if want: await act("key_down", want)
                    held = want
                if streak >= 2: out["arrived"] = True; break
                await asyncio.sleep(max(0, MIN_TICK - (time.perf_counter() - tk)))
            if held: await act("key_up", held)
            out["approach_s"] = round(time.perf_counter() - t_a, 2)
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
        er, big, v0, v1, v2, er_back = await asyncio.gather(*[asyncio.to_thread(*a) for a in (
            (er_point, f1, target), (d1_large, f1, target), (s9.d1_visible, f0, target), (s9.d1_visible, f1, target),
            (s9.d1_visible, f2, target), (er_point, f2, target))])
        pt = er["point_yx"]; central = bool(pt) and LO <= pt[0] <= HI and LO <= pt[1] <= HI
        out |= {"er_end": er, "er_central": central, "noul_large_end": big, "auto_success": central and big >= NOUL_MIN,
                "vis_t0": v0, "vis_end": v1, "vis_back": v2, "auto_retained": v2 >= 0.5, "er_back": er_back}
    print(json.dumps({k: v for k, v in out.items() if k != "ticks"} | {"n_ticks": len(out["ticks"]), "choices": "".join(t.get("choice", "E")[0] for t in out["ticks"])}), flush=True)
    return out

def sheet(rows):
    """seed photo | arrival frame (ER point in red, central 40% box in yellow) | after look-back"""
    ins, parts = [], []
    for i, r in enumerate(rows):
        for p in (OUT / f"seed_{r['case']}.jpg", OUT / f"{r['case']}_end.jpg", OUT / f"{r['case']}_back.jpg"): ins += ["-i", str(p)]
        pt = (r.get("er_end") or {}).get("point_yx"); col = "lime" if r.get("auto_success") else "red"
        mark = "drawbox=x=192:y=108:w=256:h=144:color=yellow:t=2" + (f",drawbox=x={pt[1]*640//1000-8}:y={pt[0]*360//1000-8}:w=16:h=16:color={col}:t=fill" if pt else "")
        parts.append(f"[{3*i}:v]scale=640:360[s{i}0];[{3*i+1}:v]scale=640:360,{mark}[s{i}1];[{3*i+2}:v]scale=640:360[s{i}2];[s{i}0][s{i}1][s{i}2]hstack=3[r{i}];")
    fc = "".join(parts) + "".join(f"[r{i}]" for i in range(len(rows))) + f"vstack={len(rows)}"
    subprocess.run([FF, "-y", "-v", "error", *ins, "-filter_complex", fc, "-frames:v", "1", str(OUT / "sheet.png")], timeout=120)

async def main():
    par = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    sem = asyncio.Semaphore(par)
    async def attempt(c, t):
        try: return await session(c, t)
        except Exception as e: return {"case": c, "target": t, "error": f"{type(e).__name__}: {str(e)[:400]}", "ticks": []}
    async def one(c, t):
        async with sem:
            r = await attempt(c, t)
            if "auto_success" not in r:                       # crashed: retry once, keep the first attempt on record
                first = {k: v for k, v in r.items() if k != "ticks"} | {"n_ticks": len(r["ticks"])}
                r = await attempt(c, t); r["retried"] = True; r["first_attempt"] = first
            return r
    rows = await asyncio.gather(*[one(c, t) for c, t in SEEDS])
    lat = [t["d1_s"] for r in rows for t in r["ticks"] if "d1_s" in t]
    ok = [r for r in rows if "auto_success" in r]
    n_succ = sum(r["auto_success"] for r in ok); p50 = round(statistics.median(lat), 3) if lat else None
    arr = [r["approach_s"] for r in rows if r.get("arrived")]
    summ = {"n_seeds": len(rows), "n_scored": len(ok), "turn_pulse_s": PULSE, "parallel_sessions": par,
            "arrival_rule": "Decision 1 'arrived' on 2 consecutive ticks, else stop at 15 s",
            "auto_success": n_succ, "er_central": sum(r["er_central"] for r in ok), "noul_large_ge_0.75": sum(r["noul_large_end"] >= NOUL_MIN for r in ok),
            "arrived_2_consecutive": len(arr), "time_to_arrive_s": arr, "time_to_arrive_median_s": round(statistics.median(arr), 2) if arr else None,
            "auto_retained_after_lookback": sum(r["auto_retained"] for r in ok),
            "ticks": len(lat), "d1_tick_p50_s": p50, "d1_tick_max_s": max(lat) if lat else None,
            "er_call_s": [r["er_end"]["s"] for r in ok], "retried": [r["case"] for r in rows if r.get("retried")],
            "crashed_after_retry": [r["case"] for r in rows if "auto_success" not in r],
            "first_frame_s": [r.get("first_frame_s") for r in rows], "stream_fps": [r.get("stream_fps") for r in rows],
            "genie_frames_total": sum(r.get("frames", 0) for r in rows),
            "pass": n_succ >= 4 and p50 is not None and p50 <= 1.2,
            "eye_check": "filled in by hand after viewing .context/s10/sheet.png"}
    pathlib.Path(f"results/s10_dreamrun_heldout{TAG}.json").write_text(json.dumps({"summary": summ, "seeds": rows}, indent=1))
    if ok: sheet(ok)
    print(json.dumps(summ))

if __name__ == "__main__": asyncio.run(main())
