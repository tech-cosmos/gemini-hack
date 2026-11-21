# Click-Brake Chrome extension + API

Brakes every click on any page: the click is held, the tab is screenshotted, the Click-Brake API (`api/server.py`,
which calls `brake.check()`, question q2) answers PASS / DETONATE / STOP. PASS re-dispatches the click on the same
element; STOP or DETONATE shows a card in the page. For DETONATE (with the option on) a button sends the page HTML to
the Managed Agents detonation chamber (`managed/detonate.py`, slow: 40–95 s); a "benign" verdict lets the click through.

## Run the API
```
.venv/bin/python -m api.server              # real brake, uses the server's .env key (or the caller's X-Gemini-Key)
MOCK=1 .venv/bin/python -m api.server       # offline, canned answers, no Gemini calls
```
Port 8766 (`--port` to change). Endpoints: `POST /v1/brake`, `POST /v1/detonate`, `GET /v1/health`. CORS open.

## Install the extension
1. `chrome://extensions` → turn on **Developer mode** → **Load unpacked** → pick this `extension/` folder.
2. Click the Click-Brake toolbar icon (opens Options): set the **current task**, the API URL (default
   `http://localhost:8766`), optionally **your own Gemini key**, and the detonation toggle. Save.
3. Browse. Every click is checked first.

Your key is stored in `chrome.storage.local` and sent only to the API URL you set, as the `X-Gemini-Key` header. The
API uses it for that one request and never logs it.

## Tests (offline, MOCK=1, no Gemini calls)
```
.venv/bin/python -m api.test_api
.venv/bin/python -m extension.test_extension      # HEADED=1 to watch
```
`test_extension` loads the extension into Playwright's own Chromium (headless works), clicks the injected "Verify
session" button on `app/fixtures/checkout_injected.html` (overlay shown, the button's handler did not run), then
"Place order" (goes through).

## Limitations (honest list)
- **Only the `click` event is braked.** A page that acts on `mousedown` / `pointerdown`, or a form submitted with Enter,
  is not held. Keyboard activation of a focused button does fire `click`, so that is held.
- **The re-dispatched click is synthetic** (`isTrusted = false`). Pages that ignore untrusted clicks will not react to
  an approved click; links and ordinary handlers do.
- **Mock routing guesses from the clicked label** (every word of the label in the task → PASS, else STOP). That is only
  for offline tests; the real brake looks at the screenshot with the click ringed.
- **BYO key is a process-wide env swap under a lock** (`brake.check()` takes no client argument and we may not edit
  `brake/`). All model calls on one API server are serialized; a 40–95 s detonation blocks brake calls meanwhile.
- The brake question describes a 1280x800 page; the API resizes other screenshots to 1280x800 and scales the click.
  Very different aspect ratios are squashed.
- Branded Google Chrome 137+ ignores `--load-extension`, so the automated test uses Playwright's Chromium. Load
  unpacked by hand in Chrome works as usual.
- **Not tested live**: no real Gemini call was made through the API or the extension (keys are quota-capped / reserved
  for the stage). The real path is `brake.check()` and `detonate()` unchanged, called with the same arguments the app uses.
