# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=3.2"]
# ///
"""Spike 0: do two Gemini 4 models and Decision 1 answer, and how fast is Hydrogen on one frame?
Pass mark (written before the run): all three respond; Hydrogen p50 < 1.5 s on one 720p frame over 10 calls.
Run: uv run spikes/s0_plumbing.py <image.jpg>"""
import base64, faulthandler, json, os, statistics, sys, time, pathlib

for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

faulthandler.dump_traceback_later(240, exit=True)
from google import genai

client = genai.Client(http_options={"api_version": "v1beta", "timeout": 120_000})
img = base64.b64encode(open(sys.argv[1], "rb").read()).decode()
frame = {"type": "image", "data": img, "mime_type": "image/jpeg"}
out = {}

def timed(fn):
    t = time.perf_counter(); r = fn(); return r, time.perf_counter() - t

for model in ["gemini-4-neon", "gemini-4-carbon"]:
    try:
        r, dt = timed(lambda: client.interactions.create(model=model, input="Reply with the single word: ready"))
        out[model] = {"ok": True, "s": round(dt, 2), "text": (r.output_text or "")[:40]}
    except Exception as e:
        out[model] = {"ok": False, "err": str(e)[:300]}

lat = []
for i in range(10):
    try:
        r, dt = timed(lambda: client.interactions.create(model="gemini-4-hydrogen",
            input=[{"type": "text", "text": "In one short sentence: what objects are in this frame?"}, frame]))
        lat.append(dt)
        if i == 0: out["hydrogen_sample"] = (r.output_text or "")[:120]
    except Exception as e:
        out["hydrogen_err"] = str(e)[:300]; break
if lat:
    out["gemini-4-hydrogen"] = {"ok": True, "n": len(lat), "p50_s": round(statistics.median(lat), 2), "max_s": round(max(lat), 2)}

dlat = []
for i in range(5):
    try:
        r, dt = timed(lambda: client.decisions.create(model="gemini-decision-1",
            input=[{"type": "text", "text": "One camera frame."}, {**frame, "resolution": "low"}],
            questions={"has_food": {"type": "noul", "instructions": "Does the frame show food?"},
                       "has_person": {"type": "noul", "instructions": "Does the frame show a person?"}}))
        dlat.append(dt)
        if i == 0: out["decision_sample"] = {k: round(a.noul, 2) for k, a in r.answers.items()}
    except Exception as e:
        out["decision_err"] = str(e)[:300]; break
if dlat:
    out["gemini-decision-1"] = {"ok": True, "n": len(dlat), "p50_s": round(statistics.median(dlat), 2)}

ok = all(out.get(m, {}).get("ok") for m in ["gemini-4-neon", "gemini-4-hydrogen", "gemini-decision-1"])
out["pass"] = ok and out["gemini-4-hydrogen"]["p50_s"] < 1.5
print(json.dumps(out, indent=2))
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/s0_plumbing.json").write_text(json.dumps(out, indent=2))
