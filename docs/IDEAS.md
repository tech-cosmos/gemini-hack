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
| 5 | **Witness** (5 Sigma) · Dan | A robot or a person says "done"; Witness checks it against the video. Carbon turns the instruction into 5–15 failure-first yes/no checks ("ring fully seated in the last second?"); Hydrogen picks key frames and crops; Decision 1 scores every check × camera × crop in one call → calibrated verdict + the frame that proves it. Eval: ArmnetBench v0.1, 3,118 real robot rollouts, 73% failures, HF `armnet/armnetbench_v01_*` Apache-2.0; balanced accuracy + AUROC vs one call "did it succeed?" and vs 5-vote. Motivation: FailBench (arXiv 2609.03611, Sep): best of 13 VLM detectors 0.77 balanced accuracy, <0.60 on assembly, biased toward "success". Live: a judge does any tabletop task on camera, succeeding or failing on purpose. | 4/5/4/5 | **4.45** | Decision 1 on video unproven (fallback: frames); may share the success bias; Managed Agents fit weak |
| 6 | **Census** (5 Sigma, swarm) · Dan | Count distinct things in a video. A Hydrogen swarm lists every instance per shard (crop + timestamp); Decision 1 asks "same physical object? [crop A] [crop B]" for up to 1,000 pairs per call to merge duplicates; Carbon settles borderline merges; count = clusters. Eval: SVCBench unique-count questions (406 videos, HF `buaaplay/SVCBench` CC-BY-4.0, GitHub Apache-2.0) + CountVideoBench (arXiv 2610.28356, Oct 20: "no model exceeds 27.6% Exact Match", humans 90.8%; HF CC-BY-4.0, GitHub MIT); Exact Match + MAE vs one call with 5-vote. Live: a judge films the room and checks the gallery of distinct instances by eye. | 4/4/5/5 | 4.40 | Identical-looking objects need position, not looks (CountVideoBench is built that way); the pair check is unproven |
| 7 | **Wire Trace** (5 Sigma) · Dan | Photo or scan of any node-and-arrow diagram (circuit, network, workflow) → an editable graph with every edge checked. Carbon lists nodes with boxes; Decision 1 asks "directed link A→B?" for every ordered pair in one call (32 nodes = 992 questions); Neon re-checks low-confidence pairs on zoomed crops. Eval: Knossos test split, 1,200 diagrams in 6 domains (arXiv 2610.04721, Oct 3; HF `WayneGuo0011/Knossos` CC-BY-4.0, repo MIT), Edge F1 with the repo's own scorer vs one call image→JSON. Paper: GPT-5.6 edge F1 81.1 avg, 76.8 on difficult, 61.9 on food webs. Live: a judge draws a flowchart on paper. | 4/5/3/4 | 4.05 | Knossos diagrams are rendered, not hand-drawn (a judge may call it image framing); Gemini not in the paper, so headroom unproven |
| 8 | **Who said it** (5 Sigma, swarm) · Dan | An hour of meeting audio → a transcript with the right speaker on every line. Shards of 2 min transcribed in parallel; Decision 1 answers "same speaker? [clip A] [clip B]" across shards to link voices; Carbon writes the final transcript. Eval: AMI Meeting Corpus (HF `edinburghcstr/ami` CC-BY-4.0), DER via pyannote.metrics vs one call over the whole meeting with 5-vote, and vs free pyannote. Live: three judges talk for 4 minutes and check who said what. | 4/4/3/4 | 3.80 | No fresh benchmark behind it; pyannote is a strong free baseline; voice matching by Decision 1 unproven |
| 9 | **Step Timeline** (5 Sigma) · Dan | A video of hands doing a task → a timed list of labelled steps. Hydrogen proposes windows; Decision 1 picks one of 29 skills (+ none) per window, 1,000 windows per call; Carbon writes step descriptions. Eval: RoboAtom-Bench, 500 trajectories (arXiv 2610.40207, Oct 29; HF `InternRobotics/RoboAtom` MIT): card shows Gemini 3.1 Pro 42.5 mIoU vs 56.4 for a tuned 27B. | 3/4/3/3 | 3.25 | Boundaries aren't a closed question, so Decision 1 may help labels more than mIoU |

**Dan's rescore of 1–4 (11:30):** Step Guard 4/3/5/5 = 4.15. Its eval of clips with injected mistakes that we record ourselves is the banned "team-written only" set. Fix: **ego2act-bench** (HF `ego2act/ego2act-bench`, CC-BY-4.0, released 2026-09-28) has first-person recordings labelled correct / wrong. With it, P goes back to 4 (4.40). Fixit 3/3/3/5 = 3.40: seeded bugs are team-written too. Real issues with screenshots fix that, but CUA-SWE (arXiv 2609.32600) and SWE-bench Multimodal data carry no licence. Sketch to app 4/3/2/4 = 3.35. Show and sell 4/2/3/4 = 3.30: weak fit for 5 Sigma.
**Checked and dropped (licence or fit):** FailBench data (not released yet), CUA-SWE and Chart2Code (no licence), Video-Index (`license:other`), World Models' Last Exam (no licence), LongCap (no data), receipt forgery (close to the rejected invoice-fraud idea).

## 3. The spike test
A spike is the cheapest run that could kill the idea: 15 to 20 minutes, one person and their agent.
- **Same protocol for every idea**, so the results compare: the same sizes, models and settings.
- **Use the final settings.** A result that changes when the limits change was never a result.
- **Write the pass mark before the run.** Example: "keep if the baseline fails at least half".
- **Enough repeats to not be noise.** Three samples can flip on a rewording; use ten before deciding.
- Report every spike, including the ones that failed. They become "what we tried" in the pitch.

| Idea | Who | Protocol | Pass mark (written first) | Result | Verdict |
|---|---|---|---|---|---|
| 0 · plumbing | first person with a key | Call two Gemini 4 models + Decision 1 from a script; time Hydrogen on one 720p frame, 10 calls | All three respond; Hydrogen p50 < 1.5 s | Neon 4.12 s, Carbon 6.13 s, Hydrogen on a 1280×853 frame p50 4.16 s (max 10.41 s, n=10), Decision 1 on the same frame at low res, 2 questions, p50 0.56 s (n=5) | **Fail on Hydrogen speed.** Generation per frame is too slow for a live loop; Decision 1 is fast enough. Live loops score frames with Decision 1 and call Hydrogen/Carbon only on events |
| 0b · Managed Agent | Shivam | One Managed Agent run (`antigravity-preview-09-2026`, remote sandbox): write and run a Fibonacci script, reply with the last number | Correct answer in < 3 min | 4181 (correct) in 20.7 s | **Pass.** A Managed Agent is cheap enough to use inside our flow (e.g. building the check list, running the eval), not only as a background job |
| 1 · Step Guard | | 10 phone frames of one LEGO step (5 right, 5 wrong piece) + the manual page; Hydrogen + Decision 1 judge each | ≥ 8/10 right, p50 < 2 s per frame | | |
| 2 · Fixit | | 1 tiny repo with a seeded bug + a 30 s narrated recording; one Managed Agent run, 3 times | Reproduces and fix passes its test in ≥ 2/3 runs, each < 5 min | | |
| 3 · Sketch to app | | 3 sketches by someone else; Managed Agent build + self-check | Checklist passes on ≥ 2/3, each < 5 min | | |
| 4 · Show and sell | | 5 objects on camera; listing created in a shop.dev dev store | ≥ 4/5 attributes right; store + API working in < 20 min | | |
| 5 · Witness (shared with 1) · **Dan spikes this** | Dan | 40 ArmnetBench robometer clips (20 success, 20 failure, weighted to `ring_insert`/`tool_insert`), same 2 arms: (a) one Decision 1 yes/no "did the task succeed?" per clip; (b) Carbon's 5–15 failure-first checks per task, all in one Decision 1 call per clip | Decision 1 accepts video (else frames, noted); (a) balanced acc ≤ 0.85 (room left) and (b) beats (a) by ≥ 0.05 balanced acc or halves false "success" | | n=39 (1 clip blocked by the content filter). A: one question, bal acc **0.875**, AUROC 0.95, false-success 0.0. B: failure-first checks, bal acc **0.80**, AUROC 0.932, false-success 0.0. Decision 1 takes video: median 1.0 s, about 1.7k tokens per clip. Errors are missed successes, not false successes (failures all p ≤ 0.42). `spikes/witness/result.json` | **KILL** as written: the baseline already scores over 0.85 and the checks did worse. Finding: Decision 1 on video has no success bias here. Its errors are threshold calibration, which helps 1 · Step Guard |
| 6 · Census | | 30 SVCBench unique-count questions; swarm + pair merge vs one call 5-vote; 100 hand-labelled crop pairs for the pair check | Swarm EM ≥ baseline + 10 points and pair-check AUROC ≥ 0.85 | | |
| 7 · Wire Trace | | 20 Knossos test diagrams (Food Web + Circuit); one call vs pairwise Decision 1 | Baseline edge F1 < 85 and pairwise beats it by ≥ 5 points | | |

## 4. The pattern
**11:21 (Shivam's agent):** Step Guard (1) and Witness (5) are the same engine: Carbon turns an instruction
into failure-first yes/no checks, Decision 1 scores frames against them. Spike 0 says the same engine is
the only fast one (Decision 1 0.56 s vs Hydrogen 4.16 s per frame). Witness brings a real benchmark for
Proof (ArmnetBench); Step Guard brings the live, judge-proof demo (a person assembling, a voice catching
the mistake). Merged, one build scores on all four criteria. Dan's Witness spike decides whether
Decision 1 holds up on real video.
After two rounds, look across the results for what they have in common. The surprise that explains
several results at once is usually the project.

## 5. Decision
Recorded in `DECISIONS.md` with the numbers that decided it.
