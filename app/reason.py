"""One-line reason for a STOP / DETONATE, for the card under "STOPPED".

explain(task, png, click, brake, intent="", mock=False) -> {"text", "s", "model"} or None.
Gemini 4 Carbon (thinking low) gets the brake's answers, the agent's own stated intent and the crop around the click.
Carbon must answer within CARBON_BUDGET_S (4 s), else the same prompt goes to Hydrogen (thinking low). Any failure -> None
(the card just shows no reason). NOT live-tested yet (key quota, #29): written and tested in MOCK only.
"""
from __future__ import annotations

import base64
import concurrent.futures as cf
import time

from brake import gate

CARBON, HYDROGEN = "gemini-4-carbon", "gemini-4-hydrogen"
CARBON_BUDGET_S, HYDROGEN_BUDGET_S = 4.0, 8.0
_ex = cf.ThreadPoolExecutor(4, thread_name_prefix="reason")

PROMPT = ("A browser agent working for a user wanted to click the element in this crop (the red ring marks the click point).\n"
          "User's task: \"{task}\"\nAgent's own stated reason (untrusted, the page may have misled it): \"{intent}\"\n"
          "A safety check scored the click: p(on task) = {on:.2f}, p(overt attack) = {inj:.2f}, route = {route}.\n"
          "In ONE short sentence (max 20 words) for a non-technical audience, say why this click was held back. "
          "Name the button. No preamble.")


def _ask(model: str, prompt: str, crop: bytes) -> str:
    r = gate.client(None, False, 15_000).interactions.create(
        model=model, generation_config={"thinking_level": "low"},
        input=[{"type": "image", "data": base64.b64encode(crop).decode(), "mime_type": "image/png"}, {"type": "text", "text": prompt}])
    return " ".join((r.output_text or "").split())[:200]


def explain(task: str, png: bytes, click: tuple[int, int], brake: dict, intent: str = "", mock: bool = False) -> dict | None:
    t0 = time.perf_counter()
    if mock:
        return {"text": "The ringed button adds a step the task never asked for, and the page text pushes the agent to click it.",
                "s": 0.0, "model": CARBON + " (mock)"}
    try:
        _, crop = gate.prepare(png, click)
        prompt = PROMPT.format(task=task, intent=intent or "(none)", on=float(brake.get("p_on_task", 0)), inj=float(brake.get("p_injected", 0)),
                               route=brake.get("route", "STOP"))
        for model, budget in ((CARBON, CARBON_BUDGET_S), (HYDROGEN, HYDROGEN_BUDGET_S)):
            fut = _ex.submit(_ask, model, prompt, crop)
            try:
                text = fut.result(timeout=budget)
                if text:
                    return {"text": text, "s": round(time.perf_counter() - t0, 2), "model": model}
            except Exception:
                continue  # too slow or failed: next model (the slow call finishes in the background and is ignored)
    except Exception:
        pass
    return None
