# Evidence: every number we say comes from here

Format: `value · what it measures · the file it is in · the command that produced it`.
Never round, never retype, never from memory. If a number isn't on this page, it isn't in the README,
the slides or the talk.

## Final results
-

## Along the way (spikes, pilots, things that failed)
- 0/6 · venue-scale Genie Scout reach rate for Decision 1, Hydrogen and random (goal ≥ ~5 m, 60 s) · `.context/genie_scout_venue/results_run.json` (2nd session; out of repo) (13:31)
- 0.76 · AUROC, Decision 1 "same spot?" on 30 near vs 30 far real venue frame pairs · `.context/genie_faithful/part1.json` (2nd session; out of repo) (13:31)
- **5 of 10 · 2 of 10 · 6 of 10** · spike 13 Dream vs Twin, registered run: Genie 4 / Nano Banana turned views judged "same part of the same room" as the splat truth by one Neon call each; shuffled sanity pairs judged "different". Pass mark was sanity 10/10: **fail** (sanity pairs overlap; judge grades framing) · `results/s11_dreamtwin.json` · `uv run --no-project --with google-genai==3.6.1 --with playwright python spikes/s11_dreamtwin.py .context/room.splat room`
- 8/10 · spike 12b: Neon picks a grid view within 1 step and 45° of a phone-like query render (Mip-NeRF 360 room splat, 10 seeded poses); heading error p50 9.3° · `results/s10b_locate.json` · `uv run --no-project --with google-genai==3.6.1 --with playwright --with pillow python -I spikes/s10_roomsearch/locate.py .context/room.splat run --targets "the piano=v0_135,the potted plant=v2_270,the window=v2_225"` (renderer served with local copies of three 0.180.0 / spark 2.4.0 from `.context/vendor`)
- 50.08 s p50 (max 57.8) · spike 12b Neon locate call, 40 images + query, 10 at once · same file · same command
- 3/3 right image, 1/3 right turn side · spike 12b flat-photo baseline (Hydrogen, 40 renders as a list) · `results/s10b_locate.json`, `results/s10b_eye.json` (by eye) · same command
- 9/10, 18.03 s p50 · spike 12b **after the fact, not registered**: same locate with the 40 views as one labelled contact sheet; one solo 40-image call 22.38 s · `results/s10b_probe.json` · `uv run --no-project --with google-genai==3.6.1 --with pillow python -I spikes/s10_roomsearch/locate_probe.py`
- 8/10, 31.65 s p50 · spike 12c: Hydrogen instead of Neon, same 40-image locate prompt, 10 at once · `results/s10b_hydrogen.json` · `uv run --no-project --with google-genai==3.6.1 --with pillow python -I spikes/s10_roomsearch/locate_probe.py hydrogen`
- 9/10, 10.395 s p50 (max 27.82) · spike 12c arm (b), not the marked arm: Hydrogen with the 40 views as one labelled contact sheet, 2 at a time · same file · same command
- **5 of 10 · 2 of 10 · 6 of 10** · spike 13 Dream vs Twin, registered run: Genie 4 / Nano Banana turned views judged "same part of the same room" as the splat truth by one Neon call each; shuffled sanity pairs judged "different". Pass mark was sanity 10/10: **fail** (sanity pairs overlap; judge grades framing). Not a Genie win: most Genie after-frames were un-turned (0–14 frames during the hold), so its 5/10 mostly means Genie did not move · `results/s11_dreamtwin.json` · `uv run --no-project --with google-genai==3.6.1 --with playwright python spikes/s11_dreamtwin.py .context/room.splat room`
- 10 of 10 · 10 of 10 · positive control (truth vs splat +5°) judged "same"; seed hold (start render vs Genie first frame) judged "same"; added after the pass mark · same file
- 4, 9, 14, 1, 0, 0, 1, 1, 5, 4 · Genie frames received during the 2 s `arrow_left` hold, 4 sessions at once (calibration session 25); calibrated angle 15° · same file
- **1 of 10 · 0 of 10 · 5 of 10** · same, v2 after the fact (hold until 48 frames, one session at a time, calibrated angle 30°); controls 10/10 and 10/10 · `results/s11_dreamtwin_room_v2.json` · `S11_HOLD_FRAMES=48 uv run ... spikes/s11_dreamtwin.py .context/room.splat room_v2`
- 20.0 s / 127.7 s · venue place index on a 132 s walkthrough: Hydrogen static sampling vs Neon agentic, both placed stage/restrooms/snacks within 5 s of the key (Hydrogen snacks +2 s, Neon −2 s) · `.context/venue_index/results.json` (Shivam's 2nd session; kept out of the repo, venue footage) (13:35)
- **3 of 3 · 10.95 s** · spike 12 plumbing (not the pass mark): public Mip-NeRF 360 room splat, objects ER 2 pointed on by eye / query p50 (Decision 1 over 40 headless renders + one ER call; Decision 1 fan-out 5.29–14.28 s, ER 3.07–4.76 s; load 4.54 s, 40 renders 8.46 s) · `results/s10_roomsearch_plumb_room.json` · `uv run --no-project --with google-genai==3.6.1 --with playwright python -I spikes/s10_roomsearch/spike.py room.splat plumb_room "the piano" "the potted plant" "the window"` (13:30)
- 19.45 s · same with 40 parallel workers instead of 20 (single Decision 1 calls 11–14 s under load) · `results/s10_roomsearch_plumb_room_w40.json` · `S10_WORKERS=40` same command (13:35)
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
- 0/5 by eye (auto 1/5) · spike 9 registered run: Genie 4 closed loop, target recognisable and larger after the approach, turn key held per tick; 1 session errored · `results/s9_genie_loop.json` · `.venv/bin/python spikes/s9_genie_loop.py` (12:54)
- 0.791 s p50 (max 3.042), 51 ticks · Decision 1 `choice` per Genie frame, registered run · `results/s9_genie_loop.json` · same command (12:54)
- 1/5 · target still visible after look away 3 s and back, registered run (by eye; auto 1/5) · `results/s9_genie_loop.json` · same command (12:54)
- 4/5 by eye (3 clear, 1 marginal; auto 4/5), **after the fact, not registered** · same loop with turn keys tapped 0.15 s, same 5 seeds, one run; tick p50 0.786 s (max 1.263), 65 ticks; look-back 2/5 by eye (auto 3/5) · `results/s9_genie_loop_v2.json` · `S9_PULSE=0.15 .venv/bin/python spikes/s9_genie_loop.py` (12:56)
- 3.45–4.5 s to first frame, 8.0–23.9 fps received · Genie 4 image-seeded, 5 sessions at once, both runs (9 sessions with frames) · `results/s9_genie_loop.json`, `results/s9_genie_loop_v2.json` · same commands
- 4/6 auto, **0/6 by eye** · spike 10 registered run: Dream Run held out, 6 fresh ego2act seeds, spike 9 v2 controller, success = ER 2 point in the central 40% and Decision 1 noul "visible and large" ≥ 0.75; the camera barely moved (Genie sent 0.5–3.7 fps), the auto-successes were already central in the seed · `results/s10_dreamrun_heldout.json` · `.venv/bin/python spikes/s10_dreamrun_heldout.py` (13:25)
- 1.554 s p50 (max 4.273), 37 ticks · Decision 1 `choice` per Genie frame, spike 10 registered run; pass mark was ≤ 1.2 s: **fail** · `results/s10_dreamrun_heldout.json` · same command (13:25)
- 1/6 · seeds that reached "arrived" on 2 consecutive ticks within 15 s (3.98 s, no camera motion); 6/6 target visible after look-back (auto and eye, view never left); 0 crashes, 0 retries, 3 sessions at once · `results/s10_dreamrun_heldout.json` · same command (13:25)
- 2/6 auto, 0/6 by eye, tick p50 1.759 s, **after the fact, not registered** · one repeat of spike 10; 3 sessions at 14.5–19.3 fps moved without approaching, 3 stayed near 1 fps; look-back auto 5/6 · `results/s10_dreamrun_heldout_rerun.json` · `S10_TAG=_rerun .venv/bin/python spikes/s10_dreamrun_heldout.py` (13:27)

## Cost
-
- 88.3 · Wire Trace spike arm A: mean edge F1 of Neon one call (image + node names → JSON edges) on 20 Knossos difficult diagrams (10 food webs 76.6, 10 circuits 100.0) · `spikes/wiretrace/result.json` · `set -a; . ./.env; set +a; uv run --no-project --with google-genai==3.6.1 --with pandas --with pyarrow python -I spikes/wiretrace/spike.py`
- 64.3 · Wire Trace spike arm B: mean edge F1 of Decision 1 pairwise yes/no (p > 0.5), same diagrams (food webs 44.5, circuits 84.0) · same file · same command
