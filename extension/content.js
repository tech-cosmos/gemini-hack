// Click-Brake content script: hold every click (trusted, synthetic or CDP-driven), ask the brake, then let it
// through (PASS) or show a card (STOP / DETONATE). Only "click" is braked; pages that act on mousedown are not.
(() => {
  let enabled = true;
  let bypass = false; // true while we re-dispatch an approved click, so we don't brake it again
  let host = null;    // our overlay's shadow host; clicks inside it are never braked

  chrome.storage.local.get({ enabled: true }).then((s) => (enabled = s.enabled));
  chrome.storage.onChanged.addListener((c) => { if (c.enabled) enabled = c.enabled.newValue; });

  function label(el) {
    const t = (el.innerText || el.value || el.getAttribute("aria-label") || el.title || "").trim();
    return t.replace(/\s+/g, " ").slice(0, 80);
  }

  function clickable(el) {
    return (el.closest && el.closest("a,button,input,select,textarea,label,summary,[role=button],[role=link],[onclick]")) || el;
  }

  function replay(target, e) {
    bypass = true;
    try {
      target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, composed: true, view: window,
        clientX: e.clientX, clientY: e.clientY, screenX: e.screenX, screenY: e.screenY, button: 0, detail: 1 }));
    } finally { bypass = false; }
  }

  function onClick(e) {
    if (!enabled || bypass || (host && e.composedPath().includes(host))) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const target = clickable(e.target);
    const msg = { type: "brake", x: e.clientX, y: e.clientY, dpr: window.devicePixelRatio || 1, target_text: label(target) };
    badge("Click-Brake: checking this click…");
    chrome.runtime.sendMessage(msg).then((r) => {
      if (r && r.route === "PASS") { clear(); replay(target, e); return; }
      card(r || { error: "no answer" }, target, e);
    }, (err) => card({ error: String(err) }, target, e));
  }
  window.addEventListener("click", onClick, true);

  // ---- overlay (shadow DOM so the page's CSS can't restyle or hide it) ----
  function root() {
    if (!host) {
      host = document.createElement("click-brake-overlay");
      host.attachShadow({ mode: "open" });
      host.style.cssText = "position:fixed;top:16px;right:16px;z-index:2147483647;";
    }
    if (!host.isConnected) document.documentElement.appendChild(host);
    return host.shadowRoot;
  }
  function clear() { if (host) host.remove(); }
  function badge(text) {
    root().innerHTML = `<div style="font:13px system-ui;background:#222;color:#fff;padding:8px 12px;border-radius:8px">${text}</div>`;
  }
  const fmt = (v) => (typeof v === "number" ? v.toFixed(2) : "–");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function card(r, target, e) {
    const err = r.error;
    const color = err ? "#8a6d00" : r.route === "STOP" ? "#b42318" : "#b54708";
    const title = err ? "Click-Brake could not check this click" : "Click-Brake stopped this click";
    const body = err ? `<div>${esc(err)}</div><div style="opacity:.8">The click is held. Is the API running?</div>`
      : `<div>Route: <b id="cb-route">${esc(r.route)}</b> · on task ${fmt(r.p_on_task)} · injected ${fmt(r.p_injected)} · ${fmt(r.latency_s)} s</div>
         <div style="opacity:.8">Clicked: “${esc(label(target))}” · ${esc(r.model || "")}</div>`;
    const det = !err && r.route === "DETONATE" && r.detonateEnabled
      ? `<button id="cb-det">Detonate in sandbox (slow: 40–95 s)</button>` : "";
    root().innerHTML = `<div id="cb-card" data-route="${esc(err ? "ERROR" : r.route)}" style="font:13px system-ui;width:340px;background:#fff;color:#111;
      border:3px solid ${color};border-radius:10px;padding:12px 14px;box-shadow:0 8px 30px rgba(0,0,0,.3)">
      <div style="font-weight:700;color:${color};font-size:15px;margin-bottom:6px">${title}</div>${body}
      <div id="cb-det-out" style="margin-top:6px"></div>
      <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">${det}
        <button id="cb-allow">Click anyway</button><button id="cb-close">Keep stopped</button></div></div>`;
    const $ = (id) => host.shadowRoot.getElementById(id);
    $("cb-close").onclick = clear;
    $("cb-allow").onclick = () => { clear(); replay(target, e); };
    if (det) $("cb-det").onclick = () => {
      $("cb-det").disabled = true;
      $("cb-det-out").textContent = "Detonating in a Managed Agents sandbox…";
      chrome.runtime.sendMessage({ type: "detonate", x: e.clientX, y: e.clientY, page_html: document.documentElement.outerHTML })
        .then((d) => {
          if (d.error) { $("cb-det-out").textContent = "Detonation failed: " + d.error; return; }
          $("cb-det-out").innerHTML = `Sandbox verdict: <b>${esc(d.verdict)}</b> (${fmt(d.s)} s): ${esc(d.what_happened || "")}`;
          if (d.verdict === "benign") { clear(); replay(target, e); }
        });
    };
  }
})();
