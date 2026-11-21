"""Load a splat in viewer.html (headless Chrome) and save 4 renders: 3 from the splat centre + 1 at a COLMAP training
camera, so the last one can be compared with the real photo. Prints load time and per-render pixel stdev.
Run: uv run --no-project --with playwright --with numpy --with pillow python -I spikes/s10_roomsearch/render_check.py \
       <scene.ply> <colmap_sparse_0_dir> <out_dir>"""
import base64, functools, http.server, io, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

scene, sparse, out = (pathlib.Path(a).resolve() for a in sys.argv[1:4]); out.mkdir(parents=True, exist_ok=True)

# first registered camera from the COLMAP model (world-to-camera quaternion + translation)
txt = pathlib.Path(tempfile.mkdtemp())
subprocess.run(["colmap", "model_converter", "--input_path", sparse, "--output_path", txt, "--output_type", "TXT"], check=True, capture_output=True)
cam = next(l.split() for l in (txt / "cameras.txt").read_text().splitlines() if l and l[0] != "#")
W, H, fy = int(cam[2]), int(cam[3]), float(cam[4])  # SIMPLE_RADIAL/PINHOLE: focal is the first param
img = [l.split() for l in (txt / "images.txt").read_text().splitlines() if l and l[0] != "#"][0::2]
img = sorted(img, key=lambda r: r[9])[len(img) // 2]
qw, qx, qy, qz, tx, ty, tz = map(float, img[1:8])
R = np.array([[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
              [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
              [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])
C, f = -R.T @ np.array([tx, ty, tz]), R.T @ np.array([0, 0, 1.0])
flip = np.array([1, -1, -1.0])  # viewer rotates the splat 180 deg about X (y-down exports)
C, f = C * flip, f * flip
pitch, yaw = np.degrees(np.arcsin(f[1])), np.degrees(np.arctan2(-f[0], -f[2]))
vfov = float(np.degrees(2 * np.arctan(H / 2 / fy)))

serve = pathlib.Path(tempfile.mkdtemp())
shutil.copy(pathlib.Path(__file__).with_name("viewer.html"), serve / "viewer.html"); os.symlink(scene, serve / "scene.ply")
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): pass
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(serve)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
vw, vh = 960, round(960 * H / W)
url = f"http://127.0.0.1:{httpd.server_port}/viewer.html?url=scene.ply&w={vw}&h={vh}&fov={vfov:.2f}"

res = {"scene": scene.name, "train_image": img[9], "renders": []}
t0 = time.perf_counter()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": vw, "height": vh})
    pg.on("console", lambda m: m.type == "error" and print("console:", m.text[:200]))
    pg.on("pageerror", lambda e: print("pageerror:", str(e)[:300]))
    pg.goto(url); pg.wait_for_function("window.ready === true", timeout=int(os.environ.get("LOAD_TIMEOUT_MS", 300_000)))
    res["load_s"], res["info"] = round(time.perf_counter() - t0, 2), pg.evaluate("window.info")
    c = res["info"]["p50"]
    shots = [("centre_yaw000", c, 0, 0), ("centre_yaw120", c, 120, 0), ("centre_yaw240", c, 240, 0),
             ("train_cam_" + img[9].rsplit(".", 1)[0], C.tolist(), float(yaw), float(pitch))]
    for name, pos, y, pi in shots:
        data = base64.b64decode(pg.evaluate("([p, y, x]) => window.shot(p, y, x)", [pos, y, pi]).split(",", 1)[1])
        (out / f"{name}.jpg").write_bytes(data)
        sd = float(np.asarray(Image.open(io.BytesIO(data)).convert("L")).std())
        res["renders"].append({"file": f"{name}.jpg", "pos": [round(v, 3) for v in pos], "yaw": round(y, 1), "pitch": round(pi, 1), "gray_stdev": round(sd, 1)})
    b.close()
(out / "render_check.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
