# Briefing

The lead's agent keeps "Now" current. Every agent reads it at the start of every session.

## Now
**14:50 · BUILD. Locked: Click-Brake (idea 36, problem statement One, 5 Sigma).** Decision 1 checks every click a computer-use agent proposes and stops clicks driven by injected page text; spike 16 PASS (AUROC 0.9968, p50 1.2425 s). Demo: `docs/DEMO.md`. Shared format `brake.check()` frozen (DECISIONS 14:46).
| Who | Piece | Done by |
|---|---|---|
| Shivam's agents | #21 `brake/` core + mock golden path, then the live app (`app/`) | golden 15:15, app 15:45 |
| Shivam's agent (Fable) | #22 spike 17: does a real computer-use agent fall for a typed injection? (decides DEMO 0:30) | 15:10 |
| Dan (rrrozhd) | #23 proof: VPI-Bench (public) + own set, Decision 1 vs Hydrogen, held-out, failure gallery | 15:42 |
| Dan (rrrozhd) | #24 Managed Agents: protected agent or task finisher (`managed/`), kill test first | 15:22 |
**Next gate:** 15:03 · DEMO.md written (done), golden path defined in `scripts/check` (done), shared formats frozen (done). Then 15:22 golden path green on main; 15:42 real results; 16:01 freeze.

## How to write "Now"
Keep it under 20 lines, newest state only; move the old one under "Earlier".

    **HH:MM · <phase>.** One sentence on where we are.
    | Who | Piece | Done by |
    |---|---|---|
    **Claim order for unowned issues:** #.., #.., #..
    **Next gate:** HH:MM · what must be true.
    **Budget:** cap, spent so far, what needs the lead's OK.

## Earlier
**12:50 · Still exploring; idea NOT locked (lead decides by ~14:30).** Lead: Step Guard works but "won't be impressive in itself". This round optimises for **wow first**, with credible proof.
**What today proved** (all in `docs/IDEAS.md` spike table, numbers in `docs/EVIDENCE.md`): one strong model call beats many small Decision 1 checks (Witness, Census, Before/After, Wire Trace smoke). Decision 1 wins only as a fast gate in front of Neon (Step Guard cascade: 0.925 at 1.58 s vs Neon 0.925 at 16.8 s). Omni-generated "correct" clips don't finish the task (6a fail). Done Gate ranks well (AUROC 0.99) but no fixed threshold passed (6b, 7).
| Who | Now | Due |
|---|---|---|
| Dan (rrrozhd) | Wire Trace spike, then 1–2 wow-first ideas (#10) | 13:10 |
| Shivam's agent (Fable + Gemini Carbon) | Round 3: wow-first ideas using Genie 4, Robotics-ER 2, Omni, live voice/video | 13:05 |
**Next gate:** 14:43 · idea picked (after the Click-Brake result, spike 16) and written in `docs/DECISIONS.md`. `docs/DEMO.md` holds a Step Guard draft as the fallback.
**Models on our key:** see `NOTES.md` (Genie 4, Omni 1.2, Robotics-ER 2, computer-use, Live, Lyria, Nano Banana).

