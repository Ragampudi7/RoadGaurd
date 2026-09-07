# RoadGuard API.
#
# A Dockerfile rather than Railway's automatic Python detection, for one
# reason that dominates everything else: the default PyPI wheels for torch
# pull roughly 2.5 GB of CUDA libraries. This service runs inference on CPU
# and cannot use a single byte of that, but it would still be downloaded on
# every build, stored in the image, and paid for. Installing from PyTorch's
# CPU index first means the later `-r requirements.txt` finds torch already
# satisfied and leaves it alone.

FROM python:3.11-slim

# Runtime system libraries. opencv-python-headless avoids the OpenGL stack
# that the normal opencv build needs, but Pillow and OpenCV still want glib,
# and torch's threading layer needs libgomp.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies before source: this layer is the slow one (several minutes)
# and Docker will reuse it on every deploy that does not touch requirements.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.5.0,<3.0.0" "torchvision>=0.20.0,<1.0.0" \
 && pip install --no-cache-dir -r requirements.txt \
 # Ultralytics depends on opencv-python, which needs libGL - a system library
 # slim images do not ship, and installing it just to satisfy an import the
 # app never uses is 200 MB wasted. Swap in the headless build: same cv2
 # module, no GUI bindings.
 && (pip uninstall -y opencv-python opencv-contrib-python || true) \
 && pip install --no-cache-dir --force-reinstall --no-deps \
        "opencv-python-headless>=4.10.0,<5.0.0"

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Ultralytics writes a settings file and a font cache at import time and
    # will crash if it cannot. /tmp is writable; the working directory is not
    # guaranteed to be.
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    # Torch spawns one thread per core by default and then contends with
    # itself on a shared-CPU instance. One thread is measurably faster here.
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MODEL_PATH=weights/best.pt \
    # weights/best.pt is committed, so the generic COCO model must never
    # quietly stand in for it: those detections are not road defects, but the
    # report built from them is still addressed to a municipal body.
    ALLOW_PRETRAINED_FALLBACK=false

# Railway injects PORT and expects the process to bind 0.0.0.0. One worker
# only - a YOLO process holds most of a small instance's memory, and a second
# worker buys out-of-memory restarts rather than throughput.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 65"]
