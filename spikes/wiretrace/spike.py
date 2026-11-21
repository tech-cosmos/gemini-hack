"""Wire Trace spike: does asking Decision 1 about every node pair recover diagram edges better than one call?

Data: Knossos test split (HF WayneGuo0011/Knossos, data CC-BY-4.0), the "difficult" level of two domains:
10 food webs (directed arrows, some bidirectional) and 10 circuits (undirected wires). First 10 by sample_id.
Both arms get the true node names, so this measures edges only (the paper: node F1 is about 97, edges are
the gap).
Arm A (baseline): Neon, one call: image + node names -> JSON edge list.
Arm B: Decision 1, one call per diagram: image + one yes/no per node pair (ordered pairs for food webs,
unordered for circuits); keep p > 0.5.
Score: edge F1 per diagram, averaged (food web pairs ordered, bidirectional = both orders; circuit pairs unordered).
Pass mark (docs/IDEAS.md, written before the run): A edge F1 < 85 and B beats A by >= 5 points.

Run: uv run --no-project --with google-genai==3.6.1 --with pandas --with pyarrow python -I spikes/wiretrace/spike.py
"""
import base64
import json
import pathlib
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations, permutations

import pandas as pd
from google import genai
from google.genai import types

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
HF = "https://huggingface.co/datasets/WayneGuo0011/Knossos/resolve/main/data/test/"
FILES = {"foodweb": "foodweb-02-difficult-000.parquet", "circuit": "circuit-02-difficult-000.parquet"}
BASELINE = "gemini-4-neon"  # Carbon took >5 min on one diagram in the smoke test
DECIDER = "models/gemini-decision-1"
PER_DOMAIN = 10

gen = genai.Client()
dec = genai.Client(http_options={"api_version": "v1beta"})  # decisions live on v1beta


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


def diagrams():
    out = []
    for domain, f in FILES.items():
        d = pd.read_parquet(fetch(HF + f, CACHE / f)).sort_values("sample_id").head(PER_DOMAIN)
        for r in d.itertuples():
            names = {n["id"]: n["name"] for n in r.nodes}
            truth = set()
            for e in r.edges:
                a, b = names[e["source"]], names[e["target"]]
                if domain == "circuit":
                    truth.add(frozenset((a, b)))
                else:
                    truth.add((a, b))
                    if e["type"] == "bidirectional":
                        truth.add((b, a))
            out.append({"id": r.sample_id, "domain": domain, "png": r.image["bytes"],
                        "names": list(names.values()), "truth": truth})
    return out


def key_of(domain, a, b):
    return frozenset((a, b)) if domain == "circuit" else (a, b)


def baseline(d):
    def run():
        kind = ("Each edge is a wire or line directly connecting two components; direction does not matter."
                if d["domain"] == "circuit" else
                "Each edge is an arrow; give source (tail) and target (arrowhead). A double-headed arrow is two edges.")
        prompt = (f"This diagram has these nodes: {json.dumps(d['names'])}. List every edge drawn in the diagram. "
                  f"{kind} Use the node names exactly as given. Return only JSON: "
                  '[{"source": "...", "target": "..."}]')
        text = retry(lambda: gen.models.generate_content(
            model=BASELINE, contents=[types.Part.from_bytes(data=d["png"], mime_type="image/png"), prompt]).text) or ""
        m = re.search(r"\[.*\]", text, re.S)
        try:
            edges = json.loads(m.group(0)) if m else []
        except json.JSONDecodeError:
            edges = []
        return [[e["source"], e["target"]] for e in edges if isinstance(e, dict) and "source" in e and "target" in e]
    return cached(f"A_{d['id']}", run)


def pairwise(d):
    def run():
        names = d["names"]
        pairs = list(combinations(names, 2)) if d["domain"] == "circuit" else list(permutations(names, 2))
        def q(a, b):
            if d["domain"] == "circuit":
                return f'Is there a wire or line drawn directly connecting "{a}" and "{b}" (not through another component)?'
            return f'Is there an arrow drawn from "{a}" to "{b}", with its arrowhead pointing at "{b}"?'
        r = retry(lambda: dec.decisions.create(model=DECIDER, input=[
            {"type": "image", "data": base64.b64encode(d["png"]).decode(), "mime_type": "image/png"},
            {"type": "text", "text": f"A {'circuit' if d['domain'] == 'circuit' else 'food web'} diagram."}],
            questions={f"q{i}": {"type": "noul", "instructions": q(a, b)} for i, (a, b) in enumerate(pairs)}))
        assert r is not None and r.answers, "empty Decision 1 reply"
        return [[a, b, r.answers[f"q{i}"].noul] for i, (a, b) in enumerate(pairs)]
    return cached(f"B_{d['id']}", run)


def f1(pred, truth):
    tp = len(pred & truth)
    if not pred and not truth:
        return 1.0
    p = tp / len(pred) if pred else 0.0
    r = tp / len(truth) if truth else 0.0
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def main():
    ds = diagrams()
    with ThreadPoolExecutor(6) as ex:
        a = list(ex.map(baseline, ds))
        b = list(ex.map(pairwise, ds))
    rows = []
    for d, ea, eb in zip(ds, a, b):
        pa = {key_of(d["domain"], s, t) for s, t in ea}
        pb = {key_of(d["domain"], s, t) for s, t, p in eb if p > 0.5}
        rows.append({"id": d["id"], "domain": d["domain"], "nodes": len(d["names"]), "edges": len(d["truth"]),
                     "A_f1": round(100 * f1(pa, d["truth"]), 1), "B_f1": round(100 * f1(pb, d["truth"]), 1),
                     "A_pred": len(pa), "B_pred": len(pb), "B_questions": len(eb)})
    def mean(k, dom=None):
        v = [r[k] for r in rows if dom in (None, r["domain"])]
        return round(sum(v) / len(v), 1)
    res = {"n": len(rows),
           "A_neon_one_call_edge_f1": {"all": mean("A_f1"), "foodweb": mean("A_f1", "foodweb"), "circuit": mean("A_f1", "circuit")},
           "B_decision_pairwise_edge_f1": {"all": mean("B_f1"), "foodweb": mean("B_f1", "foodweb"), "circuit": mean("B_f1", "circuit")}}
    (HERE / "per_diagram.json").write_text(json.dumps(rows, indent=1))
    (HERE / "result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
