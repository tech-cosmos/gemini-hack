"""Rebuild the golden-path fixture (needs Chrome; the golden path itself only reads the committed files).
Run: .venv/bin/python -m app.fixtures.build"""
import json
import pathlib

from app import browser, page

D = pathlib.Path(__file__).resolve().parent

if __name__ == "__main__":
    html = page.render("banner")
    png, boxes = browser.screenshot(html)
    (D / "checkout_injected.html").write_text(html)
    (D / "checkout_injected.png").write_bytes(png)
    meta = {"mode": "banner", "task": page.TASK, "attack": page.DEFAULT_ATTACK, "size": [page.W, page.H],
            "boxes": [b | {"kind": page.kind_of(b["id"], "banner")} for b in boxes]}
    (D / "checkout_injected.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta["boxes"], indent=1))
