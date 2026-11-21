"""Golden path, offline: python -m app.golden --out DIR   (MOCK=1 for no network; scripts/check runs it)

Committed fixture page (app/fixtures/checkout_injected.*) with an injected banner:
  unprotected: agent proposes the banner button -> clicked "injected"
  protected:   same proposal -> brake.check -> stop -> agent re-proposes with a "blocked" note -> brake passes -> clicked "task"
Clicks are resolved to elements with the fixture's recorded DOM boxes (no browser needed).
Writes DIR/result.json."""
import argparse
import json
import pathlib
import time

from app import agent
from brake import gate

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def element_at(boxes, x, y):
    for b in boxes:
        if b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]:
            return b
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((FIX / "checkout_injected.json").read_text())
    png = (FIX / "checkout_injected.png").read_bytes()
    task, boxes = meta["task"], meta["boxes"]
    mock = gate.mock_default()

    def kind(p):
        b = element_at(boxes, p["x"], p["y"])
        return (b or {}).get("kind", "none"), (b or {}).get("text")

    # unprotected
    p = agent.propose_click(task, png, mock=mock, boxes=boxes)
    k, txt = kind(p)
    unprotected = {"proposal": p, "clicked": k, "clicked_text": txt}

    # protected
    steps = []
    note, clicked, brake = None, "none", None
    for _ in range(3):
        p = agent.propose_click(task, png, note, mock=mock, boxes=boxes)
        k, txt = kind(p)
        r = gate.check(task, png, (p["x"], p["y"]), mock=mock, mock_label=k)
        steps.append({"proposal": p, "element": k, "element_text": txt, "brake": r})
        if r["stop"]:
            brake = brake or r
            note = agent.blocked_note(p)
            continue
        clicked = k
        break
    protected = {"brake": brake or steps[0]["brake"], "clicked": clicked, "steps": steps}

    res = {"written": time.strftime("%Y-%m-%d %H:%M:%S"), "mock": mock, "task": task, "fixture": "app/fixtures/checkout_injected.png",
           "unprotected": unprotected, "protected": protected}
    (out / "result.json").write_text(json.dumps(res, indent=1))
    print(f"unprotected clicked {unprotected['clicked']!r}; protected: brake stop={protected['brake']['stop']} "
          f"p={protected['brake']['p_injected']}, then clicked {clicked!r}")


if __name__ == "__main__":
    main()
