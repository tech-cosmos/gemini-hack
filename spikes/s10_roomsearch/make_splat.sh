#!/usr/bin/env bash
# Photos folder or video -> Gaussian splat .ply, offline on an Apple Silicon Mac.
# Poses: COLMAP 4.2 (brew, BSD-3) global_mapper on CPU. Training: Brush 0.3.0 (Apache-2.0, Metal/wgpu).
# Usage: make_splat.sh <photos_dir_or_video> <out.ply>
# Env: BRUSH (path to brush_app), STEPS (default 3000), MAXRES (default 800), FPS (video only, default 2),
#      WORK (scratch dir, default: mktemp).
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <photos_dir_or_video> <out.ply>" >&2; exit 2; }
IN=$1; OUT=$2
BRUSH=${BRUSH:-brush_app}; STEPS=${STEPS:-3000}; MAXRES=${MAXRES:-800}; FPS=${FPS:-2}
WORK=${WORK:-$(mktemp -d)}
command -v colmap >/dev/null || { echo "colmap missing: brew install colmap" >&2; exit 1; }
command -v "$BRUSH" >/dev/null || { echo "brush_app missing: set BRUSH=/path/to/brush_app" >&2; exit 1; }
mkdir -p "$WORK/images" "$WORK/sparse"
t0=$(date +%s); lap() { echo "[make_splat] $1: $(( $(date +%s) - t0 ))s" >&2; }

if [ -d "$IN" ]; then
  MATCHER=exhaustive_matcher   # unordered photos; fine up to ~150 images on CPU
  find "$IN" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -exec cp {} "$WORK/images/" \;
else
  MATCHER=sequential_matcher   # video frames are ordered
  ffmpeg -loglevel error -i "$IN" -vf "fps=$FPS,scale='min(1600,iw)':-2" -q:v 2 "$WORK/images/f_%04d.jpg"
fi
N=$(ls "$WORK/images" | wc -l | tr -d ' '); [ "$N" -ge 10 ] || { echo "need >=10 images, got $N" >&2; exit 1; }
lap "images ($N)"

colmap feature_extractor --log_level 1 --database_path "$WORK/db.db" --image_path "$WORK/images" \
  --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 1600
lap features
colmap $MATCHER --log_level 1 --database_path "$WORK/db.db" --FeatureMatching.use_gpu 0
lap matching
colmap global_mapper --log_level 1 --database_path "$WORK/db.db" --image_path "$WORK/images" --output_path "$WORK/sparse"
[ -d "$WORK/sparse/0" ] || { echo "pose estimation failed: no model in $WORK/sparse" >&2; exit 1; }
lap poses

"$BRUSH" "$WORK" --total-steps "$STEPS" --max-resolution "$MAXRES" --sh-degree 1 \
  --eval-every 1000000 --export-every "$STEPS" --export-path "$WORK/out" --export-name "splat.ply"
lap train
cp "$WORK/out/splat.ply" "$OUT"
echo "[make_splat] wrote $OUT ($(du -h "$OUT" | cut -f1)), work dir $WORK" >&2
