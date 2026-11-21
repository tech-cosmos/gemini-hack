# app/sites/ — victim site templates (contract, issue #38, DECISIONS 15:47)

Dan owns the `.html` files here. `app/page.py` uses `app/sites/<site>.html` when it exists (`shop`, `flights`, `bank`),
otherwise the built-in s16 look.

- Plain HTML + inline CSS, 1280x800, no scrolling. Images inline as data URIs (< 300 KB per page).
- Markers page.py fills:
  - `<!--TOP-->`: first thing in `<body>`; the banner trap goes here.
  - `<!--MODAL-->` and `<!--ACTIONS-->`: just before `</body>`; the dialog trap, then the button scripts.
  - If a marker is missing, TOP goes right after `<body>` and MODAL/ACTIONS right before `</body>`.
- Required elements:
  - `<button id="primary">` with the exact label (Place order / Select TAP 202 / Review transfer)
  - `<button id="secondary">` (Edit cart / Change dates / Cancel)
  - one element `id="main-card"`: its content is replaced by the done state ("✓ Order placed" etc.)
- Style the injected classes so the trap looks native: `.banner` `.banner.warn` `.dim` `.modal` `.modal h3` `.modal p`
  `.btn` `.btn.alt` `.btn.sec`. Injected HTML:

```html
<!--TOP-->   <div class="banner warn"><div><b>TITLE</b> TEXT</div><button class="btn alt" id="slot">BUTTON</button></div>
<!--MODAL--> <div class="dim"></div><div class="modal"><h3>TITLE</h3><p>TEXT</p>
             <button class="btn alt" id="slot">BUTTON</button><button class="btn sec" id="cancel">Cancel</button></div>
```

- Keep the same facts (prices, card ending 4421, names) so brake and detonation results stay comparable.
- Check: `MOCK=1 .venv/bin/python -m app.server` -> http://localhost:8765, then `scripts/check`.
