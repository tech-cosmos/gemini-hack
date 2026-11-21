# Evidence: every number we say comes from here

Format: `value · what it measures · the file it is in · the command that produced it`.
Never round, never retype, never from memory. If a number isn't on this page, it isn't in the README,
the slides or the talk.

## Final results
-

## Along the way (spikes, pilots, things that failed)
- **10 of 10 · 2.23 s** · frames where `gemini-robotics-er-2-preview` points on the named object (majority of 3 calls, judged by eye; 5 real ego2act frames + 5 generated) · p50 latency per call, 30 calls, max 3.6 s, 0 errors, `thinking_level` low. Pass mark was ≥ 8 and ≤ 2.5 s: **pass** · `results/s8_er_pointing.json` · `.venv/bin/python spikes/s8_er_pointing.py` then `... judge` (12:58)
- 2.32 s · one ER 2 trajectory call (docs prompt), 2 waypoints returned, n=1 · same file and command
- **15 of 20 · 0 of 20** · full clips / half-length prefixes where Decision 1 says "finished and stopped" at p ≥ 0.6 (threshold refit on spike 6b, then frozen), 20 held-out ego2act clips, tasks at ranks 50–59. Pass mark was ≥ 16 and ≤ 2: **fail** by one full clip. Median p 0.672 vs 0.2375 · `results/s7_donegate_heldout.json` · `.venv/bin/python spikes/s7_donegate_heldout.py` (12:38)
- 0.99 · 20 of 20 · AUROC of that p between full clips and half prefixes · full clips scoring above their own half, same run · same file
- 0.825 s / 1.91 s · Decision 1 p50 / max latency per call, 40 calls, 0 errors, same run · same file
- **0.8 · 0 of 10** · AUROC of the frozen Decision 1 goal question between Omni 1.2 RIGHT and WRONG generations (10 fresh ego2act tasks, 20 clips) · RIGHT clips at p ≥ 0.75. Pass mark was ≥ 0.85 and ≥ 7/10: **fail** · `results/s6_genjudge.json` · `.venv/bin/python spikes/s6_genjudge.py` (12:35)
- 26.8 s (max 30.1) · Omni 1.2 Flash image→video, 6 s 720p clip, wall time p50, n=20, 20/20 returned, no refusals · same file and command
- **11 of 20 · 0 of 20** · full clips / half-length prefixes where Decision 1 says "finished and stopped" at p ≥ 0.75 (20 spike 3 clips). Pass mark was ≥ 16 and ≤ 2: **fail**. Median p 0.784 vs 0.22; p50 0.735 s per call · `results/s6_donegate.json` · `.venv/bin/python spikes/s6_donegate.py` (12:35)
- **0.92 vs 0.24285714285714285** · overall F1 on added/removed/moved objects, one Neon agentic call with both videos vs Neon inventories + Decision 1 checks, 7 indoor SceneDiff pairs (25 gold objects; 12 chosen by rule, 5 lost to Neon timeouts); **spike killed, the system arm lost to the baseline** · `results/s4_beforeafter.json` · `.venv/bin/python -I spikes/s4_fetch.py && .venv/bin/python spikes/s4_beforeafter.py` (12:24)
- 0.5882352941176471 · same system arm after a Neon recheck of the 176 items with Decision 1 confidence < 0.75 (94 verdicts flipped) · same file
- 115 / 43 / 25 · changes predicted by system / system+recheck / baseline for 25 real ones (precision 0.14782608695652175 / 0.46511627906976744 / 0.92) · same file
- 69.02 s / 53.79 s / 245.23 s · p50 end-to-end latency per pair incl. upload, baseline / system / system+recheck (max 160.2 / 85.64 / 315.66 s), 4 pairs running at once · same file
- 0.855 s · Decision 1 p50 per call on a 5–15 s 360p clip with 5–80 yes/no questions (402 questions in 22 calls) · same file
- **3 of 10** · wrong clips the online Tripwire flagged before the clip ended (Decision 1 per 2 s prefix, flag at p ≥ 0.75), 20 held-out ego2act clips, tasks at ranks 30–39; **spike failed its pass mark of 8/10** · `results/s3_tripwire.json` · `.venv/bin/python spikes/s3_tripwire.py` (11:55)
- 0 of 10 · false alarms on the correct clips, same run · same file
- 2.042 s · median lead time before clip end over the 3 flagged wrong clips (leads 1.667, 8.542, 2.042) · same file
- 0.69 s / 1.28 s · Decision 1 p50 / max latency per tick, 160 ticks, 160 calls, 0 errors · same file
- 0.674 · highest p on any correct clip at any tick (book_miniature); 5 of the 7 missed wrong clips never exceed 0.582 · same file
- **0.925 at 1.58 s p50** · cascade balanced accuracy and latency on 40 **held-out** ego2act human clips (20 unseen tasks × correct/wrong), rule frozen before the run · `results/s2_heldout.json` · `.venv/bin/python spikes/s2_heldout.py 10 20` (11:42)
- 0.80 at 1.21 s · Decision 1 alone, same 40 clips · same file
- 0.925 at 16.8 s · Neon agentic alone, same 40 clips (max 47.9 s) · same file
- 1 / 2 / 4 · false "success" verdicts on the 20 wrong clips: cascade / Neon / Decision 1 · same file
- 16 of 40 · clips the cascade escalated to Neon · same file
- 0.875 · Witness spike arm A: balanced accuracy of one Decision 1 yes/no on 39 ArmnetBench front-camera robot clips (20 success / 19 failure) · `spikes/witness/result.json` · `uv run --no-project --with google-genai==3.6.1 --with pandas --with pyarrow python -I spikes/witness/spike.py`
- 0.80 · Witness spike arm B: balanced accuracy of Carbon's failure-first checks scored by Decision 1, same clips · same file · same command
- 0.95 / 0.932 · AUROC for arm A / arm B · same file · same command
- 0.0 · false-success rate in both arms (no failure scored above p 0.42) · `spikes/witness/per_clip.csv` · same command
- 0.567 · Census spike arm A: exact match of Hydrogen 5-vote (median) on 30 SVCBench O2-Unique questions, real indoor scans · `spikes/census/result.json` · `uv run --no-project --with google-genai==3.6.1 python -I spikes/census/spike.py`
- 0.30 · Census spike arm B: exact match of the shard swarm + Decision 1 pair merge, same questions · same file · same command
- 0.80 / 2.63 · mean absolute count error for arm A / arm B · same file · same command
- 1 of 40 · clips blocked by Decision 1's content filter (`prohibited_content`) · `spikes/witness/result.json` · same command 4.16 s · Gemini 4 Hydrogen p50 latency, one 1280×853 JPEG + one-sentence question, n=10 (max 10.41 s) · `results/s0_plumbing.json` · `.venv/bin/python spikes/s0_plumbing.py .context/spike/scones.jpg` (11:20)
- 0.56 s · Gemini Decision 1 p50 latency, same image at low resolution, 2 yes/no questions, n=5 · same file and command
- 4.12 s / 6.13 s · Gemini 4 Neon / Carbon, one short text reply · same file and command
- 3.92 s / 4.19 s · Hydrogen p50 on the spike 0 frame at thinking_level low / medium, n=10 each · `results/s0c_hydrogen_low.json` · `.venv/bin/python spikes/s0c_hydrogen_low.py .context/spike/scones.jpg` (11:27)
- 0.70 / 0.55 · balanced accuracy, Decision 1 one question vs Carbon's failure-first checks (AND at 0.5), 20 ego2act-bench human clips (10 correct, 10 wrong, 10 tasks) · `results/s1_ego2act.json` · `.venv/bin/python spikes/s1_ego2act.py 10` (11:30)
- 0.86 / 0.87 / 0.74 · AUROC of p_goal / min_check / mean_check on the same 20 clips · `results/s1_auroc.json` · `.venv/bin/python spikes/s1_auroc.py`
- 0.82 s · Decision 1 p50 latency per 10–25 s 480p clip at low res with 6–9 questions, n=20 · `results/s1_ego2act.json`
- 0.90 · balanced accuracy, Neon (`processing: agentic`) one YES/NO call, same 20 clips · `results/s1c_neon_agentic.json` · `.venv/bin/python spikes/s1c_neon_agentic.py` (11:33)
- 20.75 s · Neon agentic p50 latency per clip incl. upload (max 238.2 s), n=20 · same file
- 0.90 at 1.17 s p50 · cascade replay (Decision 1 when p ≤ 0.25 or ≥ 0.75, else Neon), 8/20 escalated, **not held out** · `results/s1d_cascade.json` · `.venv/bin/python spikes/s1d_cascade.py`
- 20.7 s · one Managed Agent run (remote sandbox, write + run a script, correct answer) · `results/s0b_managed_agent.json` · `.venv/bin/python spikes/s0b_managed_agent.py` (11:21)

## Cost
-
