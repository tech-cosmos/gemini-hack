"""Click-Brake HTTP API, so any agent or browser (the Chrome extension in extension/) can ask the brake before a click.

  POST /v1/brake     {task, screenshot_png_b64, click: [x, y], intent?, viewport?: [w, h], target_text?, mock_label?}
                     -> exactly brake.check()'s dict (route PASS/DETONATE/STOP, p_on_task, p_injected, ...)
  POST /v1/detonate  {page_html, click: [x, y], task}  -> managed.detonate.detonate() result. SLOW: 40-95 s.
  GET  /v1/health    -> {"ok": true, "mock": bool, ...}

Bring your own key: header `X-Gemini-Key`. If present it is used for that one request; else the server's .env key.
Limitation: brake.check() and detonate() build their genai clients from the environment and cache them, so a BYO-key
call swaps the env key under a process-wide lock and clears those caches. Every model call goes through that lock, so
calls are serialized (a 60 s detonation blocks brake calls on this server meanwhile). The key is never logged.

MOCK=1: no network. mock_label (only honoured when MOCK=1) picks the canned answer (injected -> STOP, task -> PASS,
other -> DETONATE). Without it the mock guesses from target_text: every word of the clicked element's label appears in
the task -> "task", else "injected". That heuristic is for offline tests only; the real brake looks at the screenshot.
Run: .venv/bin/python -m api.server [--port 8766]
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from brake import gate  # loads .env

W, H = gate.W, gate.H
_model_lock = threading.Lock()
KEY_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


@contextlib.contextmanager
def model_env(key: str | None):
    """Run one model call with `key` (BYO) or the server's key. Serialized; restores env and client caches after."""
    with _model_lock:
        if not key:
            yield
            return
        from managed import detonate as det
        saved = {k: os.environ.get(k) for k in KEY_VARS + (gate.ALT_KEY_ENV,)}
        saved_clients, saved_det = gate._clients, det._client
        try:
            for k in KEY_VARS:
                os.environ[k] = key
            os.environ.pop(gate.ALT_KEY_ENV, None)  # never fall back to the server's alternate key on a user's 429
            gate._clients, det._client = {}, None
            yield
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            gate._clients, det._client = saved_clients, saved_det


def fit(png: bytes, click, viewport=None) -> tuple[bytes, tuple[int, int]]:
    """Scale the screenshot to the 1280x800 page the brake question describes, and the click with it.
    `click` is in screenshot pixels, unless `viewport` [w, h] is given: then it is in CSS pixels of that viewport."""
    from PIL import Image
    im = Image.open(io.BytesIO(png))
    w, h = im.size
    x, y = float(click[0]), float(click[1])
    if viewport:
        x, y = x * w / float(viewport[0]), y * h / float(viewport[1])
    if (w, h) == (W, H):
        return png, (int(round(x)), int(round(y)))
    b = io.BytesIO()
    im.convert("RGB").resize((W, H)).save(b, "PNG")
    return b.getvalue(), (int(round(x * W / w)), int(round(y * H / h)))


def mock_label_for(body: dict) -> str | None:
    if body.get("mock_label"):
        return str(body["mock_label"])
    words = re.findall(r"[a-z0-9]+", str(body.get("target_text", "")).lower())
    task = set(re.findall(r"[a-z0-9]+", str(body.get("task", "")).lower()))
    if not words:
        return None
    return "task" if all(w in task for w in words) else "injected"


def brake(body: dict, key: str | None) -> dict:
    png = base64.b64decode(body["screenshot_png_b64"])
    png, xy = fit(png, body["click"], body.get("viewport"))
    mock = gate.mock_default()
    with model_env(None if mock else key):
        return gate.check(str(body["task"]), png, xy, intent=str(body.get("intent", "")),
                          mock=mock, mock_label=mock_label_for(body) if mock else None)


def detonate(body: dict, key: str | None) -> dict:
    if gate.mock_default():
        return {"what_happened": "mock: the click POSTs card data to evil.example", "verdict": "malicious",
                "ran_browser": False, "requests": ["POST https://evil.example/collect"], "s": 0.0, "mock": True}
    from managed import detonate as det
    with model_env(key):
        return det.detonate(str(body["page_html"]), (int(body["click"][0]), int(body["click"][1])), str(body["task"]))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Gemini-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/health":
            return self._send(200, {"ok": True, "mock": gate.mock_default(), "model": gate.MODEL,
                                    "question_version": gate.QUESTION_VERSION, "page": [W, H]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except Exception:
            return self._send(400, {"error": "body must be JSON"})
        key = (self.headers.get("X-Gemini-Key") or "").strip() or None
        route = {"/v1/brake": brake, "/v1/detonate": detonate}.get(self.path.rstrip("/"))
        if not route:
            return self._send(404, {"error": "not found"})
        try:
            self._send(200, route(body, key))
        except KeyError as e:
            self._send(400, {"error": f"missing field {e}"})
        except Exception as e:  # never echo the key: short_error gives one safe line
            self._send(502 if gate.busy(e) else 500, {"error": gate.short_error(e)})

    def log_message(self, fmt, *args):  # request line only; headers (and the key) are never logged
        print(f"[api] {self.address_string()} {fmt % args}", flush=True)


def serve(port: int = 8766, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8766)))
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    s = serve(a.port, a.host)
    print(f"Click-Brake API on http://{a.host}:{a.port}  (mock={gate.mock_default()})", flush=True)
    s.serve_forever()
