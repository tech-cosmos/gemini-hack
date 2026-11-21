# Venue photos → splat for Room Search (spike 12)

Two paths. Both end in a `.ply` (or `.spz`) that `viewer.html` loads.

## A. Phone app (fastest for a person): Scaniverse
Free, processes on the phone, works offline, exports PLY and SPZ (App Store listing; Niantic's SPZ page).
1. Install **Scaniverse** (iOS App Store or Google Play).
2. New scan → choose **Splat** mode. Walk the room slowly in one loop, phone at chest height, then a second loop
   pointing a bit down at tables. Keep 1-2 minutes; avoid pointing at windows/bright lights for long.
3. Let it **Process on device** (a few minutes on a recent iPhone).
4. Open the scan → **Share/Export** → **PLY** (or **SPZ**, about 10× smaller) → AirDrop to the Mac.
5. `uv run --no-project --with playwright --with numpy --with pillow python -I spikes/s10_roomsearch/render_check.py <file.ply> ...`
   needs a COLMAP model for its 4th render; for an app export, use `spike.py` directly (it only needs the splat).
Not verified by us today: exact menu names and time per scan (no phone run yet). Polycam and Luma also make splats,
but both process in the cloud; Scaniverse is the only one of the three that is on-device.

## B. Laptop (Mac, offline): COLMAP poses + Brush training
Tools (all reused, none written here):
- **COLMAP 4.2.1** (BSD-3-Clause), `brew install colmap`. CPU only on Mac (no CUDA). Its `global_mapper` (GLOMAP,
  now merged into COLMAP) does the poses.
- **Brush 0.3.0** (Apache-2.0, Arthur Brussee), trains splats on Metal through wgpu. Prebuilt binary:
  ```
  curl -L -o brush.tar.xz https://github.com/ArthurBrussee/brush/releases/download/v0.3.0/brush-app-aarch64-apple-darwin.tar.xz
  tar xf brush.tar.xz && xattr -dr com.apple.quarantine brush-app-aarch64-apple-darwin
  ```
- Skipped: OpenSplat (AGPL-3.0, needs a source build with libtorch/MPS).

Run (photos folder, or a phone video which is cut to 2 fps frames):
```
BRUSH=/path/to/brush_app STEPS=3000 spikes/s10_roomsearch/make_splat.sh <photos_dir_or_video.mp4> out.ply
```
Knobs: `STEPS` (training length), `MAXRES` (training image size, default 800), `FPS` (video frames per second).

### Timed run (2026-11-21, Apple M3, 16 GB)
Input: 63 photos (every 5th of Mip-NeRF 360 `room`, 1557×1038, from the HF mirror `nvs-bench/mipnerf360`; used for
timing only, not committed). Command: `STEPS=3000 MAXRES=800 make_splat.sh <63 photos> room.ply`, log in the run.

| Stage | Wall time |
|---|---|
| COLMAP features (CPU, max 1600 px) | 19 s |
| COLMAP exhaustive matching (CPU, 1953 pairs) | 62 s |
| COLMAP global_mapper | 21 s (63/63 registered, 0.52 px reprojection) |
| **Poses total** | **102 s** |
| Brush training, 3000 steps, 800 px, SH 1 | 117 s |
| **End to end** | **219 s (3.7 min)** |
| Export | `.ply`, 46,756 splats, 4.3 MB |
| Load in `viewer.html` (headless Chrome, Playwright `channel="chrome"`) | 2.05 s, render works: **yes** |

Renders in `.context/splat_capture/` (`render_check.py`, stats in `render_check.json`, side-by-side in `contact.jpg`):
the render at training camera DSCF4822 matches the real photo (sofa, armchair, rug, slippers readable; slight
offset and a blurred foreground plant). The 3 renders from the splat centre are mostly blur: the Mip-NeRF room was shot
facing inward, so nothing was photographed from the middle looking out. **For Room Search, capture must include the
views we render**: stand at 3-5 spots in the room and turn a full circle at each, plus one loop of the walls.
Budget left under 8 min: ~4 min, so `STEPS=7000` should still fit (not run).

Found on the way: `viewer.html` as committed (4c34584) failed to load any splat: Spark 2.4 imports `three/addons/…`,
which the import map didn't map. Fixed with one import-map line in this commit.
Warnings seen: global_mapper wants focal-length priors (EXIF); the HF images had none and it still worked. Video
frames have no EXIF either: if a video run fails to register, use photos, or run `colmap view_graph_calibrator` first.

### Capture tips (for Dan walking the venue)
- Video is easiest: 60-90 s, slow walk, overlap everything; `make_splat.sh` cuts 2 fps → ~120-180 frames.
- Lock exposure if the camera app allows; no zoom; avoid people walking through the frame.
