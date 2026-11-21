# Evidence: every number we say comes from here

Format: `value · what it measures · the file it is in · the command that produced it`.
Never round, never retype, never from memory. If a number isn't on this page, it isn't in the README,
the slides or the talk.

## Final results
-

## Along the way (spikes, pilots, things that failed)
- 4.16 s · Gemini 4 Hydrogen p50 latency, one 1280×853 JPEG + one-sentence question, n=10 (max 10.41 s) · `results/s0_plumbing.json` · `.venv/bin/python spikes/s0_plumbing.py .context/spike/scones.jpg` (11:33)
- 0.56 s · Gemini Decision 1 p50 latency, same image at low resolution, 2 yes/no questions, n=5 · same file and command
- 4.12 s / 6.13 s · Gemini 4 Neon / Carbon, one short text reply · same file and command
- 20.7 s · one Managed Agent run (remote sandbox, write + run a script, correct answer) · `results/s0b_managed_agent.json` · `.venv/bin/python spikes/s0b_managed_agent.py` (11:36)

## Cost
-
