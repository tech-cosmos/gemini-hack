"""Spike 0c: is Hydrogen fast enough per frame at thinking_level low (the builder guide's lever)?
Pass mark (written before the run): p50 < 1.5 s on the same frame as spike 0, n=10.
Run: .venv/bin/python spikes/s0c_hydrogen_low.py <image.jpg>"""
import base64, faulthandler, json, os, pathlib, statistics, sys, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(240, exit=True)
from google import genai
client = genai.Client(http_options={"timeout": 60_000})
img = base64.b64encode(open(sys.argv[1], "rb").read()).decode()
out = {}
for level in ["low", "medium"]:
    lat = []
    for i in range(10):
        t = time.perf_counter()
        r = client.interactions.create(model="gemini-4-hydrogen", generation_config={"thinking_level": level},
            input=[{"type": "text", "text": "In one short sentence: what objects are in this frame?"},
                   {"type": "image", "data": img, "mime_type": "image/jpeg"}])
        lat.append(time.perf_counter() - t)
        if i == 0: out[f"sample_{level}"] = (r.output_text or "")[:100]
    out[level] = {"n": 10, "p50_s": round(statistics.median(lat), 2), "max_s": round(max(lat), 2)}
out["pass"] = out["low"]["p50_s"] < 1.5
print(json.dumps(out, indent=2))
pathlib.Path("results/s0c_hydrogen_low.json").write_text(json.dumps(out, indent=2))
