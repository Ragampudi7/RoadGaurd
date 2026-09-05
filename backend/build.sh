#!/usr/bin/env bash
# Render build script. Referenced from render.yaml.
# Also usable locally on Linux:  bash build.sh
set -o errexit

python -m pip install --upgrade pip

# 1. CPU-only PyTorch FIRST.
#    On Linux the default PyPI wheels drag in ~2.5 GB of CUDA libraries that a
#    free Render instance cannot hold and a CPU-only service cannot use.
#    Installing from PyTorch's CPU index first means the later `-r requirements.txt`
#    (and Ultralytics) find torch already satisfied and leave it alone.
if [ "$(uname -s)" = "Linux" ]; then
  pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5.0,<3.0.0" "torchvision>=0.20.0,<1.0.0"
fi

# 2. Everything else.
pip install -r requirements.txt

# 3. Ultralytics depends on opencv-python, which needs libGL - a system library
#    slim Linux images do not ship. Swap it for the headless build (same cv2
#    module, no GUI bindings) to avoid "ImportError: libGL.so.1" at startup.
pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
pip install --force-reinstall --no-deps "opencv-python-headless>=4.10.0,<5.0.0"

# 4. Pre-download the fallback model during the build rather than on the first
#    request, so a cold start never blocks on a network download.
if [ "${ALLOW_PRETRAINED_FALLBACK:-true}" = "true" ] && [ ! -f "${MODEL_PATH:-weights/best.pt}" ]; then
  echo "Pre-downloading fallback model ${FALLBACK_MODEL_NAME:-yolo11n.pt} ..."
  python -c "from ultralytics import YOLO; YOLO('${FALLBACK_MODEL_NAME:-yolo11n.pt}')" || true
fi

echo "Build complete."
