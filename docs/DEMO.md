# The demo, second by second

Written before building. We build exactly this, and anything not on this page waits.

> **DRAFT (12:37, lead's agent), pending the 13:29 lock.** Assumes Step Guard (cascade) is picked.
> Rows marked *[Done Gate]* depend on spike 7. If it fails, the judge presses "Check" instead.

**The one sentence a judge should repeat afterwards:** "It watched me do the task, told me in about a
second that I'd swapped the lids, and they showed it matches the slow frontier model's accuracy at a
tenth of the wait."

Named person: a line trainer onboarding a new assembler (the builder guide's "concrete person").

| Time | On screen | Who | Says | Criterion it scores |
|---|---|---|---|---|
| 0:00 | Phone camera over a table with 3 jars and 3 lids | Shivam | "A new assembler does a task. Did they do it right? Today you'd wait for a supervisor, or for a frontier model to watch the video for ~17 seconds." | Creativity (named problem) |
| 0:15 | Judge says the goal into the mic ("each lid on its own jar"); text goal appears | Judge | (their own words) | Live: unrehearsed input |
| 0:25 | Judge does it, **deliberately wrong** (swaps two lids) | Judge | | Live |
| 0:40 | *[Done Gate]* hands withdraw → "Checking…" appears by itself (else judge presses Check) | | | Gemini use (Decision 1 gate) |
| 0:42 | Verdict in ~1–2 s: **WRONG** + Decision 1's probability + confidence. If unsure: "Asking Neon…" → Neon's verdict and reason in ~17 s ("the red and blue lids are swapped") | Hydrogen speaks it | | Live; Gemini use (2 models, each a clear job) |
| 1:05 | Judge fixes it; verdict **RIGHT** in ~1 s | Judge | | Live |
| 1:20 | One slide: accuracy vs latency for Decision 1 alone / Neon alone / cascade on 40 held-out ego2act clips | Shivam | "0.925 balanced accuracy at 1.58 s typical, same as Neon alone, which takes 16.8 s. Decision 1 alone: 0.80." | Proof (baseline) |
| 1:50 | Slide: where it fails (sock_bucket, racket_table_floor, messy_desk_monitor) + the five designs we killed today | Dan | "Splitting the judgment into many small checks lost every time. Decision 1 only won as a gate in front of Neon." | Proof (honest failures) |
| 2:30 | Model roles diagram: Decision 1 gate → Neon agentic video when unsure → Hydrogen voice; Carbon (if used) | Dan | | Gemini use |
| 2:50 | "Try it yourself" | | | |

## The moment
The judge picks the task and does it wrong on purpose, and the system says what is wrong in about a second.

## If it breaks on stage
- Neon slow or timing out: show Decision 1's verdict with its confidence, and say "unsure, would escalate".
- Wi-Fi: a phone hotspot; a recorded run of the same flow in a second tab.
- Camera: upload a clip filmed 2 minutes earlier.

## Likely questions, with answers
| Question | Answer (with the number and where it comes from) |
|---|---|
| Why would anyone need this? | Checking physical work today means a person watching, or a frontier model taking ~17 s per clip (`results/s2_heldout.json`). |
| Why can't an existing tool do it? | One Neon call can, slowly: 0.925 at 16.8 s. Decision 1 alone is fast but 0.80. The cascade gets 0.925 at 1.58 s (same file). |
| Isn't the accuracy just a tie with Neon? | Yes, on accuracy; the gain is speed at equal accuracy, and fewer false "success" calls (1 vs 2 vs 4 of 20). On 40 clips that difference is small; we say so. |
| Where does it fail? | Decision 1 confidently wrong (sock_bucket); Neon wrong on cluttered scenes (racket_table_floor, messy_desk_monitor). 16 of 40 clips still wait for Neon. |
| How did you pick the thresholds? | 0.25 / 0.75 fixed on 20 clips (spike 1d), then frozen and tested on 40 unseen clips (spike 2). |
| What would you do with another week? | Per-site threshold fitting, robot clips (Dan's ArmnetBench: Decision 1 alone 0.875), step-by-step checks. |
