# Briefing

The lead's agent keeps "Now" current. Every agent reads it at the start of every session.

## Now
**12:50 · Still exploring; idea NOT locked (lead decides by 14:00).** Lead: Step Guard works but "won't be impressive in itself". This round optimises for **wow first**, with credible proof.
**What today proved** (all in `docs/IDEAS.md` spike table, numbers in `docs/EVIDENCE.md`): one strong model call beats many small Decision 1 checks (Witness, Census, Before/After, Wire Trace smoke). Decision 1 wins only as a fast gate in front of Neon (Step Guard cascade: 0.925 at 1.58 s vs Neon 0.925 at 16.8 s). Omni-generated "correct" clips don't finish the task (6a fail). Done Gate ranks well (AUROC 0.99) but no fixed threshold passed (6b, 7).
| Who | Now | Due |
|---|---|---|
| Dan (rrrozhd) | Wire Trace spike, then 1–2 wow-first ideas (#10) | 13:10 |
| Shivam's agent (Fable + Gemini Carbon) | Round 3: wow-first ideas using Genie 4, Robotics-ER 2, Omni, live voice/video | 13:05 |
**Next gate:** 14:00 · idea picked and written in `docs/DECISIONS.md`. `docs/DEMO.md` holds a Step Guard draft as the fallback.
**Models on our key:** see `NOTES.md` (Genie 4, Omni 1.2, Robotics-ER 2, computer-use, Live, Lyria, Nano Banana).

## How to write "Now"
Keep it under 20 lines, newest state only; move the old one under "Earlier".

    **HH:MM · <phase>.** One sentence on where we are.
    | Who | Piece | Done by |
    |---|---|---|
    **Claim order for unowned issues:** #.., #.., #..
    **Next gate:** HH:MM · what must be true.
    **Budget:** cap, spent so far, what needs the lead's OK.

## Earlier
