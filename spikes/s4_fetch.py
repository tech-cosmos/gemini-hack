"""Spike 4 data step: pull 12 indoor SceneDiff pairs out of the 11.9 GB zip by HTTP range (no full download).
Selection rule (written in docs/IDEAS.md before any model output): splits/val_split.json -> "varied" in file order,
drop outdoor scenes (gas_station*, street*), take every 4th. Run: .venv/bin/python -I spikes/s4_fetch.py"""
import io, json, pathlib, pickle, subprocess, remotezip
U = "https://huggingface.co/datasets/yuqun/SceneDiff/resolve/main/scenediff_benchmark.zip"
OUT = pathlib.Path(".context/scenediff"); OUT.mkdir(parents=True, exist_ok=True)
FF = "/opt/homebrew/bin/ffmpeg"

class Safe(pickle.Unpickler):  # the pickle is untrusted: allow plain containers only
    def find_class(self, mod, name):
        if (mod, name) in {("collections", "OrderedDict"), ("builtins", "dict"), ("builtins", "list"), ("builtins", "set"), ("builtins", "tuple")}:
            return getattr(__import__(mod), name)
        raise pickle.UnpicklingError(f"blocked {mod}.{name}")

z = remotezip.RemoteZip(U)
names = {i.filename: i.file_size for i in z.infolist()}
varied = json.loads(z.read("scenediff_benchmark/splits/val_split.json"))["varied"]
indoor = [p for p in varied if not p.startswith(("gas_station", "street"))]
picked = indoor[0::4]
print(len(varied), len(indoor), picked, flush=True)
man = []
for p in picked:
    d = OUT / p; d.mkdir(exist_ok=True); pre = f"scenediff_benchmark/data/{p}/"
    seg = Safe(io.BytesIO(z.read(pre + "segments.pkl"))).load()
    gold = []
    objs = seg["objects"]
    if len(man) == 0: print({k: (type(v).__name__, list(v)[:3] if hasattr(v, "__iter__") and not isinstance(v, str) else v) for k, v in seg.items()}, str(objs)[:600], flush=True)
    for k, o in (objs.items() if isinstance(objs, dict) else enumerate(objs)):
        t = "moved" if o["in_video1"] and o["in_video2"] else "removed" if o["in_video1"] else "added"
        gold.append({"id": str(k), "label": o["label"], "type": t, "deformability": o.get("deformability")})
    rec = {"pair": p, "scenetype": seg.get("scenetype"), "gold": gold, "raw_bytes": 0}
    for v in ("1", "2"):
        src = next(n for n in names if n.startswith(pre + f"original_video{v}."))
        raw = d / src.rsplit("/", 1)[-1]
        if not raw.exists(): raw.write_bytes(z.read(src))
        rec["raw_bytes"] += names[src]
        for h, fps, crf in ((720, 15, 28), (360, 5, 30)):
            o = d / f"v{v}_{h}.mp4"
            if not o.exists():
                subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(raw), "-an", "-vf", f"scale=-2:{h},fps={fps}", "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", str(o)], check=True)
            rec[f"v{v}_{h}_bytes"] = o.stat().st_size
        dur = subprocess.run([FF.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(d / f"v{v}_720.mp4")], capture_output=True, text=True).stdout.strip()
        rec[f"v{v}_s"] = float(dur)
    man.append(rec); print(json.dumps(rec), flush=True)
(OUT / "manifest.json").write_text(json.dumps(man, indent=1))
print("raw MB", sum(r["raw_bytes"] for r in man) / 1e6)
