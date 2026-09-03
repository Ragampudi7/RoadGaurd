"""
YOLO detection service.

Responsibilities
----------------
* Load exactly one YOLO model per process, at application startup.
* Run CPU inference on an in-memory image.
* Return plain Python dictionaries - nothing in this module leaks Ultralytics
  or Torch types into the rest of the codebase.

Model resolution order
----------------------
1. ``MODEL_PATH`` (default ``weights/best.pt``) - your trained road-defect
   model.  This is the only mode whose output is meaningful for a real
   grievance report.
2. If that file does not exist and ``ALLOW_PRETRAINED_FALLBACK=true``, a
   generic pretrained model (``yolov8n.pt``) is downloaded and used instead.
   It detects COCO objects - person, car, bottle - and **cannot** detect
   potholes or cracks.  Every response produced in this mode is flagged, and
   the PDF is watermarked, so nobody mistakes it for a real assessment.
3. Otherwise the API starts but ``/analyze`` answers 503 until weights exist.

The Ultralytics import is deliberately done *inside* ``load()`` so that this
module (and the unit tests) can be imported on a machine that has no torch
installed.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from PIL import Image

from app.config import Settings, get_settings
from app.models.schemas import ModelInfo
from app.utils.errors import InferenceError, ModelUnavailableError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

STATUS_TRAINED = "trained"
STATUS_FALLBACK = "pretrained_fallback"
STATUS_UNAVAILABLE = "unavailable"

FALLBACK_WARNING = (
    "No trained road-defect model was found, so a generic pretrained model was "
    "used. The objects listed below are NOT road defects and this report must "
    "not be submitted to a municipal authority. Place your trained best.pt in "
    "the weights/ folder to get real results."
)


class RoadDefectDetector:
    """Thin, framework-agnostic wrapper around an Ultralytics YOLO model."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._model: Any = None
        self._status: str = STATUS_UNAVAILABLE
        self._model_name: str = "none"
        self._class_names: List[str] = []
        self._load_error: Optional[str] = None
        # Ultralytics models are not thread-safe; serialise access.
        self._lock = threading.Lock()

    # -- lifecycle --------------------------------------------------------

    def load(self) -> None:
        """Load the model once. Never raises - failures are recorded instead."""
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO  # imported lazily, see module docstring
        except Exception as exc:  # pragma: no cover - depends on environment
            self._load_error = "Ultralytics/torch is not installed: %s" % exc
            logger.error(self._load_error)
            return

        weights_path = self.settings.model_file
        started = time.perf_counter()

        if weights_path.is_file():
            target, status = str(weights_path), STATUS_TRAINED
            logger.info("Loading trained road-defect weights from %s", weights_path)
        elif self.settings.allow_pretrained_fallback:
            target, status = self.settings.fallback_model_name, STATUS_FALLBACK
            logger.warning(
                "%s not found - falling back to the generic pretrained model '%s'. "
                "Detections will NOT be road defects.",
                weights_path,
                target,
            )
        else:
            self._load_error = (
                "Weights file %s not found and ALLOW_PRETRAINED_FALLBACK is disabled."
                % weights_path
            )
            logger.error(self._load_error)
            return

        try:
            model = YOLO(target)
            # A tiny warm-up pass. The first inference in a fresh process is
            # several times slower than the rest; doing it at startup means the
            # first citizen upload is not the one that pays for it.
            model.predict(
                Image.new("RGB", (320, 320), color=(128, 128, 128)),
                imgsz=self.settings.inference_image_size,
                device="cpu",
                verbose=False,
            )
        except Exception as exc:
            self._load_error = "Failed to load model '%s': %s" % (target, exc)
            logger.exception(self._load_error)
            self._model = None
            return

        names = getattr(model, "names", {}) or {}
        if isinstance(names, dict):
            self._class_names = [str(names[key]) for key in sorted(names)]
        else:  # pragma: no cover - older ultralytics returned a list
            self._class_names = [str(name) for name in names]

        self._model = model
        self._status = status
        self._model_name = weights_path.name if status == STATUS_TRAINED else target
        self._load_error = None
        logger.info(
            "Model ready in %.2fs | status=%s | classes=%s",
            time.perf_counter() - started,
            status,
            self._class_names or "(none reported)",
        )

    def unload(self) -> None:
        self._model = None
        self._status = STATUS_UNAVAILABLE

    # -- introspection ----------------------------------------------------

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_road_defect_model(self) -> bool:
        return self._status == STATUS_TRAINED

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def info(self) -> ModelInfo:
        return ModelInfo(
            status=self._status,
            name=self._model_name,
            classes=self._class_names,
            device="cpu",
            confidence_threshold=self.settings.confidence_threshold,
            iou_threshold=self.settings.iou_threshold,
            is_road_defect_model=self.is_road_defect_model,
        )

    def warnings(self) -> List[str]:
        return [FALLBACK_WARNING] if self._status == STATUS_FALLBACK else []

    # -- inference --------------------------------------------------------

    def predict(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Run detection on a PIL image and return raw detections.

        Each item: ``{class_id, class_name, confidence, x1, y1, x2, y2}`` with
        coordinates in the ORIGINAL image's pixel space (Ultralytics rescales
        them back for us after its internal letterboxing).
        """
        if self._model is None:
            # The real reason (which may contain a server filesystem path) goes
            # to the log only; the client gets the generic, safe message.
            logger.error("Inference requested but no model is loaded: %s", self._load_error)
            raise ModelUnavailableError()

        width, height = image.size
        try:
            with self._lock:
                results = self._model.predict(
                    image,  # a PIL image keeps channel order unambiguous
                    imgsz=self.settings.inference_image_size,
                    conf=self.settings.confidence_threshold,
                    iou=self.settings.iou_threshold,
                    max_det=self.settings.max_detections,
                    device="cpu",
                    verbose=False,
                )
        except Exception as exc:
            logger.exception("YOLO inference failed: %s", exc)
            raise InferenceError() from exc

        if not results:
            return []

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        names = getattr(result, "names", None) or {}
        detections: List[Dict[str, Any]] = []

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            # Clamp to the image so a box that spills over the edge cannot
            # inflate the damaged-area calculation.
            x1 = int(max(0, min(round(xyxy[0]), width)))
            y1 = int(max(0, min(round(xyxy[1]), height)))
            x2 = int(max(0, min(round(xyxy[2]), width)))
            y2 = int(max(0, min(round(xyxy[3]), height)))
            if x2 <= x1 or y2 <= y1:
                continue  # degenerate box, nothing to measure

            detections.append(
                {
                    "class_id": class_id,
                    "class_name": str(names.get(class_id, "class_%d" % class_id)),
                    "confidence": confidence,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                }
            )

        detections.sort(key=lambda item: item["confidence"], reverse=True)
        return detections


# --- process-wide singleton -------------------------------------------------

_detector: Optional[RoadDefectDetector] = None


def get_detector() -> RoadDefectDetector:
    """Return the one detector instance for this process."""
    global _detector
    if _detector is None:
        _detector = RoadDefectDetector()
    return _detector


def set_detector(detector: Optional[RoadDefectDetector]) -> None:
    """Replace the singleton. Used by the test-suite to inject a stub."""
    global _detector
    _detector = detector
