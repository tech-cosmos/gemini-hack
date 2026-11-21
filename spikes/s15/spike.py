"""Spike 15 (idea 34 Robot Data Engine): does Decision 1 keep only the Omni edits that still finish the task?

Data: ArmnetBench v0.1 (HF armnet/armnetbench_v01_robometer, Apache-2.0), SO-101 front camera, the two eye-drops tasks,
teleoperated excluded, none of the clips the Witness spike used. Per task: 5 successful + 5 failed, random_state 0.
Successful clips must be <= 15 s (Omni's edit limit); failed clips are never edited, so they have no length rule.
(a) One Decision 1 success question on each of the 20 originals.
(b) Omni 1.2 edits each of the 10 successful clips with 2 fixed prompts = 20 variants. A person labels every variant
    by eye from a side-by-side review clip, before any score is shown. Decision 1 asks the same question; keep p >= 0.5.
Pass mark (docs/IDEAS.md spike 15, written 14:05 before any call): gate precision >= 0.9, yield (kept / 20) >= 0.4,
gate precision >= keep-all precision + 0.15. KILL = gate precision <= keep-all precision.

Run:  uv run --no-project --with google-genai==3.6.1 --with pandas --with pyarrow python -I spikes/s15/spike.py gen
      (person fills spikes/s15/eye_labels.json: {"v01": true, ...}, true = the arm still puts the eye drops there)
      uv run ... python -I spikes/s15/spike.py score
"""
import base64
import json
import pathlib
import random
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from google import genai

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "cache"
REVIEW = CACHE / "review"
REVIEW.mkdir(parents=True, exist_ok=True)
HF = "https://huggingface.co/datasets/armnet/armnetbench_v01_robometer/resolve/main/"
WITNESS = HERE.parent / "witness" / "cache"
FF = "/opt/homebrew/bin/"
DECIDER = "models/gemini-decision-1"
OMNI = "gemini-omni-1.2-flash"
TASKS = ["Put the eye drops into the basket", "Put the eye drops on the shelf"]
PER = 5
QUESTION = "Watch to the end. Did the robot fully complete the instruction, with the final state matching it?"
PROMPTS = {
    "scene": "Keep every motion of the robot arm and of the eye drops exactly as in the video, frame by frame. "
             "Change only the surroundings: make the table dark walnut wood and the lighting warm evening light.",
    "object": "Keep every motion of the robot arm exactly as in the video, frame by frame. Make the eye drops bottle "
              "bright blue, and add a red coffee mug standing on the table far from the arm's path.",
}

client = genai.Client(http_options={"api_version": "v1beta", "timeout": 600_000})  # decisions + Omni live on v1beta


def fetch(url, path):
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    return path


def cached(key, fn):
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    out = fn()
    path.write_text(json.dumps(out, indent=1))
    return out


def retry(fn, tries=4):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            if attempt == tries - 1 or not any(c in str(e) for c in ("429", "500", "503")):
                raise
            time.sleep(2 ** attempt)


def duration(p):
    out = subprocess.run([FF + "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def clip(row):
    return fetch(HF + row.frames, CACHE / row.frames.replace("/", "__"))


def pick():
    meta = pd.read_parquet(WITNESS / "so101.parquet")
    meta = meta[meta.id.str.endswith("/front") & meta.task.isin(TASKS)].copy()
    meta = meta[meta.id.str.split("/").str[2] != "teleoperated"]
    used = {p.stem[2:] for p in WITNESS.glob("A_*.json")}
    meta = meta[~meta.id.map(lambda i: re.sub(r"\W+", "_", i)).isin(used)]
    picks = []
    for task in TASKS:
        for label in ("successful", "failure"):
            pool = meta[(meta.task == task) & (meta.quality_label == label)].sample(frac=1, random_state=0)
            got = []
            for row in pool.itertuples():
                if label == "failure" or duration(clip(row)) <= 15.0:
                    got.append(row)
                if len(got) == PER:
                    break
            picks += [{"id": r.id, "task": r.task, "success": label == "successful", "path": str(clip(r))} for r in got]
    return picks


def decide(key, path, task):
    def call():
        data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
        t = time.time()
        try:
            r = retry(lambda: client.decisions.create(model=DECIDER, input=[
                {"type": "video", "data": data, "mime_type": "video/mp4"},
                {"type": "text", "text": f"Instruction given to the robot: {task}"}],
                questions={"success": {"type": "noul", "instructions": QUESTION}}))
        except Exception as e:  # a content-filter block is a result to report, not a crash
            if "prohibited_content" in str(e):
                return {"blocked": True, "error": str(e)[:200]}
            raise
        assert r is not None and r.answers, "empty Decision 1 reply"
        return {"p": r.answers["success"].noul, "latency": round(time.time() - t, 2)}
    return cached(f"D_{key}", call)


def edit(key, path, prompt):
    out = CACHE / f"{key}.mp4"
    def call():
        f = client.files.upload(file=path)
        while f.state.name == "PROCESSING":
            time.sleep(2)
            f = client.files.get(name=f.name)
        t = time.time()
        r = retry(lambda: client.interactions.create(
            model=OMNI, input=[{"type": "video", "uri": f.uri}, {"type": "text", "text": prompt}],
            response_format={"type": "video", "resolution": "360p"}))
        wall = round(time.time() - t, 1)
        assert r is not None, "empty Omni reply"
        v = r.output_video
        if v is None:
            return {"ok": False, "wall_s": wall, "status": str(r.status), "raw": str(r)[:500]}
        if getattr(v, "data", None):
            out.write_bytes(base64.b64decode(v.data))
        else:
            client.files.download(file=v.uri, destination=str(out))
        return {"ok": True, "wall_s": wall, "mp4": str(out)}
    return cached(f"E_{key}", call)


def side_by_side(orig, variant, out):
    if not out.exists():
        subprocess.run([FF + "ffmpeg", "-v", "error", "-y", "-i", orig, "-i", variant, "-filter_complex",
                        "[0:v]scale=-2:360,setsar=1[a];[1:v]scale=-2:360,setsar=1[b];[a][b]hstack=inputs=2",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", str(out)], check=True)


def gen():
    picks = cached("picks", pick)
    jobs = [(f"{i:02d}_{name}", c, prompt) for i, c in enumerate(picks) if c["success"] for name, prompt in PROMPTS.items()]
    with ThreadPoolExecutor(4) as ex:
        orig = list(ex.map(lambda ic: decide(f"orig_{ic[0]:02d}", ic[1]["path"], ic[1]["task"]), enumerate(picks)))
        edits = list(ex.map(lambda j: edit(j[0], j[1]["path"], j[2]), jobs))
        var = list(ex.map(lambda je: decide(f"var_{je[0][0]}", je[1]["mp4"], je[0][1]["task"]) if je[1]["ok"] else None,
                          zip(jobs, edits)))
    order = list(range(len(jobs)))
    random.Random(15).shuffle(order)  # review order hides which prompt or clip a variant came from
    review = {}
    for n, k in enumerate(order, 1):
        if edits[k]["ok"]:
            vid = f"v{n:02d}"
            side_by_side(jobs[k][1]["path"], edits[k]["mp4"], REVIEW / f"{vid}.mp4")
            review[vid] = {"job": jobs[k][0], "task": jobs[k][1]["task"]}
    (CACHE / "review.json").write_text(json.dumps(review, indent=1))
    print(json.dumps({"originals": len(orig), "edits_ok": sum(e["ok"] for e in edits), "edits": len(edits),
                      "edit_wall_s_median": sorted(e["wall_s"] for e in edits)[len(edits) // 2],
                      "variants_scored": sum(v is not None for v in var), "review_dir": str(REVIEW)}, indent=1))


def bal_acc(y, pred):
    pos = [p for a, p in zip(y, pred) if a]
    neg = [p for a, p in zip(y, pred) if not a]
    return round((sum(pos) / len(pos) + sum(not p for p in neg) / len(neg)) / 2, 3)


def score():
    picks = cached("picks", pick)
    review = json.loads((CACHE / "review.json").read_text())
    eye = json.loads((HERE / "eye_labels.json").read_text())
    assert set(eye) == set(review), "eye_labels.json must label every review clip"
    orig = [decide(f"orig_{i:02d}", c["path"], c["task"]) for i, c in enumerate(picks)]
    ok = [(o, c) for o, c in zip(orig, picks) if not o.get("blocked")]
    rows = []
    for vid, r in sorted(review.items()):
        d = json.loads((CACHE / f"D_var_{r['job']}.json").read_text())
        rows.append({"vid": vid, **r, "eye_true": eye[vid], "p": d.get("p"), "blocked": d.get("blocked", False)})
    n_jobs = 2 * sum(c["success"] for c in picks)
    kept = [r for r in rows if not r["blocked"] and r["p"] >= 0.5]
    keep_all = sum(r["eye_true"] for r in rows) / len(rows)
    gate = sum(r["eye_true"] for r in kept) / len(kept) if kept else 0.0
    res: dict = {
        "originals": {"n": len(ok), "blocked": len(orig) - len(ok),
                      "balanced_acc_at_0.5": bal_acc([c["success"] for _, c in ok], [o["p"] >= 0.5 for o, _ in ok])},
        "variants": {"planned": n_jobs, "edited": len(rows), "eye_true": sum(r["eye_true"] for r in rows),
                     "kept": len(kept), "keep_all_precision": round(keep_all, 3), "gate_precision": round(gate, 3),
                     "yield_kept_over_planned": round(len(kept) / n_jobs, 3),
                     "eye_true_rejected": sum(r["eye_true"] for r in rows if r not in kept)},
    }
    v = res["variants"]
    # registered clause: keep-all precision >= 0.9 means the gate is not needed (FAIL for the gate, augmentation works)
    res["verdict"] = ("FAIL_GATE_NOT_NEEDED" if keep_all >= 0.9 else "KILL" if gate <= keep_all else
                      "PASS" if gate >= 0.9 and v["yield_kept_over_planned"] >= 0.4 and gate >= keep_all + 0.15 else "FAIL")
    (HERE / "per_variant.json").write_text(json.dumps(rows, indent=1))
    (HERE / "result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"gen": gen, "score": score}[sys.argv[1]]()
