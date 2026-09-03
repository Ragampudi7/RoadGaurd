"""
Shared test fixtures.

The suite runs without torch or Ultralytics installed: a stub detector is
injected in place of the real one, which keeps the tests fast and makes them
runnable on any machine (including CI) while still exercising the *whole*
pipeline - validation, scoring, annotation and PDF generation.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

import pytest
from PIL import Image

from app.config import get_settings
from app.models.schemas import ModelInfo
from app.services import detection_service


class StubDetector:
    """Stand-in for RoadDefectDetector that returns scripted detections."""

    def __init__(self, detections: List[Dict[str, Any]] = None, ready: bool = True) -> None:
        self.settings = get_settings()
        self._detections = detections if detections is not None else []
        self._ready = ready
        self.status = detection_service.STATUS_TRAINED if ready else detection_service.STATUS_UNAVAILABLE
        self.load_error = None if ready else "stub: no model"

    def load(self) -> None:
        return None

    def unload(self) -> None:
        return None

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def is_road_defect_model(self) -> bool:
        return self._ready

    def info(self) -> ModelInfo:
        return ModelInfo(
            status=self.status,
            name="best.pt" if self._ready else "none",
            classes=["pothole", "crack"],
            device="cpu",
            confidence_threshold=self.settings.confidence_threshold,
            iou_threshold=self.settings.iou_threshold,
            is_road_defect_model=self._ready,
        )

    def warnings(self) -> List[str]:
        return []

    def predict(self, image) -> List[Dict[str, Any]]:
        if not self._ready:
            from app.utils.errors import ModelUnavailableError

            raise ModelUnavailableError()
        return list(self._detections)


def make_jpeg(width: int = 800, height: int = 600, colour=(90, 90, 90)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


SAMPLE_DETECTIONS: List[Dict[str, Any]] = [
    {"class_id": 0, "class_name": "pothole", "confidence": 0.91,
     "x1": 100, "y1": 120, "x2": 300, "y2": 280},
    {"class_id": 0, "class_name": "pothole", "confidence": 0.64,
     "x1": 400, "y1": 300, "x2": 500, "y2": 380},
    {"class_id": 1, "class_name": "crack", "confidence": 0.47,
     "x1": 550, "y1": 60, "x2": 780, "y2": 140},
]


@pytest.fixture
def stub_detector():
    detector = StubDetector(SAMPLE_DETECTIONS)
    detection_service.set_detector(detector)
    yield detector
    detection_service.set_detector(None)


@pytest.fixture
def empty_detector():
    detector = StubDetector([])
    detection_service.set_detector(detector)
    yield detector
    detection_service.set_detector(None)


@pytest.fixture
def broken_detector():
    detector = StubDetector([], ready=False)
    detection_service.set_detector(detector)
    yield detector
    detection_service.set_detector(None)


@pytest.fixture
def client(stub_detector):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()
