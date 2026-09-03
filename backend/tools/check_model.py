"""
Quick sanity check for your weights file.

    python tools/check_model.py [path/to/best.pt]

Prints where the model was loaded from, which classes it knows, and how long a
single CPU inference takes - the number that decides whether your deployment
feels usable.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.detection_service import RoadDefectDetector  # noqa: E402
from app.utils.logging_config import configure_logging  # noqa: E402


def main() -> int:
    configure_logging("INFO")
    settings = get_settings()
    if len(sys.argv) > 1:
        settings.model_path = sys.argv[1]

    print("Weights path : %s" % settings.model_file)
    print("Exists       : %s" % settings.model_file.is_file())
    print("Fallback     : %s" % settings.allow_pretrained_fallback)
    print("-" * 60)

    detector = RoadDefectDetector(settings)
    detector.load()

    if not detector.is_ready:
        print("FAILED to load a model.")
        print("Reason: %s" % (detector.load_error or "unknown"))
        return 1

    info = detector.info()
    print("Status       : %s" % info.status)
    print("Model        : %s" % info.name)
    print("Classes      : %s" % (", ".join(info.classes) or "(none reported)"))
    print("Road-defect model: %s" % info.is_road_defect_model)
    if not info.is_road_defect_model:
        print()
        print("!! This is the generic fallback model. Its classes are everyday")
        print("!! objects, not road defects. Put your trained best.pt in weights/.")

    sample = Image.new("RGB", (1280, 720), (110, 110, 112))
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        detections = detector.predict(sample)
        timings.append(time.perf_counter() - started)

    print("-" * 60)
    print("Inference (1280x720, CPU): %s" % ", ".join("%.2fs" % t for t in timings))
    print("Detections on a blank image: %d (0 is expected)" % len(detections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
