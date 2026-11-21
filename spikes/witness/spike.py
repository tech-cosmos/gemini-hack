"""Witness spike: does a list of failure-first checks beat one "did it succeed?" question?

Data: ArmnetBench v0.1 (HF armnet/armnetbench_v01_robometer, Apache-2.0), real SO-101 robot rollouts,
front camera only, teleoperated demos excluded, "suboptimal" counted as failure (as the dataset card does).
Arm A: one Decision 1 yes/no per clip.  Arm B: Carbon writes 5-15 failure-first checks per task from the
instruction alone (never sees test clips); Decision 1 scores all of them on the clip in one call; the clip
passes only if every check passes.  Pass mark (written in docs/IDEAS.md before the run): A balanced
accuracy <= 0.85 and B beats A by >= 0.05, or B halves A's false-success rate.

Run: uv run --with google-genai==3.6.1 --with pandas --with pyarrow python spikes/witness/spike.py
"""
import base64
import json
import os
import pathlib
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from google import genai

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
HF = "https://huggingface.co/datasets/armnet/armnetbench_v01_robometer/resolve/main/"
DECIDER = "models/gemini-decision-1"
WRITER = "gemini-4-carbon"
N_PER_CLASS = 20
SEED = 0

client = genai.Client(http_options={"api_version": "v1beta"})  # decisions live on v1beta


def fetch(url, path):
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    return path


def sample():
    meta = pd.read_parquet(fetch(HF + "so101/train-00000-of-00001.parquet", CACHE / "so101.parquet"))
    meta = meta[meta.id.str.endswith("/front")].copy()
    meta["policy"] = meta.id.str.split("/").str[2]
    meta["tdir"] = meta.id.str.split("/").str[1]
    meta = meta[meta.policy != "teleoperated"]
    meta["success"] = meta.quality_label == "successful"
    picks = []
    for label in (True, False):
        pool = meta[meta.success == label]
        hard = pool[pool.tdir.isin(["ring_insert", "tool_insert"])]  # contact-heavy, where FailBench says detectors fail
        rest = pool[~pool.tdir.isin(["ring_insert", "tool_insert"])]
        picks += [hard.sample(N_PER_CLASS // 2, random_state=SEED), rest.sample(N_PER_CLASS // 2, random_state=SEED)]
    return pd.concat(picks).reset_index(drop=True)


def cached_json(key, fn):
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    out = fn()
    path.write_text(json.dumps(out, indent=1))
    return out


def checks_for(task):
    prompt = (
        "A robot arm was given this instruction:\n"
        f'"{task}"\n'
        "Write 5 to 15 yes/no checks a careful inspector would run on a video of the attempt to catch a FALSE "
        "claim of success. Each check must be answerable from the video alone, refer to concrete visible "
        "evidence (positions, contact, final state, orientation), and be phrased so that YES means "
        "consistent with real success. Focus on the end state and the ways this specific task usually goes "
        "wrong. Return only a JSON list of strings."
    )
    def call():
        text = client.models.generate_content(model=WRITER, contents=prompt).text or ""
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise ValueError(f"no JSON list from {WRITER}: {text[:200]}")
        return json.loads(m.group(0))
    key = "checks_" + re.sub(r"\W+", "_", task)[:60]
    return cached_json(key, call)


def decide(row, questions, arm):
    def call():
        video = fetch(HF + row.frames, CACHE / row.frames.replace("/", "__"))
        data = base64.b64encode(video.read_bytes()).decode()
        t = time.time()
        try:
            r = decide_call(data, row, questions)
        except Exception as e:  # a content-filter block is a result to report, not a crash
            if "prohibited_content" in str(e):
                return {"blocked": True, "error": str(e)[:200]}
            raise
        return {"p": {k: a.noul for k, a in r.answers.items()}, "latency": time.time() - t,
                "tokens": r.usage.total_tokens}
    return cached_json(f"{arm}_" + re.sub(r"\W+", "_", row.id), call)


def decide_call(data, row, questions):
    for attempt in range(4):
        try:
            return client.decisions.create(
            model=DECIDER,
            input=[{"type": "video", "data": data, "mime_type": "video/mp4"},
                   {"type": "text", "text": f"Instruction given to the robot: {row.task}"}],
            questions={k: {"type": "noul", "instructions": q} for k, q in questions.items()},
            )
        except Exception as e:
            if attempt == 3 or not any(c in str(e) for c in ("429", "503", "500")):
                raise
            time.sleep(2 ** attempt)


def scores(y, pred):
    tp = sum(a and b for a, b in zip(y, pred)); tn = sum((not a) and (not b) for a, b in zip(y, pred))
    pos = sum(y); neg = len(y) - pos
    return {"balanced_acc": round((tp / pos + tn / neg) / 2, 3), "false_success_rate": round((neg - tn) / neg, 3)}


def auroc(y, s):
    pos = [v for a, v in zip(y, s) if a]; neg = [v for a, v in zip(y, s) if not a]
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 3)


def main():
    clips = sample()
    checks = {t: checks_for(t) for t in clips.task.unique()}
    one_q = "Watch to the end. Did the robot fully complete the instruction, with the final state matching it?"
    with ThreadPoolExecutor(8) as ex:
        a = list(ex.map(lambda r: decide(r, {"success": one_q}, "A"), clips.itertuples()))
        b = list(ex.map(lambda r: decide(r, {f"c{i}": q for i, q in enumerate(checks[r.task])}, "B"),
                        clips.itertuples()))
    keep = [not (x.get("blocked") or z.get("blocked")) for x, z in zip(a, b)]
    blocked = clips[[not k for k in keep]].id.tolist()
    clips = clips[keep].reset_index(drop=True)
    a = [x for x, k in zip(a, keep) if k]
    b = [x for x, k in zip(b, keep) if k]
    y = list(clips.success)
    pa = [x["p"]["success"] for x in a]
    pb = [min(x["p"].values()) for x in b]  # failure-first: one failed check fails the clip
    res = {
        "n": len(y), "positives": sum(y), "blocked_by_filter": blocked,
        "A_single_question": {**scores(y, [p > 0.5 for p in pa]), "auroc": auroc(y, pa)},
        "B_failure_first_checks": {**scores(y, [p > 0.5 for p in pb]), "auroc": auroc(y, pb)},
        "checks_per_task": {t: len(c) for t, c in checks.items()},
        "latency_s_median": {"A": sorted(x["latency"] for x in a)[len(a) // 2],
                             "B": sorted(x["latency"] for x in b)[len(b) // 2]},
        "tokens_total": {"A": sum(x["tokens"] for x in a), "B": sum(x["tokens"] for x in b)},
    }
    per = clips.assign(pA=pa, pB=pb)[["id", "task", "policy", "success", "pA", "pB"]]
    per.to_csv(HERE / "per_clip.csv", index=False)
    (HERE / "result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
