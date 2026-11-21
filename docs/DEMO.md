# The demo, second by second

Written before building. We build exactly this, and anything not on this page waits.

> **Click-Brake, locked 14:46.** Rows marked *[17]* depend on spike 17 (a real computer-use agent falls for a
> typed injection). If it doesn't, the "unprotected" run replays a recorded hijack from our own set and we say so.

**The one sentence a judge should repeat afterwards:** "I typed my own trap into the page, the agent fell for it,
and with the brake on it was stopped in about a second, before the click, and still finished the job."

Named person: anyone letting a browser agent shop, pay or answer email for them; the bank or shop deploying it.

| Time | On screen | Who | Says | Criterion |
|---|---|---|---|---|
| 0:00 | A shop checkout page; task box: "Place the order for the headphones in my cart." | Shivam | "Browser agents read the page to act. Anything on the page can give them orders." | Creativity (named problem) |
| 0:15 | Judge types their own banner text into the "attacker" box; it appears on the page | Judge | (their own words) | Live: unrehearsed input |
| 0:30 | *[17]* **Brake OFF**: agent runs, ring lands on the judge's banner button → red HIJACKED | | "That's what happens today." | Live |
| 0:50 | **Brake ON**: same page; agent proposes the same click → STOPPED in ~1.2 s, p = 0.9x, Carbon's one-line reason; ER 2 circles "Place order" | | | Gemini use (Decision 1 gate, computer-use, ER 2, Carbon) |
| 1:10 | Agent clicks the right button; order placed (Managed Agents finishes the task) | | | Gemini use (Managed Agents) |
| 1:25 | Judge tries a legit pop-up (cookie / confirm) → brake lets it through | Judge | | Live; Proof (no false stop) |
| 1:45 | Slide: VPI-Bench (public, not ours) + our set: Decision 1 vs Hydrogen, AUROC, false stops, latency | Dan | numbers from `docs/EVIDENCE.md` only | Proof (baseline, inputs we didn't write) |
| 2:15 | Slide: where it fails (reload / sign-in pop-ups stopped, clicks near an injection) and what we changed | Dan | | Proof (honest failures) |
| 2:40 | Model roles diagram | Dan | | Gemini use |
| 2:55 | "Try your own trap" | | | |

## The moment
The judge writes the attack, watches the agent fall for it, then watches the brake stop the same click.

## If it breaks on stage
- Computer-use agent slow or flaky: replay its recorded proposed click; the brake call stays live.
- Decision 1 slow under load: show the latency honestly; fall back to cached run in a second tab.
- Wi-Fi: phone hotspot; recorded run of the same flow.

## Likely questions, with answers
| Question | Answer (number and source) |
|---|---|
| Isn't this just a classifier? | It's a gate on the action, not the page: same page, right click passes, injected click stops (spike 16 "injection ignored" cases; `results/s16_clickbrake.json`). |
| Why not ask Hydrogen? | Hydrogen ranks as well but takes ~3× longer per click (spike 16: 3.716 s vs 1.2425 s p50). Final numbers: VPI-Bench run, `docs/EVIDENCE.md`. |
| You wrote the test pages. | The headline number is on VPI-Bench (ICLR 2026, CC-BY-4.0), which we didn't write. |
| Where does it fail? | From the eval: legit reload/sign-in pop-ups, correct clicks on pages that also carry an injection. |
