"""SHOPIFY=1: the Northwind shop site shows a REAL product from Shop MCP (live search, merchant image by its CDN URL,
not re-hosted), under the same template contract (#38). Any failure falls back to the designed fictional shop.

template() -> app/sites/shop.html with the live product swapped in, or None (use the normal site).
python -m shopify.site checkout  -> creates the real checkout for that product and prints its continue_url, where a
judge reviews and pays on the merchant's own page (we never complete checkouts).
"""
from __future__ import annotations

import html
import os
import pathlib
import re

from shopify import mcp

QUERY = os.environ.get("SHOPIFY_QUERY", "wireless headphones")
SHOP_HTML = pathlib.Path(__file__).resolve().parent.parent / "app/sites/shop.html"
_product: dict | None = None


def enabled() -> bool:
    return os.environ.get("SHOPIFY", "") not in ("", "0")


def product() -> dict:
    global _product  # one live search per server process, so every screenshot of a run shows the same item
    if _product is None:
        _product = mcp.search(QUERY)
    return _product


def template() -> str | None:
    if not enabled():
        return None
    try:
        p = product()
    except Exception:
        return None
    t = SHOP_HTML.read_text()
    title, price = html.escape(p["title"]), html.escape(p["price"])
    t = re.sub(r'<img src="data:image/[^"]+" alt="Aria Wireless Headphones"',
               f'<img src="{html.escape(p["image"])}" alt="{title}"', t, count=1)
    t = t.replace('Aria Wireless Headphones<small>Midnight · Bluetooth 5.4</small>',
                  f'{title}<small>Sold by {html.escape(p["seller"])} · via Shop</small>')
    t = t.replace("$129.00", price).replace("<small>USD</small>$133.99", f"{price} + shipping")
    return t


if __name__ == "__main__":
    import json
    import sys
    p = product()
    print(json.dumps(p, indent=1))
    if sys.argv[1:] == ["checkout"]:
        c = mcp.checkout(p["shop"], p["variant_id"])
        print("status:", c["status"], "| total:", c["total"])
        print("pay on the merchant's page:", c["continue_url"])
