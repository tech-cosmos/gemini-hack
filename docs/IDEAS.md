# Ideas, and the spike test that picks one

We pick by evidence, not by who argues best, and we never lock the first idea.

## 1. Criteria (from the judging rubric in BRIEF.md)
| Criterion | Weight | What a 5 looks like |
|---|---|---|
| L · Live Demo | 35% | A judge hands us an input we've never seen (their object, their drawing, their bug) and it works in seconds |
| P · Proof It Works | 25% | An eval on inputs someone else made, a baseline number beside ours, and a "where it fails" slide |
| C · Creativity | 20% | A problem other teams avoid; the camera, voice or video does something text could not |
| G · Gemini 4 + Decisions API | 20% | 2+ Gemini 4 models each with an obvious job, Decision 1 on the hot path, pushed on speed or multimodality |

Also weigh, outside the score: **Managed Agents prize ($5k)**, **Shopify prize**, and the banned list in
BRIEF.md (no image analyzers, dashboards, sports, health, education chatbots). Their own example (messy
forms) is the one half the room will build: avoid it.

## 2. Shortlist
Everyone adds one or two. Score each 1 to 5 per criterion; the weighted total only decides what gets spiked.
Total = 0.35·L + 0.25·P + 0.2·C + 0.2·G. Shivam's agent's first pass, 10:58; Dan adds his and rescores.

| # | Idea | One line | Scores L/P/C/G | Total | Risk |
|---|---|---|---|---|---|
| 1 | **Step Guard** (Element 119) | Phone camera on your hands while you assemble something (LEGO, flat-pack, a breadboard). Carbon reads the instruction PDF once and turns it into steps with visual checks; Hydrogen watches the live stream; Decision 1 scores each step "done right / wrong piece / skipped" and a voice says "stop, that's the 2×4, step 7 needs the 2×2". Eval: clips with injected mistakes, detection rate and false alarms vs one-call baseline (frame + whole manual). | 4/4/5/5 | **4.40** | Real-time latency on venue Wi-Fi; needs a physical kit (buying one is the lead's call); no natural Managed Agents fit |
| 2 | **Fixit from a screen recording** (5 Sigma) | Record a bug with your voice ("I click save and nothing happens"). Neon turns the video into repro steps; a **Managed Agent** in its sandbox clones the repo, reproduces it with Playwright, writes a failing test, patches, reruns; Decision 1 gates "reproduced?" and "fix verified?". Eval: 20+ seeded bugs in 2–3 small open-source apps, recorded by the other person, vs baseline single call (video → patch). | 3/5/3/5 | 3.90 | A sandbox run may take minutes (live demo shows the start, then a finished run); preparing seeded bugs takes time. Strong Managed Agents fit |
| 3 | **Sketch to app, self-checked** (5 Sigma) | Photo of a whiteboard sketch + spoken narration. A **Managed Agent** builds the app, screenshots it, Carbon checks the screenshot against a checklist made from the sketch and loops until it passes. Eval: 30 sketches drawn by other people, checklist pass rate vs single-shot baseline. | 4/4/2/4 | 3.60 | Crowded idea (many teams do sketch-to-app); creativity low |
| 4 | **Show and sell** (Element 119 + Shopify) | Hold things up to the camera and talk about them; the agent creates real Shopify listings (cleaned photo, attributes, description, price from comparables), then a shopping agent sells them by voice. Eval: attribute accuracy on objects we've never seen vs one-call baseline. | 4/3/3/4 | 3.55 | Dev store setup time; "image analyzer" ban if it doesn't act; stacks the Shopify prize |

## 3. The spike test
A spike is the cheapest run that could kill the idea: 15 to 20 minutes, one person and their agent.
- **Same protocol for every idea**, so the results compare: the same sizes, models and settings.
- **Use the final settings.** A result that changes when the limits change was never a result.
- **Write the pass mark before the run.** Example: "keep if the baseline fails at least half".
- **Enough repeats to not be noise.** Three samples can flip on a rewording; use ten before deciding.
- Report every spike, including the ones that failed. They become "what we tried" in the pitch.

| Idea | Who | Protocol | Pass mark (written first) | Result | Verdict |
|---|---|---|---|---|---|
| 0 · plumbing | first person with a key | Call two Gemini 4 models + Decision 1 from a script; time Hydrogen on one 720p frame, 10 calls | All three respond; Hydrogen p50 < 1.5 s | | |
| 1 · Step Guard | | 10 phone frames of one LEGO step (5 right, 5 wrong piece) + the manual page; Hydrogen + Decision 1 judge each | ≥ 8/10 right, p50 < 2 s per frame | | |
| 2 · Fixit | | 1 tiny repo with a seeded bug + a 30 s narrated recording; one Managed Agent run, 3 times | Reproduces and fix passes its test in ≥ 2/3 runs, each < 5 min | | |
| 3 · Sketch to app | | 3 sketches by someone else; Managed Agent build + self-check | Checklist passes on ≥ 2/3, each < 5 min | | |
| 4 · Show and sell | | 5 objects on camera; listing created in a shop.dev dev store | ≥ 4/5 attributes right; store + API working in < 20 min | | |

## 4. The pattern
After two rounds, look across the results for what they have in common. The surprise that explains
several results at once is usually the project.

## 5. Decision
Recorded in `DECISIONS.md` with the numbers that decided it.
