"""Shop MCP client (https://mcp.shop.com/, no account or key; docs https://shop.dev/docs/quickstart.md).

search(query) -> first product as {"title", "price", "image", "seller", "shop", "variant_id", "url"}
checkout(shop, variant_id) -> {"id", "status", "continue_url", "total"}

Shop MCP rules: fetch live (no caching, no re-hosted images), keep URLs exactly as returned, and the shopper pays on
the merchant's page via `continue_url`; we never call complete_checkout.
"""
from __future__ import annotations

import json
import urllib.request

URL = "https://mcp.shop.com/"
PROTO = "2026-07-28"


def call(tool: str, arguments: dict, timeout: float = 20) -> dict:
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": tool, "arguments": arguments,
        "_meta": {"io.modelcontextprotocol/protocolVersion": PROTO,
                  "io.modelcontextprotocol/clientInfo": {"name": "click-brake", "version": "0.1"},
                  "io.modelcontextprotocol/clientCapabilities": {}}}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTO, "Mcp-Method": "tools/call", "Mcp-Name": tool})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        out = json.loads(f.read())
    if out.get("error"):
        raise RuntimeError(out["error"].get("message", "Shop MCP error"))
    res = out.get("result") or {}
    if res.get("isError"):
        raise RuntimeError(" ".join(p.get("text", "") for p in res.get("content", [])) or f"{tool} failed")
    return res.get("structuredContent") or {}


def money(m: dict) -> str:
    return f"{m['amount'] / 100:,.2f} {m['currency']}" if m else ""


def search(query: str, country: str = "US") -> dict:
    doc = call("search_catalog", {"catalog": {"query": query, "context": {"address_country": country, "currency": "USD"},
                                              "pagination": {"limit": 5}}})
    for p in doc.get("products", []):
        v = (p.get("variants") or [{}])[0]
        if v.get("id") and (v.get("seller") or {}).get("domain"):
            media = (p.get("media") or v.get("media") or [{}])
            return {"title": p.get("title", ""), "price": money(v.get("price") or {}),
                    "image": (media[0] or {}).get("url", ""), "seller": v["seller"].get("name", ""),
                    "shop": v["seller"]["domain"], "variant_id": v["id"], "url": p.get("url") or v.get("url", "")}
    raise RuntimeError(f"no purchasable product for {query!r}")


def checkout(shop: str, variant_id: str, country: str = "US") -> dict:
    doc = call("create_checkout", {"shop": shop, "checkout": {
        "line_items": [{"item": {"id": variant_id}, "quantity": 1}], "context": {"address_country": country}}})
    total = next((t for t in doc.get("totals", []) if t.get("type") == "total"), {})
    amt = f"{total['amount'] / 100:,.2f} {doc.get('currency', '')}".strip() if "amount" in total else ""
    return {"id": doc.get("id"), "status": doc.get("status"), "continue_url": doc.get("continue_url"),
            "total": amt or total.get("display_text", "")}


if __name__ == "__main__":
    p = search("wireless headphones")
    print(json.dumps({k: v for k, v in p.items()}, indent=1))
