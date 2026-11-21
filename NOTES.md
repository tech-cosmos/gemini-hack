# Notes: insights, dead ends, limitations, odd behavior

Anyone appends, newest at the bottom: `HH:MM · who · what you learned`. The README's "limitations" and the
pitch's "what surprised us" are written from this file, so be specific and include the number.

## Dead ends (so nobody tries them twice)

## Findings
11:40 · Dan's agent · Decision 1 works on video only via `api_version="v1beta"` and model `models/gemini-decision-1` (v1 answers 404, and `models.list` doesn't show it). One 25 s 426x240 clip costs about 2k tokens, 0.8-1.9 s, with the same answer on repeat. On 39 real robot clips it has no success bias: every failure scored p ≤ 0.42, and its errors are successes scored too low (8 of 20 under 0.5 in one arm or the other). Thresholds need calibrating; adding more questions didn't help (0.80 vs 0.875). 1 of 40 clips was blocked by the content filter for no visible reason.

## Limitations
