"""Offline test of the Click-Brake API (MOCK=1, no network): start it on a free port, post the golden fixture.
Run: MOCK=1 .venv/bin/python -m api.test_api"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import threading
import urllib.request

os.environ["MOCK"] = "1"
from api import server  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent.parent / "app/fixtures"
KEYS = ("route", "p_on_task", "p_injected", "confidence", "stop", "threshold", "latency_s", "model", "question_version")


def post(url, body, headers=None):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def main():
    s = server.serve(0)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{s.server_address[1]}"
    meta = json.loads((FIX / "checkout_injected.json").read_text())
    png = base64.b64encode((FIX / "checkout_injected.png").read_bytes()).decode()
    centre = {b["kind"]: [b["x"] + b["w"] / 2, b["y"] + b["h"] / 2] for b in meta["boxes"]}
    assert json.loads(urllib.request.urlopen(base + "/v1/health").read())["mock"] is True
    want = {"injected": "STOP", "task": "PASS", "other": "DETONATE"}
    for kind, route in want.items():
        r = post(base + "/v1/brake", {"task": meta["task"], "screenshot_png_b64": png, "click": centre[kind], "mock_label": kind},
                 {"X-Gemini-Key": "byo-test-not-a-key"})
        assert set(KEYS) <= set(r), r
        assert r["route"] == route and r["stop"] == (route != "PASS"), (kind, r)
    # no mock_label: the mock guesses from the clicked element's label
    r = post(base + "/v1/brake", {"task": meta["task"], "screenshot_png_b64": png, "click": centre["task"], "target_text": "Place order"})
    assert r["route"] == "PASS", r
    r = post(base + "/v1/brake", {"task": meta["task"], "screenshot_png_b64": png, "click": centre["injected"], "target_text": "Verify session"})
    assert r["route"] == "STOP", r
    # click scaling: CSS click (100, 50) in a 640x400 viewport -> (200, 100) on the 1280x800 page
    assert server.fit((FIX / "checkout_injected.png").read_bytes(), [100, 50], viewport=[640, 400])[1] == (200, 100)
    d = post(base + "/v1/detonate", {"page_html": "<html></html>", "click": centre["injected"], "task": meta["task"]})
    assert d["verdict"] in ("malicious", "benign", "unclear"), d
    # BYO key: swapped in for the call only, then the server's env and client caches come back
    before = {k: os.environ.get(k) for k in server.KEY_VARS}
    clients = server.gate._clients
    with server.model_env("byo-test-not-a-key"):
        assert os.environ["GEMINI_API_KEY"] == "byo-test-not-a-key" and server.gate._clients is not clients
    assert {k: os.environ.get(k) for k in server.KEY_VARS} == before and server.gate._clients is clients
    s.shutdown()
    print("api/test_api.py: PASS (health, brake STOP/PASS/DETONATE, target_text mock, click scaling, detonate mock)")


if __name__ == "__main__":
    main()
