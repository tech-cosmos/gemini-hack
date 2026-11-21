"""Spike 5: what Gemini video generation (Omni 1.2 Flash) and the Genie 4 world model do with our key.
Media goes to .context/videogen/ (gitignored). Each run prints one JSON line of measurements.
Run: .venv/bin/python spikes/s5_videogen.py t2v "<prompt>" [seconds=4]
     .venv/bin/python spikes/s5_videogen.py i2v <image> "<prompt>" [seconds=4]
     .venv/bin/python spikes/s5_videogen.py edit <video<=15s> "<prompt>"            (same length as the input)
     .venv/bin/python spikes/s5_videogen.py extend <video> "<prompt>" [seconds=3]
     .venv/bin/python spikes/s5_videogen.py genie "<world prompt>" [frames=96] [seed_image_16x9]
Env: S5_NAME=<output stem>, S5_RES=360p|720p|1080p|4k (default 720p)."""
import asyncio, base64, faulthandler, json, mimetypes, os, pathlib, subprocess, sys, time, wave
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(900, exit=True)
from google import genai
OUT = pathlib.Path(".context/videogen"); OUT.mkdir(parents=True, exist_ok=True)
FF = "/opt/homebrew/bin/"
MODEL = os.environ.get("S5_MODEL", "gemini-omni-1.2-flash")
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 600_000})

def probe(p):
    r = subprocess.run([FF + "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}"); v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in j.get("streams", []) if s["codec_type"] == "audio"), None)
    return {"res": f"{v.get('width')}x{v.get('height')}", "fps": v.get("r_frame_rate"), "vcodec": v.get("codec_name"),
            "audio": f"{a['codec_name']} {a.get('sample_rate')} Hz" if a else None, "dur_s": float(j.get("format", {}).get("duration", 0)), "bytes": p.stat().st_size}

def thumb(p, at):
    png = p.with_suffix(".png")
    subprocess.run([FF + "ffmpeg", "-y", "-v", "error", "-ss", str(at), "-i", str(p), "-frames:v", "1", str(png)])
    return str(png)

def upload(path):
    f = client.files.upload(file=path)
    while f.state.name == "PROCESSING": time.sleep(2); f = client.files.get(name=f.name)
    assert f.state.name == "ACTIVE", f.state
    return f.uri

def omni(mode, name, inp, seconds=None, task=None):
    fmt = {"type": "video", "resolution": os.environ.get("S5_RES", "720p")}
    if seconds: fmt["duration"] = f"{int(seconds)}s"
    kw = {"generation_config": {"video_config": {"task": task}}} if task else {}
    t = time.perf_counter()
    r = client.interactions.create(model=MODEL, input=inp, response_format=fmt, **kw)  # one blocking call, no operation to poll
    wall = round(time.perf_counter() - t, 1)
    v = r.output_video
    if v is None:
        print(json.dumps({"test": mode, "ok": False, "wall_s": wall, "status": r.status, "raw": str(r)[:1500]})); return
    p = OUT / f"{name}.mp4"
    if getattr(v, "data", None): p.write_bytes(base64.b64decode(v.data))
    else: client.files.download(file=v.uri, destination=str(p))
    m = probe(p)
    print(json.dumps({"test": mode, "ok": True, "model": MODEL, "wall_s": wall, "status": r.status, "id": r.id, **m,
                      "mp4": str(p), "png": thumb(p, m["dur_s"] / 2), "usage": str(getattr(r, "usage", None))[:400]}))

async def genie(prompt, n_frames, seed=None):
    t0 = time.perf_counter()
    it = await client.aio.interactions.create(model="genie-4", api_version="v1beta")
    setup = {"event_type": "world_setup", "world_prompt": {"text": prompt}}
    if seed: setup["reference_image"] = {"mime_type": mimetypes.guess_type(seed)[0], "data": base64.b64encode(pathlib.Path(seed).read_bytes()).decode()}
    name = os.environ.get("S5_NAME", "genie"); d = OUT / name; d.mkdir(exist_ok=True)
    frames, pcm, other, t_first, t_last, t_conn = 0, [], {}, None, None, None
    async with client.aio.interactions.connect(it.id, api_version="v1beta") as s:
        t_conn = time.perf_counter(); await s.send(setup)
        async for ev in s.receive():
            if ev.event_type == "step.delta":
                dt = getattr(ev.delta, "type", None)
                if dt == "video" and ev.delta.data:
                    frames += 1; t_last = time.perf_counter(); t_first = t_first or t_last
                    (d / f"f{frames:04d}.jpg").write_bytes(base64.b64decode(ev.delta.data))
                    if frames == 1: await s.send({"event_type": "user_action", "action": "key_down", "input": "key_w"})      # walk forward
                    if frames == n_frames // 2:
                        await s.send({"event_type": "user_action", "action": "key_up", "input": "key_w"})
                        await s.send({"event_type": "user_action", "action": "key_down", "input": "arrow_left"})             # then pan left
                    if frames == n_frames: await s.complete()   # once only: a second complete() returns 'Precondition check failed'; complete() stops billing; leaving the block alone does not
                elif dt == "audio" and ev.delta.data: pcm.append(base64.b64decode(ev.delta.data))
            else:
                other[ev.event_type] = other.get(ev.event_type, 0) + 1
                if ev.event_type in ("interaction.completed", "error", "interaction.failed"):
                    if ev.event_type != "interaction.completed": other["detail"] = str(ev)[:600]
                    break
    if pcm:
        with wave.open(str(d / "audio.wav"), "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(b"".join(pcm))
    out = {"test": "genie", "ok": frames > 0, "connect_s": round(t_conn - t0, 2), "frames": frames, "events": other,
           "audio_s": round(sum(map(len, pcm)) / 192000, 2)}
    if frames:
        mp4 = OUT / f"{name}.mp4"
        subprocess.run([FF + "ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", str(d / "f%04d.jpg"), "-pix_fmt", "yuv420p", str(mp4)])
        png = OUT / f"{name}.png"; subprocess.run([FF + "ffmpeg", "-y", "-v", "error", "-i", str(d / f"f{frames:04d}.jpg"), str(png)])
        out |= {"first_frame_s": round(t_first - t_conn, 2), "stream_fps": round((frames - 1) / max(t_last - t_first, 1e-6), 1),
                "frame": probe(d / "f0001.jpg")["res"], "mp4": str(mp4), "png": str(png)}
    print(json.dumps(out))

if __name__ == "__main__":
    mode, a = sys.argv[1], sys.argv[2:]
    name = os.environ.get("S5_NAME", mode)
    if mode == "t2v": omni(mode, name, a[0], a[1] if len(a) > 1 else 4)
    elif mode == "i2v":
        img = {"type": "image", "data": base64.b64encode(pathlib.Path(a[0]).read_bytes()).decode(), "mime_type": mimetypes.guess_type(a[0])[0]}
        omni(mode, name, [img, {"type": "text", "text": a[1]}], a[2] if len(a) > 2 else 4)
    elif mode == "edit": omni(mode, name, [{"type": "video", "uri": upload(a[0])}, {"type": "text", "text": a[1]}])
    elif mode == "extend": omni(mode, name, [{"type": "video", "uri": upload(a[0])}, {"type": "text", "text": a[1]}], a[2] if len(a) > 2 else 3)
    elif mode == "genie": asyncio.run(genie(a[0], int(a[1]) if len(a) > 1 else 96, a[2] if len(a) > 2 else None))
