"""Spike 12b (was 10b) after-the-fact latency probe (NOT the registered run). Needs locate.py's outputs first.
(1) the registered 40-image Neon prompt for q0, alone (no parallel load, no cache);
(2) the 40 grid views as ONE labelled contact sheet, all 10 queries, 2 at a time, scored with locate.py's rule.
Run: uv run --no-project --with google-genai==3.6.1 --with pillow python -I spikes/s10_roomsearch/locate_probe.py
Writes results/s10b_probe.json.
With arg "hydrogen" (spike 12c): Hydrogen instead of Neon, (1) runs on all 10 queries 10 at once (as the registered run);
writes results/s10b_hydrogen.json."""
import sys
import base64, io, json, os, pathlib, re, statistics, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from google import genai
from PIL import Image, ImageDraw

OUT, R = ROOT / ".context/s10b", json.load(open(ROOT / "results/s10b_locate.json"))
client = genai.Client(http_options={"api_version": "v1beta", "timeout": 180_000})
ADJ = {0: {1, 2, 3, 4}, 1: {0, 2, 3}, 2: {0, 1, 4}, 3: {0, 1, 4}, 4: {0, 2, 3}}
VIEWS = [{"file": f"v{pi}_{yaw:03d}.jpg", "pi": pi, "yaw": yaw} for pi in range(5) for yaw in range(0, 360, 45)]
def ang(a): return (a + 180) % 360 - 180
def jpg(b): return {"type": "image", "data": base64.b64encode(b).decode(), "mime_type": "image/jpeg"}
def small(f): bio = io.BytesIO(); Image.open(f).resize((480, 270)).save(bio, "JPEG", quality=80); return bio.getvalue()
ASK = ("Which reference view was taken from the closest spot AND facing the most similar direction to the QUERY? "
       "Then estimate how many degrees the QUERY camera is turned to the RIGHT of that view (negative = turned left), between -45 and 45. "
       'Reply with JSON only: {"nearest": <index 0-39>, "turn_right_deg": <number>}')  # same words as locate.py

HYD = sys.argv[1:] == ["hydrogen"]; MODEL = "gemini-4-hydrogen" if HYD else "gemini-4-neon"
def neon(parts):
    t = time.perf_counter(); r = client.interactions.create(model=MODEL, input=parts, generation_config={"thinking_level": "low"})
    return (r.output_text or "").strip(), round(time.perf_counter() - t, 2)

def score(q, text):
    m = re.search(r"\{.*\}", text, re.S); o = json.loads(m.group(0)) if m else None
    if not o or not isinstance(o.get("nearest"), int) or not 0 <= o["nearest"] < 40: return {"ok": False, "error": "unparseable"}
    v = VIEWS[o["nearest"]]; pred = (v["yaw"] - float(o.get("turn_right_deg") or 0)) % 360
    view_ok = (v["pi"] == q["true_pi"] and abs(ang(v["yaw"] - q["true_gyaw"])) <= 45) or (v["pi"] in ADJ[q["true_pi"]] and v["yaw"] == q["true_gyaw"])
    err = abs(ang(pred - q["yaw"]))
    return {"pred_view": v["file"], "heading_err": round(err, 1), "exact_pos": v["pi"] == q["true_pi"], "ok": view_ok and err <= 45}

res: dict = {"model": MODEL, "note": "spike 12c registered (hydrogen)" if HYD else "after the fact, not registered; thinking low; same scoring as locate.py"}
grid = [{"type": "text", "text": "Below are 40 reference views of one room, rendered from a 3D scan, labelled #0 to #39. Then a QUERY photo taken by a person somewhere in the same room."}]
for i, v in enumerate(VIEWS): grid += [{"type": "text", "text": f"#{i}"}, jpg(small(OUT / v["file"]))]
def grid_one(q):
    text, s = neon(grid + [{"type": "text", "text": "QUERY:"}, jpg((OUT / q["q"]).read_bytes()), {"type": "text", "text": ASK}])
    return {"q": q["q"], "s": s, "raw": text[:200], **score(q, text)}
if HYD:
    with ThreadPoolExecutor(10) as ex: res["grid40"] = list(ex.map(grid_one, R["queries"]))
    for r in res["grid40"]: print(r, flush=True)
    lat = [r["s"] for r in res["grid40"]]
    res["grid40_summary"] = {"pass_n": sum(r["ok"] for r in res["grid40"]), "n": 10, "p50_s": statistics.median(lat), "max_s": max(lat),
                             "exact_pos_n": sum(r.get("exact_pos", False) for r in res["grid40"])}
    res["grid40_summary"]["PASS"] = res["grid40_summary"]["pass_n"] >= 8 and res["grid40_summary"]["p50_s"] <= 10
    print("GRID40", res["grid40_summary"], flush=True)
else:
    res["solo_40img_q0"] = grid_one(R["queries"][0]); print("solo 40-image", res["solo_40img_q0"], flush=True)

sheet = Image.new("RGB", (8 * 320, 5 * 180)); d = ImageDraw.Draw(sheet)
for i, v in enumerate(VIEWS):
    x, y = i % 8 * 320, i // 8 * 180; sheet.paste(Image.open(OUT / v["file"]).resize((320, 180)), (x, y))
    d.rectangle((x, y, x + 46, y + 22), fill="black"); d.text((x + 4, y + 4), f"#{i}", fill="yellow", font_size=16)
bio = io.BytesIO(); sheet.save(bio, "JPEG", quality=85); sheet.save(OUT / "contact_labelled.jpg", quality=85)
pre = [{"type": "text", "text": "The first image is a contact sheet of 40 reference views of one room, rendered from a 3D scan, each labelled #0 to #39 in its top-left corner (row by row, 8 per row). The second image is a QUERY photo taken by a person somewhere in the same room."}, jpg(bio.getvalue())]
def one(q):
    text, s = neon(pre + [{"type": "text", "text": "QUERY:"}, jpg((OUT / q["q"]).read_bytes()), {"type": "text", "text": ASK}])
    return {"q": q["q"], "s": s, "raw": text[:200], **score(q, text)}
with ThreadPoolExecutor(2) as ex: res["sheet"] = list(ex.map(one, R["queries"]))
for r in res["sheet"]: print(r, flush=True)
lat = [r["s"] for r in res["sheet"]]
res["sheet_summary"] = {"pass_n": sum(r["ok"] for r in res["sheet"]), "n": 10, "p50_s": statistics.median(lat), "max_s": max(lat),
                        "exact_pos_n": sum(r.get("exact_pos", False) for r in res["sheet"])}
print("SHEET", res["sheet_summary"])
json.dump(res, open(ROOT / ("results/s10b_hydrogen.json" if HYD else "results/s10b_probe.json"), "w"), indent=1)
