"""Offline end-to-end test of the Chrome extension (MOCK=1, no Gemini calls).

Starts the API (MOCK) and a static server for app/fixtures, loads extension/ unpacked into Playwright's bundled Chromium
(branded Google Chrome 137+ ignores --load-extension), sets the task on the options page, then:
  1. clicks the injected "Verify session" button -> the overlay appears and the button's handler did NOT run;
  2. clicks "Place order" -> the click goes through (body[data-state] = "✓ Order placed").
Run: .venv/bin/python -m extension.test_extension       (HEADED=1 to watch it)
"""
from __future__ import annotations

import functools
import json
import os
import pathlib
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

os.environ["MOCK"] = "1"
from api import server as api  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
FIX = ROOT / "app/fixtures"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def chromium_path(p) -> str | None:
    """Playwright's own Chromium (loads unpacked extensions); else the newest one already in the cache; else CHROMIUM."""
    if os.environ.get("CHROMIUM"):
        return os.environ["CHROMIUM"]
    if pathlib.Path(p.chromium.executable_path).exists():
        return None
    apps = sorted(pathlib.Path.home().glob("Library/Caches/ms-playwright/chromium-*/chrome-*/*.app/Contents/MacOS/*")) + \
        sorted(pathlib.Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux*/chrome"))
    return str(apps[-1]) if apps else None


def main():
    from playwright.sync_api import sync_playwright
    a = api.serve(0)
    threading.Thread(target=a.serve_forever, daemon=True).start()
    st = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(FIX)))
    threading.Thread(target=st.serve_forever, daemon=True).start()
    api_url = f"http://127.0.0.1:{a.server_address[1]}"
    page_url = f"http://127.0.0.1:{st.server_address[1]}/checkout_injected.html"
    meta = json.loads((FIX / "checkout_injected.json").read_text())
    centre = {b["kind"]: (b["x"] + b["w"] / 2, b["y"] + b["h"] / 2) for b in meta["boxes"]}

    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        ctx = p.chromium.launch_persistent_context(
            tmp, channel="chromium", executable_path=chromium_path(p), headless=not os.environ.get("HEADED"), viewport={"width": 1280, "height": 800},
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15_000)
        ext_id = sw.url.split("/")[2]

        opt = ctx.new_page()
        opt.goto(f"chrome-extension://{ext_id}/options.html")
        opt.wait_for_function("document.getElementById('apiUrl').value !== ''")
        opt.fill("#task", meta["task"])
        opt.fill("#apiUrl", api_url)
        opt.fill("#apiKey", "byo-test-not-a-key")
        opt.click("#save")
        opt.wait_for_selector("#saved:has-text('Saved')")
        opt.close()

        page = ctx.new_page()
        page.goto(page_url)
        page.wait_for_timeout(300)

        page.mouse.click(*centre["injected"])
        page.wait_for_selector("click-brake-overlay >> #cb-card", timeout=10_000)
        route = page.get_attribute("click-brake-overlay >> #cb-card", "data-route")
        state = page.evaluate("document.body.getAttribute('data-state')")
        assert route == "STOP", route
        assert state is None, f"injected click went through: {state}"
        print(f"1. injected click: overlay shown, route={route}, body[data-state]={state}")

        page.click("click-brake-overlay >> #cb-close")
        page.mouse.click(*centre["task"])
        page.wait_for_function("document.body.getAttribute('data-state') !== null", timeout=10_000)
        state = page.evaluate("document.body.getAttribute('data-state')")
        assert state == "✓ Order placed", state
        print(f"2. task click: went through, body[data-state]={state!r}")
        ctx.close()
    a.shutdown(); st.shutdown()
    print("extension/test_extension.py: PASS")


if __name__ == "__main__":
    main()
