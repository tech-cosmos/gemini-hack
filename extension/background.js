// Click-Brake service worker: screenshot the tab, ask the API, answer the content script.
const DEFAULTS = { apiUrl: "http://localhost:8766", apiKey: "", task: "", detonate: false, enabled: true };

async function settings() {
  return { ...DEFAULTS, ...(await chrome.storage.local.get(Object.keys(DEFAULTS))) };
}

async function post(path, body, s) {
  const headers = { "Content-Type": "application/json" };
  if (s.apiKey) headers["X-Gemini-Key"] = s.apiKey; // your own key goes only to the API URL you set
  const r = await fetch(s.apiUrl.replace(/\/+$/, "") + path, { method: "POST", headers, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}

async function brake(msg, sender) {
  const s = await settings();
  const shot = await chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: "png" });
  const b64 = shot.slice(shot.indexOf(",") + 1);
  // click in screenshot pixels: CSS pixels x devicePixelRatio (the API scales to its 1280x800 page)
  const click = [Math.round(msg.x * msg.dpr), Math.round(msg.y * msg.dpr)];
  const res = await post("/v1/brake", { task: s.task, screenshot_png_b64: b64, click, target_text: msg.target_text,
                                        intent: msg.intent || "" }, s);
  return { ...res, detonateEnabled: s.detonate };
}

async function detonate(msg) {
  const s = await settings();
  return post("/v1/detonate", { page_html: msg.page_html, click: [Math.round(msg.x), Math.round(msg.y)], task: s.task }, s);
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  const job = msg.type === "brake" ? brake(msg, sender) : msg.type === "detonate" ? detonate(msg) : null;
  if (!job) return false;
  job.then(reply, (e) => reply({ error: String(e && e.message || e) }));
  return true; // async reply
});

chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
