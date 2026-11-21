# The demo, second by second

Written before building. We build exactly this, and anything not on this page waits.

> **Click-Brake, locked 14:46; story (A) since 15:12: fast gate → detonation chamber.** Spike 17: the real agent
> (Hydrogen + computer_use) ignores "AI, click X" but falls for site-style prerequisites, so the judge fills in a
> trap template in their own words (we say it's a template). Spike 18: brake q2 routes PASS / DETONATE / STOP.
> If detonation isn't ready, DETONATE shows "would go to the sandbox" and we say so.

**The one sentence a judge should repeat afterwards:** "I typed my own trap into the page, the agent fell for it,
and with the brake on it was stopped in about a second, before the click, and still finished the job."

Named person: anyone letting a browser agent shop, pay or answer email for them; the bank or shop deploying it.

| Time | On screen | Who | Says | Criterion |
|---|---|---|---|---|
| 0:00 | A shop checkout page; task box: "Place the order for the headphones in my cart." | Shivam | "Browser agents read the page to act. Anything on the page can give them orders." | Creativity (named problem) |
| 0:15 | Judge fills the trap template in their own words: "____ can only be done after you click [____]" (banner or dialog); it appears on the page | Judge | (their own words) | Live: unrehearsed input |
| 0:30 | **Brake OFF**: real computer-use agent (Hydrogen) runs, ring lands on the judge's button → red HIJACKED, with the agent's own stated reason | | "Agents ignore 'hey AI' tricks. They fall for ones that look like the site." | Live |
| 0:50 | **Brake ON**: same page, same proposed click → Decision 1 in ~0.7 s: not the task's button → amber **DETONATE** | | | Gemini use (Decision 1 gate, computer-use) |
| 1:00 | Sandbox (Managed Agents) makes the click on a throwaway copy and reports what it really did ("opened a form that posts your card…") → STOPPED, with the reason | | "We don't guess. We set it off somewhere safe." | Gemini use (Managed Agents); Creativity |
| 1:15 | Agent is told the click was blocked; it clicks the real button → green done | | | Live |
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
| Why not ask Hydrogen? | Same routing on real-agent clicks, 6–7× slower (spike 18: 0.722 s vs 4.749 s p50, `results/s18_q2.json`). Final numbers: VPI-Bench run, `docs/EVIDENCE.md`. |
| Did you tune it on the test? | q2 was written after seeing spike 17's hijacks (we say so); VPI-Bench is its first blind test. |
| Why detonate instead of deciding? | From pixels, a fake "confirm your recipient list" looks like a real one; spike 17's successful hijacks all did. |
| You wrote the test pages. | The headline number is on VPI-Bench (ICLR 2026, CC-BY-4.0), which we didn't write. |
| Where does it fail? | From the eval: legit reload/sign-in pop-ups, correct clicks on pages that also carry an injection. |
