# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=3.2"]
# ///
"""Spike 0b: does a Managed Agent run end to end, and how long does one small coding task take?
Pass mark (written before the run): finishes with correct output in < 3 min.
Run: uv run spikes/s0b_managed_agent.py"""
import faulthandler, json, os, pathlib, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(420, exit=True)
from google import genai
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 600_000})
t = time.perf_counter(); out = {}
try:
    r = client.interactions.create(agent="antigravity-preview-09-2026", environment="remote",
        input="Write a Python script that prints the first 20 Fibonacci numbers, run it, and reply with only the last number it printed.")
    out = {"ok": True, "s": round(time.perf_counter() - t, 1), "output": (r.output_text or "")[-200:],
           "correct": "4181" in (r.output_text or "")}
except Exception as e:
    out = {"ok": False, "s": round(time.perf_counter() - t, 1), "err": str(e)[:400]}
out["pass"] = bool(out.get("correct")) and out["s"] < 180
print(json.dumps(out, indent=2))
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/s0b_managed_agent.json").write_text(json.dumps(out, indent=2))
