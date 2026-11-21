"""Headless Chrome via Playwright: render a page to a 1280x800 PNG, list clickable boxes, and hit-test a click
against the DOM. Sync Playwright must stay on one thread, so every call runs on one dedicated worker thread."""
import concurrent.futures as cf

from app.page import W, H

_ex = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")
_state = {}

_BOXES_JS = """() => [...document.querySelectorAll('button, a')].filter(e => e.id).map(e => {
  const r = e.getBoundingClientRect(); return {id: e.id, text: e.innerText.trim(), x: r.x, y: r.y, w: r.width, h: r.height}; })"""
_HIT_JS = """([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return null;
  const b = e.closest('button, a') || e; return {id: b.id || null, tag: b.tagName.toLowerCase(), text: (b.innerText || '').trim().slice(0, 80)}; }"""


def _page():
    if "page" not in _state:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            br = pw.chromium.launch(channel="chrome")
        except Exception:
            br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H})
        _state.update(pw=pw, br=br, page=pg, blocked=[])

        def guard(route):
            # nothing leaves the app's browser for a non-local host: requests to evil.example (or anywhere else) are aborted and recorded
            req = route.request
            if req.url.startswith(("http://127.0.0.1", "http://localhost", "data:", "about:")):
                return route.continue_()
            _state["blocked"].append({"method": req.method, "url": req.url, "body": (req.post_data or "")[:300]})
            route.abort()
        pg.route("**/*", guard)
    return _state["page"]


def _shot(html: str):
    pg = _page()
    pg.set_content(html)
    return pg.screenshot(), pg.evaluate(_BOXES_JS)


def _hit(html: str, x: int, y: int):
    pg = _page()
    pg.set_content(html)
    return pg.evaluate(_HIT_JS, [x, y])


def screenshot(html: str) -> tuple[bytes, list[dict]]:
    """-> (png bytes, [{"id","text","x","y","w","h"}, ...] for every button/link with an id)."""
    return _ex.submit(_shot, html).result()


def hit(html: str, x: int, y: int) -> dict | None:
    """The clickable element at (x, y), from the DOM: {"id","tag","text"} or None."""
    return _ex.submit(_hit, html, int(x), int(y)).result()


def _fire(html: str, x: int, y: int):
    pg = _page()
    pg.set_content(html)
    _state["blocked"].clear()
    pg.mouse.click(x, y)
    pg.wait_for_timeout(400)
    return {"blocked": list(_state["blocked"]), "state": pg.evaluate("() => document.body.getAttribute('data-state')"),
            "html_after": pg.evaluate("() => '<!doctype html>' + document.documentElement.outerHTML")}


def fire(html: str, x: int, y: int) -> dict:
    """Really click (x, y) in the app's own headless Chrome. Every outside request is aborted and listed in "blocked"
    (so a hijack shows what it WOULD have sent, without sending it). -> {"blocked", "state", "html_after"}"""
    return _ex.submit(_fire, html, int(x), int(y)).result()
