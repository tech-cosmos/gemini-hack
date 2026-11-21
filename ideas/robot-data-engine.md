# Robot Data Engine (Ghost Hands as a data collector) · Dan, 14:05

**Pitch:** "Every person is a robot data collector. Ghost Hands guides you through a robot task, checks every
step, and turns one checked human demo into ten checked training clips, then shows your own motion done by a robot arm."

## The one task (fixed, so every claim is scorable)
**"Restock the pharmacy: put the eye drops into the basket, then put the eye drops on the shelf."**
These are two real tasks in ArmnetBench (SO-101 arm, Apache-2.0): "Put the eye drops into the basket" (290 rollouts)
and "Put the eye drops on the shelf" (349 rollouts), each labelled successful / failed. So our demos are in-distribution
for a public robot dataset, and our labeller can be scored on that dataset's real robot clips.
Props: one eye-drops bottle, a small basket or cup, a box as the shelf. A fixed front camera.

Why a fixed task fixes Ghost Hands' hole: spike 14 showed ER 2 can't guess *where* an arbitrary item goes
(0.47 hit). Here the target is named ("the basket"), so ER 2 only has to point at a named object, which spike 8 passed (10/10).

## Pipeline
1. **Guide:** Carbon has the step list (fixed for this task). Robotics-ER 2 points at the bottle and at the target and the
   overlay draws the arrow on the live video (~2.2 s per point, spike 8).
2. **Check every step:** the Step Guard cascade (Decision 1 when sure, Neon when unsure) labels each step done / not done,
   with Neon's reason on a failure (0.925 at 1.58 s p50 on held-out human clips, spike 2).
3. **Label:** each episode = video + instruction + step boundaries + success per step + ER 2 grasp and place points (2D).
4. **Multiply:** Omni 1.2 edits the checked clip into variants (lighting, table, bottle colour, distractors), actions
   kept (spike 5: a 12.3 s real clip edited in 131.9 s with actions kept).
5. **Gate the synthetic clips:** Decision 1 re-asks the success question on every variant and drops the ones where the
   edit broke the task. Load-bearing: spike 6a showed Omni-generated clips often don't finish multi-object goals.
6. **Export:** LeRobot-style episodes (format not yet checked against the LeRobot schema).

**The wow moment (stretch, gated):** Omni edits the judge's hand into a white robot arm doing the same motion in the same
scene. The judge did it with their hand; two minutes later a robot does it on screen. The gate says whether the
robot version still finishes the task.

## Demo (3 min)
- 0:00 Judge stands at the table. Screen: "Restock the pharmacy." Arrow appears on the bottle, then on the basket.
- 0:30 Judge does it. Green tick in ~1.6 s. Judge deliberately puts it next to the basket: red, Neon says why.
- 1:15 Episode card: video, steps, labels, points. "1 human demo."
- 1:30 Variants grid fills in (pre-rendered from a run 2 min earlier, said out loud): 10 variants, the gate rejects the broken ones in red.
- 2:15 Hand → robot-arm clip of the judge's own demo.
- 2:40 The numbers: labeller accuracy on real ArmnetBench robot clips; gate precision on Omni variants vs keeping all.

## Proof (5 Sigma)
- **E1, labels on real robot data:** Decision 1 / cascade success labels on held-out ArmnetBench eye-drops clips.
  Prior: Witness arm A, one Decision 1 question on 39 mixed ArmnetBench clips: 0.875 balanced accuracy, AUROC 0.95, 0 false successes.
- **E2, synthetic gate:** spike 15 below. Baseline = keep every Omni variant.
- **E3 (stretch):** hand → arm edits judged by eye.

## Holes, said out loud
- Human-hand demos are not robot joint trajectories. What transfers: language, step labels, success labels, 2D grasp
  and place points, and (stretch) arm-rendered video. We do not claim a policy trained on it.
- Omni edits take ~132 s each, so the live demo shows variants from an earlier run.
- "Synthetic" = Omni edits of a real demo, not generated from nothing.
