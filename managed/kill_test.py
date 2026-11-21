# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=3.2"]
# ///
"""Kill test for #24: can a hosted Managed Agents run call OUR function (brake_check) and use its answer?
Pass mark (written 14:58, before any call): PASS = the remote antigravity agent emits >= 1 function_call
to brake_check with a task string and a click point, we return a result, and the run then finishes
(status completed) quoting our p_injected, all in < 120 s. KILL otherwise (then Managed Agents only
finishes the task after the brake, DEMO row 1:10). The function result is a canned brake reply: this
tests the plumbing and round-trip time, not the brake.
Run: uv run managed/kill_test.py"""
import json, os, pathlib, time
from typing import Any
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from google import genai

AGENT = "antigravity-preview-09-2026"
TOOLS = [{"type": "function", "name": "brake_check",
          "description": "Safety gate. Call before every click; returns p_injected and stop.",
          "parameters": {"type": "object", "properties": {
              "task": {"type": "string"}, "x": {"type": "integer"}, "y": {"type": "integer"}},
              "required": ["task", "x", "y"]}}]
CANNED = {"p_injected": 0.913, "stop": True, "threshold": 0.5, "model": "gemini-decision-1"}
PROMPT = ("You are about to click at (640, 400) for the task 'Place the order for the headphones'. "
          "Call brake_check once with that task and point. Then reply with one line: the p_injected value "
          "it returned and whether you would click.")

client = genai.Client(http_options={"api_version": "v1beta", "timeout": 300_000})
out: dict[str, Any] = {"calls": [], "steps": []}
t0 = time.perf_counter()
try:
    r = client.interactions.create(agent=AGENT, environment="remote", tools=TOOLS, input=PROMPT)
    out["t_first_s"] = round(time.perf_counter() - t0, 2)
    for hop in range(4):
        out["steps"].append({"status": str(r.status), "types": [s.type for s in (r.steps or [])]})
        calls = [s for s in (r.steps or []) if s.type == "function_call"]
        if not calls:
            break
        results = []
        for c in calls:
            out["calls"].append({"name": c.name, "args": c.arguments, "t_s": round(time.perf_counter() - t0, 2)})
            results.append({"type": "function_result", "call_id": c.id, "name": c.name, "result": json.dumps(CANNED)})
        r = client.interactions.create(agent=AGENT, environment="remote", tools=TOOLS,
                                       previous_interaction_id=r.id, input=results)
    out.update(ok=True, status=str(r.status), output=(r.output_text or "")[-300:])
except Exception as e:
    out.update(ok=False, err=f"{type(e).__name__}: {str(e)[:600]}")
out["s"] = round(time.perf_counter() - t0, 2)
out["pass"] = bool(out.get("ok") and any(c["name"] == "brake_check" for c in out["calls"])
                   and "completed" in out.get("status", "") and "0.913" in out.get("output", "") and out["s"] < 120)
print(json.dumps(out, indent=2, default=str))
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/managed_kill_test.json").write_text(json.dumps(out, indent=2, default=str))
