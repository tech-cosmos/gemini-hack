# Notes: insights, dead ends, limitations, odd behavior

Anyone appends, newest at the bottom: `HH:MM · who · what you learned`. The README's "limitations" and the
pitch's "what surprised us" are written from this file, so be specific and include the number.

## Dead ends (so nobody tries them twice)
12:08 · Dan's agent · Census (count distinct objects by listing per shard + Decision 1 "same object?" merges) loses to plain Hydrogen 5-vote: EM 0.30 vs 0.567 on 30 SVCBench questions. Decision 1 can't tell look-alike instances apart from crops: it never merges identical ceiling lights (0/109 pairs) yet merges different chairs (6 → 1). Hydrogen on the whole clip at low media resolution already counts well (MAE 0.8, about 4k tokens per minute of video).

## Findings
11:40 · Dan's agent · Decision 1 works on video only via `api_version="v1beta"` and model `models/gemini-decision-1` (v1 answers 404, and `models.list` doesn't show it). One 25 s 426x240 clip costs about 2k tokens, 0.8-1.9 s, with the same answer on repeat. On 39 real robot clips it has no success bias: every failure scored p ≤ 0.42, and its errors are successes scored too low (8 of 20 under 0.5 in one arm or the other). Thresholds need calibrating; adding more questions didn't help (0.80 vs 0.875). 1 of 40 clips was blocked by the content filter for no visible reason.

## Limitations

- 12:00 · Both people's agents run Claude Opus 5.5 (high). For "ask a different model" (fresh ideas, hostile judge) use Fable or Gemini 4, not Opus, so the second opinion isn't the same model twice. Ideas 10–17 and spike 3 came from Fable.

- 12:09 · **Models our keys can call** (from the key's own model list, v1beta): Gemini 4 Carbon/Neon/Hydrogen/Argon, `gemini-decision-1`; **video gen/edit** `gemini-omni-1.2-flash` (also 1.1, `gemini-omni-flash-preview`; up to 15 s with audio, image→video, extend, edit); **interactive worlds** `genie-4` (bidi, 24 fps); images `gemini-nano-banana-2.1`, `gemini-3-pro-image`; music `lyria-3.5`; live voice/video `gemini-3.8-live`; robotics `gemini-robotics-er-2-preview` (+ streaming); `gemini-2.5-computer-use-preview-10-2025`. No Veo. Anyone may use any of these; the lead says the event key has no spend limit (still estimate before a batch). A Fable agent is measuring Omni and Genie now; numbers land here.
