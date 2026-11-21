"""Spike 1+5: can Decision 1 tell a correct human manipulation video from a wrong one, and do
failure-first checks written by Carbon beat one "was the goal reached?" question?

Data: ego2act-bench (CC-BY-4.0, https://huggingface.co/datasets/ego2act/ego2act-bench), human recordings.
Pass mark (docs/IDEAS.md, written 11:31 before the run): Decision 1 accepts video; arm (a) balanced
accuracy <= 0.85 and arm (b) beats (a) by >= 0.05 balanced accuracy or halves false "success".

Run: .venv/bin/python spikes/s1_ego2act.py [n_tasks=10]
Clips are cached in .context/ego2act/, Carbon's checks in results/s1_checks.json.
"""
import base64, concurrent.futures as cf, csv, faulthandler, io, json, os, pathlib, sys, time, urllib.request

for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(1500, exit=True)
from google import genai

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
BASE = "https://huggingface.co/datasets/ego2act/ego2act-bench/resolve/main"
CACHE = pathlib.Path(".context/ego2act"); CACHE.mkdir(parents=True, exist_ok=True)
RES = pathlib.Path("results"); RES.mkdir(exist_ok=True)
gen = genai.Client(http_options={"timeout": 180_000})
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 180_000})


def fetch(rel):
    p = CACHE / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{BASE}/{rel}", timeout=120) as r:
            p.write_bytes(r.read())
    return p


# 1. Pick tasks that have both correct_1 and wrong_1, shortest first.
rows = list(csv.DictReader(io.StringIO(fetch("human/metadata.csv").read_text())))
dur = {(r["case_id"], r["label"], r["file_name"].rsplit("/", 1)[-1]): float(r["duration_s"]) for r in rows}
cases = sorted({r["case_id"] for r in rows})
pairs = []
for c in cases:
    a, b = dur.get((c, "correct", "correct_1.mp4")), dur.get((c, "wrong", "wrong_1.mp4"))
    if a and b:
        pairs.append((max(a, b), c))
pairs.sort()
tasks = [c for _, c in pairs[:N]]
goals = {c: json.loads(fetch(f"cases/{c}/metadata.json").read_text())["goal"] for c in tasks}
clips = [(c, lab, f"human/{lab}/{c}/{lab}_1.mp4") for c in tasks for lab in ("correct", "wrong")]
for _, _, rel in clips:
    fetch(rel)
print(f"{len(tasks)} tasks, {len(clips)} clips, longest {pairs[N-1][0]:.1f} s", flush=True)

# 2. Carbon writes failure-first checks from the goal text (cached).
checks_path = RES / "s1_checks.json"
checks = json.loads(checks_path.read_text()) if checks_path.exists() else {}


def write_checks(c):
    r = gen.interactions.create(model="gemini-4-carbon", input=(
        "A person is filmed from their own point of view doing a manipulation task. Goal for the final state:\n"
        f"{goals[c]}\n\n"
        "Write 5 to 8 yes/no checks a strict inspector would apply to the END of the video to catch the ways "
        "people get this wrong (wrong object, swapped items, wrong orientation, step skipped, not fully "
        "closed/seated). Each check must be phrased so that YES means that part is done correctly. "
        "One check per line, no numbering, no other text."))
    return c, [l.strip("-• ").strip() for l in (r.output_text or "").splitlines() if len(l.strip()) > 8][:8]


todo = [c for c in tasks if c not in checks]
with cf.ThreadPoolExecutor(5) as ex:
    for c, cl in ex.map(write_checks, todo):
        checks[c] = cl
checks_path.write_text(json.dumps(checks, indent=2))


# 3. Decision 1 on each clip: arm (a) one question, arm (b) Carbon's checks, both in one call.
def judge(item):
    c, lab, rel = item
    vid = {"type": "video", "data": base64.b64encode(fetch(rel).read_bytes()).decode(),
           "mime_type": "video/mp4", "resolution": "low"}
    qs = {"goal_reached": {"type": "noul", "instructions":
          f"By the end of the video, is this goal fully reached? Goal: {goals[c]}"}}
    for i, q in enumerate(checks[c]):
        qs[f"check_{i}"] = {"type": "noul", "instructions": q}
    t = time.perf_counter()
    try:
        r = beta.decisions.create(model="gemini-decision-1",
                                  input=[{"type": "text", "text": "First-person video of a person doing a task."}, vid],
                                  questions=qs)
    except Exception as e:
        return {"case": c, "label": lab, "error": str(e)[:300]}
    ans = {k: round(a.noul, 3) for k, a in r.answers.items()}
    conf = {k: round(a.confidence, 3) for k, a in r.answers.items()}
    cks = [v for k, v in ans.items() if k.startswith("check_")]
    return {"case": c, "label": lab, "s": round(time.perf_counter() - t, 2),
            "a_success": ans["goal_reached"] > 0.5, "b_success": bool(cks) and min(cks) > 0.5,
            "p_goal": ans["goal_reached"], "p_checks": cks, "min_check": min(cks) if cks else None,
            "conf_goal": conf["goal_reached"]}


with cf.ThreadPoolExecutor(5) as ex:
    out = list(ex.map(judge, clips))


def metrics(arm):
    ok = [o for o in out if "error" not in o]
    pos = [o for o in ok if o["label"] == "correct"]; neg = [o for o in ok if o["label"] == "wrong"]
    tpr = sum(o[f"{arm}_success"] for o in pos) / max(len(pos), 1)
    tnr = sum(not o[f"{arm}_success"] for o in neg) / max(len(neg), 1)
    return {"balanced_acc": round((tpr + tnr) / 2, 3), "tpr": round(tpr, 3), "tnr": round(tnr, 3),
            "false_success": sum(o[f"{arm}_success"] for o in neg), "n_correct": len(pos), "n_wrong": len(neg)}


summary = {"a_one_question": metrics("a"), "b_failure_first_checks": metrics("b"),
           "errors": [o for o in out if "error" in o],
           "decision_latency_s": sorted(o["s"] for o in out if "s" in o)}
a, b = summary["a_one_question"], summary["b_failure_first_checks"]
summary["video_accepted"] = len(summary["errors"]) < len(out)
summary["pass"] = (summary["video_accepted"] and a["balanced_acc"] <= 0.85 and
                   (b["balanced_acc"] - a["balanced_acc"] >= 0.05 or
                    b["false_success"] <= a["false_success"] / 2 and a["false_success"] > 0))
(RES / "s1_ego2act.json").write_text(json.dumps({"summary": summary, "clips": out}, indent=2))
print(json.dumps(summary, indent=2))
