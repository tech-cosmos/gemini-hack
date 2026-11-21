# Fresh ideas: a world model of the venue, with agents doing real tasks in it

Dan's agent, 13:05. Wow first, then proof. Does not repeat ideas 1–29: how each one differs is written on the idea.

## What we measured first (informal probe, no pass mark set beforehand)
- **Genie 4 takes only one photo.** `world_setup` with `reference_images` (a list of 3) returns
  `parameter_unknown: Unknown parameter 'reference_images'`. With one `reference_image` it works: first frame
  5.34 s, 152 frames in 18.44 s (6 s holding `arrow_left`). So you can't build a whole-venue Genie world from
  several photos. Anything outside the seed photo is generated, not remembered. (This matters to the lead's Scout spike too.)
- We have **not** shown that Genie drifts from the real room. The clip we compared against shows a later
  moment, not the true view to the left. Probe script and frames live outside the repo, in the session scratchpad.
- So the rule for every idea below: **if the agent's task depends on the world being true beyond what we
  captured, proof stays at 1–2 until we measure it.** Dan's fix: build the venue model as a **Gaussian
  splat from our own photos**. A splat is geometrically true wherever we captured it, and that is what makes the agent's answers checkable.

## Real tasks an agent could do in a venue model
| Task | Who needs it | Needs the model to be true beyond the capture? |
|---|---|---|
| "Where is X, and how do I get there?" (outlet, extinguisher, coffee, registration) | newcomer, low-vision visitor, event staff | No, if X was captured. **Splat: yes. Genie: no.** |
| Errand rehearsal: plan a route before a robot or person moves | delivery robot, runner | Splat: only along captured paths |
| "What changed since the capture?" (bag left, door open) | security walk | No. But Before/After lost to one Neon call (spike 4) |
| Imagine the unseen ("what's behind that door?") | none credible | **Yes, so it can't be proven. Drop** |

## Idea A · Room Search (splat of the venue, outsiders ask the questions) · **top pick**
**Pitch:** "Ask where anything in this room is. Gemini searches a photoreal 3D copy of the venue we scanned
this morning, flies you there, then tells you how many steps to take."
**The 20-second clip a judge films:** a judge asks out loud "where's the nearest power outlet?" On screen the camera
flies through a 3D copy of *this* room, stops, and a red Robotics-ER 2 dot lands on the outlet. A voice says
"turn around, about 6 steps, under the window." The judge turns, and it's there.
**How:**
1. Capture: someone on the team walks the venue with a phone splat app (free on-device options I know of:
   Scaniverse, Polycam, Luma. Not checked today; `search-first` before choosing) and exports `.ply`/`.spz`.
2. Render: a web splat viewer (three.js-based, for example Spark or mkkellogg GaussianSplats3D; not checked yet),
   driven headless by Playwright, renders about 100 views on a grid of positions and headings.
3. Search: **Decision 1 is the fast gate** ("is <X> visible?", all renders, the pattern that won in spike 2).
   The top 5 views go to **Robotics-ER 2**, which points at X. A ray through that point to the splat surface gives X's 3D position.
4. Find the judge: one **Neon** call matches the judge's live photo to the nearest render (Neon, not Decision 1,
   because Census showed Decision 1 can't tell look-alike things apart). **Carbon/Neon** turns the two positions
   into directions; Hydrogen or TTS speaks them.
**Models:** Decision 1 (gate), Robotics-ER 2 (pointing), Neon (localising the judge + directions), Hydrogen (voice). Two Gemini 4 models, each with its own job.
**Eval on inputs we didn't write:** 30 questions from **other hackers** ("name something in this room"),
collected at 13:45–14:30 on a form, with no filtering. Score: (a) found, meaning the final render contains X and the point
lands on it, judged by the person who asked; (b) walked, meaning a teammate who follows the spoken directions reaches X within 2 m.
Public offline set, if the lead wants a benchmark: object-goal questions on public splat or scan scenes
(Mip-NeRF 360 or ScanNet++). **Licences not verified**: ScanNet++ has non-commercial terms, and the Mip-NeRF 360 terms need checking.
**Baseline:** Hydrogen given the same capture photos as a flat list (no 3D): "which photo shows X, and
how do I get there from photo k?" Second baseline: Decision 1 on the raw photos without the splat.
**Spike (pass mark written before any run):** capture one corner (about 5 m), render 40 views, 3 objects named by someone outside
the team. **PASS** = splat captured and exported in ≤ 10 min, loaded by the viewer and rendered headless;
≥ 2 of 3 objects pointed at correctly in a render; render → point in ≤ 5 s p50.
**Differs from:** #24 Dream Run and #21 Dry Run (Genie dream, one photo deep, no ground truth). #11 Hot/Cold
(table top, live only). Before/After (killed).
**Scores:** wow **5** · proof **4** (real outsider questions, physical success check, flat-photo baseline) · buildable by 16:00 **3**
(capture quality in a busy room, headless splat rendering, and the ray to 3D are the risky parts).

## Idea B · Dream vs Twin (the splat grades Genie)
**Pitch:** "World models make things up. We built a true 3D copy of this room and catch Genie in the act."
**The 20-second clip:** a split screen. Left: Genie seeded with a splat render, turning left. Right: the splat rendering the
*same* turn from the same pose. A meter turns red the moment they disagree ("Genie added a door at 1.8 s").
**How:** seed Genie with a splat render at pose P. Hold `arrow_left` for t seconds, then render the splat at P rotated
by the matching angle (calibrate degrees per second once). One **Neon** call per pair: "same place, same objects? name
what's different." Decision 1 scores every 0.5 s and Neon confirms the first flag. That's the gate pattern again.
**Eval:** 20 start poses across the venue splat, chosen on a grid before any run. Report a faithfulness curve:
the share of pairs judged "same place" against turn angle. **Unlike #26 Trust Horizon**, which checks Genie against
itself (look away and back), this checks Genie against the real geometry.
**Baseline:** Nano Banana image edit ("show the view 45° to the left") from the same render, scored the same way.
**Spike:** 10 poses, 2 s turns. **PASS** = the Neon judge separates true pairs from shuffled pairs 10/10, and the curve is
measured on 10/10 sessions. The verdict itself is a finding whichever way it goes.
**Scores:** wow **4** · proof **5** (ground truth by construction) · buildable **3** (needs A's capture and
renderer). Best as A's "where it breaks" slide, not on its own: the judges score Creativity, and a pure model audit is close to the image-analyser ban.

## Idea C · Errand Rehearsal (route in the splat, done in the real room, checked live)
**Pitch:** "Before anyone moves, the agent rehearses the errand in the 3D copy. Then it guides a real person, and
checks every checkpoint against the live camera."
**The 20-second clip:** "bring a water bottle to table 4." The rehearsal video flies the route. Then a teammate walks it with
the phone, and each checkpoint lights up green when Decision 1 says "arrived at checkpoint k" on the live frame.
Checks follow the route order, so there is no matching across look-alike places.
**Eval:** transfer gap. Rehearsed success vs real success on 15 errands written by other hackers. Baseline: directions from the flat photo list.
**Scores:** wow 4 · proof 3 (n small, needs people walking) · buildable 2. **Fold into A as step 4, not a separate build.**

## Dropped, with the reason
- **Dream-Ahead** (re-seed Genie from each live frame, roll out left/forward/right, pick the best). When the target is
  visible, "point at it and turn" (Robotics-ER 2 alone) already answers. When it's not visible, Genie invents it. Predicted to lose to its own baseline.
- **Multi-photo Genie venue**: the API refuses it (measured above).

## Ranking
1. **A · Room Search** (wow 5 / proof 4 / build 3). The splat makes the agent's answer checkable in the real room, and the questions come from outsiders.
2. **B · Dream vs Twin** (4 / 5 / 3), as A's "where it breaks" act. It reuses A's capture and renderer.
3. C · Errand Rehearsal (4 / 3 / 2). Fold into A.

**Biggest risk to A:** a phone splat of a crowded room may be blurry, and headless rendering of a web splat viewer is
untested. The spike settles both in about 20 minutes. Capturing the room is a person's job (label `human`), and someone should start now.
