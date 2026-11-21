# Briefing

The lead's agent keeps "Now" current. Every agent reads it at the start of every session.

## Now
**11:56 · Still exploring; idea NOT locked (lead decides by 12:58).** Every spike result is in `docs/IDEAS.md` (spike table) and `docs/EVIDENCE.md`.
**Strongest so far:** Step Guard cascade (Decision 1 → Neon agentic when unsure): 0.925 bal acc at p50 1.58 s on 40 held-out ego2act clips (Neon alone 0.925 at 16.8 s, Decision 1 alone 0.80). Dan's Witness spike: Decision 1 alone 0.875 on robot clips.
**Being explored now:**
| Who | Spike | Status |
|---|---|---|
| Dan (rrrozhd) | Census (#6): count distinct objects in video, SVCBench | running (#8), result by 12:30 |
| Shivam's agent (Fable) | Tripwire (#10): catch a mistake while it happens | **failed**: 3/10 caught early, 0/10 false alarms, 0.69 s/tick |
| Shivam's agent (Fable) | licence check for Fable's ideas 10–17 + datasets with timestamped mistakes | running |
**New ideas 10–17** came from a different model (Fable), with a hostile-judge read on Step Guard: see IDEAS.md.
**Next gate:** 12:58 · idea picked and written in `docs/DECISIONS.md`.
**Budget:** organizer Gemini keys only.

## How to write "Now"
Keep it under 20 lines, newest state only; move the old one under "Earlier".

    **HH:MM · <phase>.** One sentence on where we are.
    | Who | Piece | Done by |
    |---|---|---|
    **Claim order for unowned issues:** #.., #.., #..
    **Next gate:** HH:MM · what must be true.
    **Budget:** cap, spent so far, what needs the lead's OK.

## Earlier
