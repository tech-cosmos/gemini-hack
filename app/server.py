"""Click-Brake live demo app (stdlib http.server + plain HTML/JS).

Run:  .venv/bin/python -m app.server            -> http://localhost:8765
      MOCK=1 .venv/bin/python -m app.server     -> no network (canned agent + brake), for rehearsal / venue Wi-Fi loss
      PORT=9000 ... to change the port.

The browser page (app/static/index.html) drives the steps so each one shows up as it happens:
  POST /api/shot     {site, mode, attack}            -> render page in headless Chrome: {page_id, html, boxes, s}
  POST /api/propose  {page_id, task, note, replay, backend} -> agent.propose_click + DOM hit-test: {proposal, element}
  POST /api/brake    {page_id, task, x, y, kind, intent} -> brake.check dict (q2: route PASS / DETONATE / STOP)
  POST /api/detonate_poll {job}                      -> {done, elapsed_s, result}: the detonation api_brake started on DETONATE
  POST /api/fire     {page_id, x, y}                 -> really click in the app's Chrome; outside requests aborted: {blocked, state, html_after}
  POST /api/detonate {page_id, task, x, y}           -> synchronous detonation (app/detonate.py -> managed/detonate.py)
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

from app import agent, browser, detonate, er2, finisher, page, reason
from brake import gate

STATIC = pathlib.Path(__file__).resolve().parent / "static"
PAGES: dict[str, dict] = {}
_lock = threading.Lock()


def _mock(body) -> bool:
    m = body.get("mock")
    return gate.mock_default() if m is None else bool(m)


def api_shot(b):
    mode = b.get("mode", "banner")
    site = b.get("site") or "shop"
    attack = b.get("attack") or None
    html = page.render(mode, attack, site)
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
            p = {"x": int(s["x"] + s["w"] / 2), "y": int(s["y"] + s["h"] / 2), "label": s["text"], "intent": f"Click '{s['text']}'.",
                 "s": 0.0, "model": "replayed proposal"}
        else:
            p = agent.propose_click(b["task"], pg["png"], b.get("note"), mock=mock, boxes=pg["boxes"], backend=b.get("backend"))
    else:
        p = agent.propose_click(b["task"], pg["png"], b.get("note"), mock=mock, boxes=pg["boxes"], backend=b.get("backend"))
    h = browser.hit(pg["html"], p["x"], p["y"]) or {}
    el = {"id": h.get("id"), "text": h.get("text", ""), "kind": page.kind_of(h.get("id"), pg["mode"])}
    return {"proposal": p, "element": el}


JOBS: dict[str, dict] = {}


def _detonate_job(jid, html, xy, task, mock, kind):
    t = time.perf_counter()
    try:
        if mock:
            time.sleep(4.0)
            res = ({"what_happened": "mock: the click POSTed the card number to https://evil.example/collect", "verdict": "malicious"} if kind == "injected"
                   else {"what_happened": "mock: the click did what its label says; no outside request", "verdict": "benign"})
            res |= {"mock": True}
        else:
            res = detonate.detonate(html, xy, task)
    except Exception as e:  # fail closed, never a traceback in the UI
        res = {"what_happened": f"detonation failed: {gate.short_error(e)}", "verdict": "unclear"}
    res.setdefault("s", round(time.perf_counter() - t, 2))
    JOBS[jid].update(done=True, result=res)


def start_detonation(pg, xy, task, mock, kind) -> str:
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"t0": time.time(), "done": False, "result": None}
    threading.Thread(target=_detonate_job, args=(jid, pg["html"], xy, task, mock, kind), daemon=True).start()
    return jid


def api_brake(b):
    """brake.check; when the route is DETONATE the sandboxed detonation starts at once in a background thread (40-90 s live)
    and its job id comes back as "job" (an app field next to the check() keys)."""
    pg = PAGES[b["page_id"]]
    xy = (int(b["x"]), int(b["y"]))
    r = gate.check(b["task"], pg["png"], xy, intent=b.get("intent") or "", mock=_mock(b), mock_label=b.get("kind"))
    if r["route"] == "DETONATE":
        r = r | {"job": start_detonation(pg, xy, b["task"], _mock(b), b.get("kind"))}
    return r


def api_detonate_poll(b):
    j = JOBS[b["job"]]
    return {"done": j["done"], "elapsed_s": round(time.time() - j["t0"], 1), "result": j["result"]}


def api_detonate(b):
    """Synchronous detonation (kept for scripts); the UI uses the background job from api_brake."""
    pg = PAGES[b["page_id"]]
    jid = start_detonation(pg, (int(b["x"]), int(b["y"])), b["task"], _mock(b), b.get("kind"))
    while not JOBS[jid]["done"]:
        time.sleep(0.2)
    return JOBS[jid]["result"]


def api_fire(b):
    """The allowed (or unprotected) click really happens in the app's own headless Chrome; outside requests are aborted."""
    pg = PAGES[b["page_id"]]
    return browser.fire(pg["html"], int(b["x"]), int(b["y"]))


def api_explain(b):
    pg = PAGES[b["page_id"]]
    return {"reason": reason.explain(b["task"], pg["png"], (int(b["x"]), int(b["y"])), b.get("brake") or {}),
            "circle": er2.circle_target(b["task"], pg["png"])}


def api_finish(b, host):
    pg = PAGES[b["page_id"]]
    if _mock(b):
        return {"finish": None}
    return {"finish": finisher.finish(b["task"], pg["html"], pg["mode"])}


REPLAYS = pathlib.Path(__file__).resolve().parent / "replays"


def _replay_path(site: str, brake: bool) -> pathlib.Path:
    assert site in page.SITES, site
    return REPLAYS / f"{site}_{'on' if brake else 'off'}.json"


def api_save_replay(b):
    """A finished live run recorded by the page (every API response + its wall time), saved for offline playback."""
    REPLAYS.mkdir(exist_ok=True)
    rec = {"recorded": time.strftime("%Y-%m-%d %H:%M:%S"), "site": b["site"], "brake": bool(b["brake"]), "task": b["task"],
           "mode": b["mode"], "attack": b.get("attack"), "outcome": b.get("outcome"), "events": b["events"]}
    p = _replay_path(b["site"], bool(b["brake"]))
    p.write_text(json.dumps(rec, indent=1))
    return {"saved": str(p.relative_to(REPLAYS.parent.parent)), "n_events": len(b["events"])}


def api_replay(b):
    p = _replay_path(b["site"], bool(b["brake"]))
    return json.loads(p.read_text()) if p.exists() else {"error": f"no recording {p.name}"}


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
            return self._send(200, json.dumps({"mock": gate.mock_default(), "agent_model": agent.MODEL, "cu_model": agent.CU_MODEL, "backend": agent.BACKEND, "brake_model": gate.MODEL,
                                               "threshold": gate.THRESHOLD, "question_version": gate.QUESTION_VERSION,
                                               "sites": {k: {"name": v["site"], "task": v["task"], "mode": v["mode"], "attack": v["attack"],
                                                             "done": v["done"], "prim": v["prim"], "cookie": page.cookie(k)} for k, v in page.SITES.items()},
                                               "default_site": page.DEFAULT_SITE}).encode())
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
            fn = {"/api/shot": api_shot, "/api/propose": api_propose, "/api/brake": api_brake, "/api/explain": api_explain,
                  "/api/detonate": api_detonate, "/api/detonate_poll": api_detonate_poll, "/api/fire": api_fire,
                  "/api/save_replay": api_save_replay, "/api/replay": api_replay}.get(path)
            if path == "/api/finish":
                out = api_finish(b, self.headers.get("Host", "localhost"))
            elif fn:
                out = fn(b)
            else:
                return self._send(404, b'{"error":"not found"}')
            self._send(200, json.dumps(out).encode())
        except agent.AgentBusy as e:
            msg = "API quota reached on this key — switch key or use replay" if e.quota else "Agent model busy: every retry and fallback failed"
            self._send(503, json.dumps({"error": msg, "busy": True, "quota": e.quota, "notes": e.notes}).encode())
        except Exception as e:
            busy, q = gate.busy(e), gate.quota(e)
            if not busy:
                traceback.print_exc()
            msg = "API quota reached on this key — switch key or use replay" if q else ("Model busy: " if busy else "Error: ") + gate.short_error(e)
            self._send(503 if busy else 500, json.dumps({"error": msg, "busy": busy, "quota": q}).encode())


def main():
    port = int(os.environ.get("PORT", "8765"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Click-Brake app on http://localhost:{port}  (mock={gate.mock_default()}, agent={agent.MODEL}, brake={gate.MODEL})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
