"""Census spike: does "list instances per shard, merge duplicates with Decision 1" count better than voting?

Data: SVCBench O2-Unique questions ("How many different X have appeared so far?"), HF buaaplay/SVCBench
(CC-BY-4.0 on the repo; clips come from ScanNet / ScanNet++ / ARKitScenes, whose own terms are research-use).
Real indoor scans only, last query per question (longest "so far"), count 2-12, one question per video.
Each video is cut to [0, query_time] ourselves.

Arm A (baseline): Hydrogen answers with one integer, 5 samples, median.
Arm B (swarm): the clip is cut into shards; Hydrogen lists every distinct instance per shard with a time and
a box; each instance becomes a crop from the full-resolution frame; Decision 1 gets all crops in one call and
answers "same physical object?" for every cross-shard pair; union-find on p > 0.5; count = clusters.
Pass mark (docs/IDEAS.md, written before the run): B exact match >= A + 10 points. The pair-check AUROC part
needs hand-labelled pairs and is NOT run here.

Run: uv run --no-project --with google-genai==3.6.1 python -I spikes/census/spike.py
"""
import base64
import json
import pathlib
import re
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from statistics import median

from google import genai
from google.genai import types

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
HF = "https://huggingface.co/datasets/buaaplay/SVCBench/resolve/main/"
WORKER = "gemini-4-hydrogen"
DECIDER = "models/gemini-decision-1"
N_QUESTIONS = 30
SHARD_S = 20
VOTES = 5
MAX_CLIP_S = 180

gen = genai.Client()
dec = genai.Client(http_options={"api_version": "v1beta"})  # decisions live on v1beta
LOW = types.GenerateContentConfig(media_resolution="MEDIA_RESOLUTION_LOW", temperature=1.0)


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


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def pick_questions():
    rows = [json.loads(l) for l in fetch(HF + "vcbench_eval.jsonl", CACHE / "eval.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["counting_subtype"] == "O2-Unique" and r["source_dataset"] != "simulated"]
    last = {}
    for r in rows:  # keep the last query of each question: the longest "so far"
        if r["id"] not in last or r["query_index"] > last[r["id"]]["query_index"]:
            last[r["id"]] = r
    seen, picks = set(), []
    for r in sorted(last.values(), key=lambda r: r["q_id"]):
        if 2 <= r["count"] <= 12 and r["query_time"] <= MAX_CLIP_S and r["video_path"] not in seen:
            seen.add(r["video_path"])
            picks.append(r)
    step = max(1, len(picks) // N_QUESTIONS)  # spread over the list instead of taking the first few videos
    return picks[::step][:N_QUESTIONS]


def clip_for(q):
    src = fetch(HF + f"videos/{q['source_dataset']}/{q['video_path']}", CACHE / q["video_path"])
    out = CACHE / f"clip_{q['q_id']}.mp4"
    if not out.exists():
        ffmpeg("-i", str(src), "-t", str(q["query_time"]), "-vf", "scale=-2:360,fps=2", "-an",
               "-c:v", "libx264", "-preset", "veryfast", str(out))
    return src, out


def ask(contents, retries=4):
    for attempt in range(retries):
        try:
            return gen.models.generate_content(model=WORKER, contents=contents, config=LOW).text or ""
        except Exception as e:
            if attempt == retries - 1 or not any(c in str(e) for c in ("429", "500", "503")):
                raise
            time.sleep(2 ** attempt)
    return ""


def thing(q):
    m = re.search(r"How many different (.+?) have appeared", q["question"])
    return m.group(1) if m else "objects"


def baseline(q, clip):
    def run():
        v = types.Part.from_bytes(data=clip.read_bytes(), mime_type="video/mp4")
        prompt = (f"{q['question']} Count each physical {thing(q)} once even if it appears several times. "
                  "Answer with a single integer only.")
        votes = []
        for _ in range(VOTES):
            m = re.search(r"\d+", ask([v, prompt]))
            votes.append(int(m.group(0)) if m else 0)
        return {"votes": votes, "answer": int(median(votes))}
    return cached(f"A_{q['q_id']}", run)


def swarm(q, src, clip):
    def run():
        dur = float(q["query_time"])
        shards = [(s, min(s + SHARD_S, dur)) for s in range(0, int(dur) + 1, SHARD_S) if s < dur - 0.5]
        instances = []
        for si, (s, e) in enumerate(shards):
            part = CACHE / f"shard_{q['q_id']}_{si}.mp4"
            if not part.exists():
                ffmpeg("-ss", str(s), "-i", str(clip), "-t", str(e - s), "-c", "copy", str(part))
            prompt = (f"List every distinct {thing(q)} visible in this clip, each physical one once. For each give "
                      "the time in seconds (from the clip start) of its clearest view and its bounding box at that "
                      "moment as [ymin, xmin, ymax, xmax] scaled 0-1000. Return only JSON: "
                      '[{"t": 3.5, "box": [y0, x0, y1, x1]}]. Return [] if there is none.')
            text = ask([types.Part.from_bytes(data=part.read_bytes(), mime_type="video/mp4"), prompt])
            m = re.search(r"\[.*\]", text, re.S)
            try:
                found = json.loads(m.group(0)) if m else []
            except json.JSONDecodeError:
                found = []
            for f in found:
                if isinstance(f, dict) and "t" in f and len(f.get("box", [])) == 4:
                    instances.append({"shard": si, "t": s + float(f["t"]), "box": f["box"]})
        crops = []
        for i, inst in enumerate(instances):  # crop from the full-resolution source with a 30% margin
            y0, x0, y1, x1 = [max(0, min(1000, float(v))) / 1000 for v in inst["box"]]
            h, w = max(y1 - y0, 0.05), max(x1 - x0, 0.05)
            y0, x0 = max(0, y0 - 0.3 * h), max(0, x0 - 0.3 * w)
            h, w = min(1 - y0, 1.6 * h), min(1 - x0, 1.6 * w)
            out = CACHE / f"crop_{q['q_id']}_{i}.jpg"
            ffmpeg("-ss", f"{min(inst['t'], dur - 0.1):.2f}", "-i", str(src), "-frames:v", "1",
                   "-vf", f"crop=iw*{w:.3f}:ih*{h:.3f}:iw*{x0:.3f}:ih*{y0:.3f},scale=-2:256", str(out))
            crops.append(out)
        pairs = [(i, j) for i, j in combinations(range(len(instances)), 2)
                 if instances[i]["shard"] != instances[j]["shard"]][:1000]
        probs = {}
        if pairs:
            inp = [{"type": "text", "text": f"Crops of {thing(q)} seen while walking through one indoor scene."}]
            for i, c in enumerate(crops):
                inp += [{"type": "text", "text": f"crop {i}:"},
                        {"type": "image", "data": base64.b64encode(c.read_bytes()).decode(), "mime_type": "image/jpeg"}]
            r = dec.decisions.create(model=DECIDER, input=inp, questions={
                f"{i}_{j}": {"type": "noul", "instructions":
                             f"Do crop {i} and crop {j} show the same physical {thing(q)} (the same individual "
                             "object in the room, not just the same kind)?"} for i, j in pairs})
            probs = {k: a.noul for k, a in r.answers.items()}
        parent = list(range(len(instances)))
        def root(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for k, p in probs.items():
            if p > 0.5:
                i, j = map(int, k.split("_"))
                parent[root(i)] = root(j)
        return {"shards": len(shards), "instances": len(instances), "pairs": len(pairs),
                "merges": sum(p > 0.5 for p in probs.values()),
                "answer": len({root(i) for i in range(len(instances))})}
    return cached(f"B_{q['q_id']}", run)


def run_one(q):
    src, clip = clip_for(q)
    return {"q_id": q["q_id"], "source": q["source_dataset"], "question": q["question"],
            "seconds": q["query_time"], "truth": q["count"], "A": baseline(q, clip), "B": swarm(q, src, clip)}


def main():
    qs = pick_questions()
    with ThreadPoolExecutor(6) as ex:
        rows = [r for r in ex.map(run_one, qs)]
    def summary(arm):
        err = [r[arm]["answer"] - r["truth"] for r in rows]
        return {"exact_match": round(sum(e == 0 for e in err) / len(err), 3),
                "mae": round(sum(abs(e) for e in err) / len(err), 2),
                "mean_signed_error": round(sum(err) / len(err), 2)}
    res = {"n": len(rows), "A_hydrogen_5vote": summary("A"), "B_swarm_merge": summary("B"),
           "B_instances_median": median(r["B"]["instances"] for r in rows),
           "B_pairs_median": median(r["B"]["pairs"] for r in rows)}
    (HERE / "per_question.json").write_text(json.dumps(rows, indent=1))
    (HERE / "result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
