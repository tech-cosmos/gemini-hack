# Evidence: every number we say comes from here

Format: `value · what it measures · the file it is in · the command that produced it`.
Never round, never retype, never from memory. If a number isn't on this page, it isn't in the README,
the slides or the talk.

## Final results
-

## Along the way (spikes, pilots, things that failed)
- 0.875 · Witness spike arm A: balanced accuracy of one Decision 1 yes/no on 39 ArmnetBench front-camera robot clips (20 success / 19 failure) · `spikes/witness/result.json` · `uv run --no-project --with google-genai==3.6.1 --with pandas --with pyarrow python -I spikes/witness/spike.py`
- 0.80 · Witness spike arm B: balanced accuracy of Carbon's failure-first checks scored by Decision 1, same clips · same file · same command
- 0.95 / 0.932 · AUROC for arm A / arm B · same file · same command
- 0.0 · false-success rate in both arms (no failure scored above p 0.42) · `spikes/witness/per_clip.csv` · same command
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
