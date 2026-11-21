"""Click-Brake live demo app (stdlib http.server + plain HTML/JS).

Run:  .venv/bin/python -m app.server            -> http://localhost:8765
      MOCK=1 .venv/bin/python -m app.server     -> no network (canned agent + brake), for rehearsal / venue Wi-Fi loss
      PORT=9000 ... to change the port.

The browser page (app/static/index.html) drives the steps so each one shows up as it happens:
  POST /api/shot     {mode, attack}                  -> render page in headless Chrome: {page_id, html, boxes, s}
  POST /api/propose  {page_id, task, note, replay}   -> agent.propose_click + DOM hit-test: {proposal, element}
  POST /api/brake    {page_id, task, x, y, kind}     -> brake.check dict
  POST /api/explain  {page_id, task, x, y, brake}    -> reason.explain (hook) + er2.circle_target (hook)
  POST /api/finish   {page_id, task}                 -> finisher.finish (hook, Dan's managed/ lane)
  GET  /page/<id>.html                               -> the rendered page (for the Managed Agents finisher)
"""
import base64
import json
import os
import pathlib
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import agent, browser, er2, finisher, page, reason
from brake import gate

STATIC = pathlib.Path(__file__).resolve().parent / "static"
PAGES: dict[str, dict] = {}
_lock = threading.Lock()


def _mock(body) -> bool:
    m = body.get("mock")
    return gate.mock_default() if m is None else bool(m)


def api_shot(b):
    mode = b.get("mode", "banner")
    attack = b.get("attack") or None
    html = page.render(mode, attack)
    t = time.perf_counter()
    png, boxes = browser.screenshot(html)
    boxes = [x | {"kind": page.kind_of(x["id"], mode)} for x in boxes]
    pid = uuid.uuid4().hex[:10]
    with _lock:
        PAGES[pid] = {"html": html, "png": png, "boxes": boxes, "mode": mode}
        for k in list(PAGES)[:-50]:
            PAGES.pop(k, None)
    return {"page_id": pid, "html": html, "boxes": boxes, "s": round(time.perf_counter() - t, 3), "size": [page.W, page.H]}


def api_propose(b):
    pg = PAGES[b["page_id"]]
    mock = _mock(b)
    note = b.get("note")
    if isinstance(note, dict):  # the previous proposal that the brake blocked
        note = agent.blocked_note(note)
    b["note"] = note
    if b.get("replay") and not note:
        # Recorded-hijack fallback (DEMO.md row 0:30): the proposal is the injected element's centre, not a model call.
        s = next((x for x in pg["boxes"] if x["kind"] == "injected"), None)
        if s:
            p = {"x": int(s["x"] + s["w"] / 2), "y": int(s["y"] + s["h"] / 2), "label": s["text"], "s": 0.0, "model": "replayed proposal"}
        else:
            p = agent.propose_click(b["task"], pg["png"], b.get("note"), mock=mock, boxes=pg["boxes"])
    else:
        p = agent.propose_click(b["task"], pg["png"], b.get("note"), mock=mock, boxes=pg["boxes"])
    h = browser.hit(pg["html"], p["x"], p["y"]) or {}
    el = {"id": h.get("id"), "text": h.get("text", ""), "kind": page.kind_of(h.get("id"), pg["mode"])}
    return {"proposal": p, "element": el}


def api_brake(b):
    pg = PAGES[b["page_id"]]
    return gate.check(b["task"], pg["png"], (int(b["x"]), int(b["y"])), mock=_mock(b), mock_label=b.get("kind"))


def api_explain(b):
    pg = PAGES[b["page_id"]]
    return {"reason": reason.explain(b["task"], pg["png"], (int(b["x"]), int(b["y"])), b.get("brake") or {}),
            "circle": er2.circle_target(b["task"], pg["png"])}


def api_finish(b, host):
    return {"finish": finisher.finish(b["task"], f"http://{host}/page/{b['page_id']}.html")}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/config":
            return self._send(200, json.dumps({"mock": gate.mock_default(), "agent_model": agent.MODEL, "brake_model": gate.MODEL,
                                               "threshold": gate.THRESHOLD, "task": page.TASK, "attack": page.DEFAULT_ATTACK,
                                               "cookie": page.COOKIE}).encode())
        if path.startswith("/page/") and path.endswith(".html"):
            pg = PAGES.get(path[6:-5])
            if pg:
                return self._send(200, pg["html"].encode(), "text/html; charset=utf-8")
        if path.startswith("/png/"):
            pg = PAGES.get(path[5:].removesuffix(".png"))
            if pg:
                return self._send(200, pg["png"], "image/png")
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        path = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        try:
            b = json.loads(self.rfile.read(n) or b"{}")
            fn = {"/api/shot": api_shot, "/api/propose": api_propose, "/api/brake": api_brake, "/api/explain": api_explain}.get(path)
            if path == "/api/finish":
                out = api_finish(b, self.headers.get("Host", "localhost"))
            elif fn:
                out = fn(b)
            else:
                return self._send(404, b'{"error":"not found"}')
            self._send(200, json.dumps(out).encode())
        except Exception as e:
            traceback.print_exc()
            self._send(500, json.dumps({"error": f"{type(e).__name__}: {str(e)[:300]}"}).encode())


def main():
    port = int(os.environ.get("PORT", "8765"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Click-Brake app on http://localhost:{port}  (mock={gate.mock_default()}, agent={agent.MODEL}, brake={gate.MODEL})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
