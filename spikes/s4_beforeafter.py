"""Spike 4: Before/After (idea 12) on 12 indoor SceneDiff pairs (data step: spikes/s4_fetch.py).
Arm (a): one Neon agentic call with both videos lists the changes.
Arm (b): Neon agentic inventories A and B separately -> Decision 1 checks A items on video B and B items on video A
         -> change list derived in code; (b+recheck) Neon re-judges items whose Decision 1 confidence < 0.75.
One fixed matcher (Carbon, blind to the arm) maps gold objects to predicted lines; the change type must match.
Pass mark (docs/IDEAS.md, written 11:58 before the run): PASS = (b) overall F1 >= (a) F1 + 0.10 and (b) p50
end-to-end latency <= 60 s per pair. KILL = (b) F1 < (a) F1.
Run: .venv/bin/python -I spikes/s4_fetch.py && .venv/bin/python spikes/s4_beforeafter.py [n_pairs=12]
Replies are cached in .context/scenediff/cache with their measured latency; 4 pairs run at once, so Neon latencies include that load."""
import base64, concurrent.futures as cf, faulthandler, hashlib, json, os, pathlib, re, statistics, sys, threading, time
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")
faulthandler.dump_traceback_later(1500, exit=True)
from google import genai
D = pathlib.Path(".context/scenediff"); CACHE = D / "cache"; CACHE.mkdir(exist_ok=True)
gen = genai.Client(http_options={"timeout": 300_000})
beta = genai.Client(http_options={"api_version": "v1beta", "timeout": 180_000})
MAN = json.loads((D / "manifest.json").read_text())[:int(sys.argv[1]) if len(sys.argv) > 1 else 12]  # first N in rule order
CONF, MAXI = 0.75, 40
calls = {"neon": 0, "decision1": 0, "carbon": 0, "upload": 0}; lock = threading.Lock()
TYPES = ("added", "removed", "moved")

def cached(kind, key, fn):
    """Every reply is cached with its measured latency, so a rerun costs nothing and keeps the timings."""
    p = CACHE / f"{kind}_{hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]}.json"
    if p.exists(): return json.loads(p.read_text())
    t = time.perf_counter(); out = fn(); out = {"out": out, "s": round(time.perf_counter() - t, 2)}
    with lock: calls[kind.split("-")[0]] += 1
    p.write_text(json.dumps(out)); return out

def upload(path):
    def go():
        f = gen.files.upload(file=str(path))
        for _ in range(60):
            f = gen.files.get(name=f.name)
            if str(getattr(f, "state", "ACTIVE")).upper().endswith("ACTIVE"): break
            time.sleep(2)
        return f.uri
    return cached("upload", str(path), go)

def vid(uri): return {"type": "video", "uri": uri, "mime_type": "video/mp4", "processing": "agentic"}
def neon(tag, key, parts):
    return cached(f"neon-{tag}", key, lambda: (gen.interactions.create(model="gemini-4-neon", input=parts).output_text or "").strip())
def jparse(txt, opener="["):
    m = re.search(r"\[.*\]" if opener == "[" else r"\{.*\}", txt, re.S)
    try: return json.loads(m.group(0)) if m else None
    except Exception: return None
def lines(txt):
    out = []
    for l in txt.splitlines():
        m = re.match(r"\W*(added|removed|moved)\W*:\s*(.+)", l.strip(), re.I)
        if m: out.append({"type": m.group(1).lower(), "object": m.group(2).strip()[:120]})
    return out

P_BASE = ("Video A is the scene BEFORE, video B is the same scene AFTER, filmed again by hand (the camera path differs). "
          "List every object that was added, removed or moved between A and B. Ignore camera viewpoint, lighting and people. "
          "One change per line, exactly in the form `added: <object>` or `removed: <object>` or `moved: <object>`. "
          "If nothing changed, reply `none`.")
P_INV = ("List the distinct movable objects visible in this video of a scene: things a person could pick up, carry or shift "
         "(include chairs, stools, bags, clothes, bottles, small items; skip walls, floors, built-in or heavy furniture). "
         f"At most {MAXI} items, each a separate physical object. Reply with only a JSON array of "
         '{"object": "<short name with colour>", "location": "<where it is, relative to fixed things>"}.')

def d1(tag, pair, v, qs):
    if not qs: return {"out": {}, "s": 0.0}
    def go():
        b = base64.b64encode((D / pair / f"v{v}_360.mp4").read_bytes()).decode()
        r = beta.decisions.create(model="gemini-decision-1", input=[
            {"type": "text", "text": "Hand-held video of an indoor scene."},
            {"type": "video", "data": b, "mime_type": "video/mp4", "resolution": "low"}],
            questions={k: {"type": "noul", "instructions": q} for k, q in qs.items()})
        return {k: {"p": round(a.noul, 3), "conf": round(a.confidence, 3)} for k, a in r.answers.items()}
    return cached(f"decision1-{tag}", [pair, v, qs], go)

def run_pair(rec):
    pair = rec["pair"]; o = {"pair": pair, "gold": rec["gold"]}
    try:
        with cf.ThreadPoolExecutor(2) as ex: ua, ub = ex.map(lambda v: upload(D / pair / f"v{v}_720.mp4"), "12")
        up_s = max(ua["s"], ub["s"]); A, B = ua["out"], ub["out"]; o["upload_s"] = up_s
        # arm (a)
        r = neon("base", [pair, P_BASE], [{"type": "text", "text": "Video A (before):"}, vid(A), {"type": "text", "text": "Video B (after):"}, vid(B), {"type": "text", "text": P_BASE}])
        o["a"] = {"raw": r["out"][:1500], "pred": lines(r["out"]), "s": round(up_s + r["s"], 2), "calls": 1}
        # arm (b) step 1: inventories in parallel
        with cf.ThreadPoolExecutor(2) as ex:
            ia, ib = ex.map(lambda x: neon("inv", [pair, x[0], P_INV], [vid(x[1]), {"type": "text", "text": P_INV}]), [("A", A), ("B", B)])
        inv = [[{"object": str(i.get("object", ""))[:80], "location": str(i.get("location", ""))[:120]} for i in (jparse(x["out"]) or []) if isinstance(i, dict)][:MAXI] for x in (ia, ib)]
        # step 2: Decision 1, one call per video
        qb = {}
        for i, it in enumerate(inv[0]):
            qb[f"p{i}"] = f"Is this object visible anywhere in this video? Object: {it['object']}. (Earlier it was: {it['location']}.)"
            qb[f"s{i}"] = f"Is this object visible in this video AND at this exact place? Object: {it['object']}. Place: {it['location']}. Answer no if it is somewhere else or not visible."
        qa = {f"p{i}": f"Is this object visible anywhere in this video? Object: {it['object']}." for i, it in enumerate(inv[1])}
        with cf.ThreadPoolExecutor(2) as ex: db, da = ex.map(lambda x: d1("chk", pair, x[0], x[1]), [("2", qb), ("1", qa)])
        # step 3: derive
        items = []
        for i, it in enumerate(inv[0]):
            p, s = db["out"][f"p{i}"], db["out"][f"s{i}"]
            v = "removed" if p["p"] < 0.5 else "moved" if s["p"] < 0.5 else "unchanged"
            items.append({"src": "A", **it, "p_present": p["p"], "p_same": s["p"], "conf": p["conf"] if v == "removed" else min(p["conf"], s["conf"]), "verdict": v})
        for i, it in enumerate(inv[1]):
            p = da["out"][f"p{i}"]
            items.append({"src": "B", **it, "p_present": p["p"], "conf": p["conf"], "verdict": "added" if p["p"] < 0.5 else "unchanged"})
        def preds(key):
            seen, out = set(), []
            for it in items:
                k = (it[key], it["object"].lower())
                if it[key] in TYPES and k not in seen: seen.add(k); out.append({"type": it[key], "object": f"{it['object']} ({it['location']})"})
            return out
        base_s = up_s + max(ia["s"], ib["s"]) + max(da["s"], db["s"])
        for it in items: it["verdict_rc"] = it["verdict"]
        o["b"] = {"n_inv": [len(inv[0]), len(inv[1])], "pred": preds("verdict"), "s": round(base_s, 2), "calls": 4,
                  "inv_s": [ia["s"], ib["s"]], "d1_s": [da["s"], db["s"]], "n_questions": len(qa) + len(qb)}
        # step 4: Neon recheck of the unsure items, one call per pair
        low = [(i, it) for i, it in enumerate(items) if it["conf"] < CONF]
        rc_s = 0.0
        if low:
            lst = "\n".join(f'{i}. [{"seen in A (before)" if it["src"] == "A" else "seen in B (after)"}] {it["object"]} - {it["location"]}' for i, it in low)
            pr = ("Video A is the scene BEFORE, video B the same scene AFTER, filmed again by hand. For each numbered object below decide what happened "
                  "to it between A and B: `removed` (in A, not in B), `added` (in B, not in A), `moved` (in both, different place) or `unchanged`. "
                  "Ignore camera viewpoint. Reply with only a JSON object mapping the number to one of those four words.\n" + lst)
            r = neon("recheck", [pair, pr], [{"type": "text", "text": "Video A (before):"}, vid(A), {"type": "text", "text": "Video B (after):"}, vid(B), {"type": "text", "text": pr}])
            rc_s = r["s"]; m = jparse(r["out"], "{") or {}
            for i, it in low:
                v = str(m.get(str(i), "")).lower().strip()
                if v in TYPES + ("unchanged",): it["verdict_rc"] = v
        o["b_rc"] = {"pred": preds("verdict_rc"), "s": round(base_s + rc_s, 2), "calls": 4 + bool(low), "n_rechecked": len(low),
                     "n_flipped": sum(it["verdict"] != it["verdict_rc"] for it in items)}
        o["items"] = items
        # scoring: same Carbon matcher for every arm, blind to which arm it is
        for arm in ("a", "b", "b_rc"):
            P, G = o[arm]["pred"], rec["gold"]; match = {}
            if P and G:
                pr = ("Match ground-truth scene changes to predicted changes. A predicted line matches a ground-truth change only if it names the same "
                      "physical object (synonyms and extra detail are fine; trailing _1, _2 number separate instances) AND has the same change type. "
                      "Each predicted line may be used for at most one ground-truth change. Reply with only a JSON object mapping every ground-truth id "
                      "to the index of its predicted line, or null if there is none.\n\nGround truth:\n"
                      + "\n".join(f'{g["id"]}: {g["type"]}: {g["label"]}' for g in G) + "\n\nPredicted:\n"
                      + "\n".join(f'{i}: {p["type"]}: {p["object"]}' for i, p in enumerate(P)))
                r = cached("carbon-match", [pair, pr], lambda: (gen.interactions.create(model="gemini-4-carbon", input=pr).output_text or "").strip())
                used = set()
                for g in G:
                    j = (jparse(r["out"], "{") or {}).get(g["id"])
                    if isinstance(j, int) and 0 <= j < len(P) and j not in used and P[j]["type"] == g["type"]: used.add(j); match[g["id"]] = j
            o[arm]["match"] = match
    except Exception as e:
        o["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(pair, o.get("error", "ok"), {a: (len(o[a]["pred"]), len(o[a].get("match", {})), o[a]["s"]) for a in ("a", "b", "b_rc") if a in o}, flush=True)
    return o

with cf.ThreadPoolExecutor(4) as ex: out = list(ex.map(run_pair, MAN))
ok = [o for o in out if "error" not in o]

def prf(tp, npred, ngold):
    p = tp / npred if npred else None; r = tp / ngold if ngold else None
    f = 2 * tp / (npred + ngold) if npred + ngold else None
    return {"tp": tp, "n_pred": npred, "n_gold": ngold, "precision": p, "recall": r, "f1": f}
def score(arm):
    res = {}
    for t in TYPES + ("overall",):
        keep = lambda x: t == "overall" or x["type"] == t
        tp = sum(1 for o in ok for g in o["gold"] if keep(g) and g["id"] in o[arm]["match"])
        res[t] = prf(tp, sum(1 for o in ok for p in o[arm]["pred"] if keep(p)), sum(1 for o in ok for g in o["gold"] if keep(g)))
    ls = [o[arm]["s"] for o in ok]
    res["latency_s"] = {"p50": statistics.median(ls), "max": max(ls), "note": "upload + model calls, parallel steps counted once; excludes ffmpeg re-encode and scoring"}
    res["calls_per_pair"] = statistics.mean(o[arm]["calls"] for o in ok)
    return res
S = {"n_pairs": len(ok), "n_gold": sum(len(o["gold"]) for o in ok), "errors": [(o["pair"], o["error"]) for o in out if "error" in o],
     "arms": {"a_baseline": score("a"), "b_system": score("b"), "b_system_recheck": score("b_rc")},
     "inventory_items": {"A": sum(o["b"]["n_inv"][0] for o in ok), "B": sum(o["b"]["n_inv"][1] for o in ok)},
     "d1_questions": sum(o["b"]["n_questions"] for o in ok), "d1_call_s_p50": statistics.median(s for o in ok for s in o["b"]["d1_s"] if s),
     "rechecked_items": sum(o["b_rc"]["n_rechecked"] for o in ok), "recheck_flips": sum(o["b_rc"]["n_flipped"] for o in ok),
     "new_calls_this_run": calls, "pairs": [o["pair"] for o in out]}
fa, fb = S["arms"]["a_baseline"]["overall"]["f1"] or 0, S["arms"]["b_system"]["overall"]["f1"] or 0
S["pass"] = fb >= fa + 0.10 and S["arms"]["b_system"]["latency_s"]["p50"] <= 60; S["kill"] = fb < fa
pathlib.Path("results/s4_beforeafter.json").write_text(json.dumps({"summary": S, "pairs": out}, indent=1))
print(json.dumps(S, indent=1))
