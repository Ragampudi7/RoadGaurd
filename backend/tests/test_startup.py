"""
A cold start must not make login wait for the AI model.

Loading torch and the YOLO weights takes about a minute on a free Render
instance. The server now accepts requests at once and loads the model on a
background thread; only /analyze waits for it.
"""
import sys
import threading
import time
import types

import pytest

from app.config import get_settings
from app.services import detection_service
from app.services.detection_service import RoadDefectDetector
from tests.conftest import StubDetector, make_jpeg


# ------------------------------------------------- the real detector class --
@pytest.fixture
def slow_ultralytics(monkeypatch):
    """A stand-in `ultralytics` whose YOLO takes `delay` seconds to load."""
    gate = {"delay": 0.6, "loads": 0}

    class FakeYOLO:
        names = {0: "pothole", 1: "crack"}

        def __init__(self, target):
            gate["loads"] += 1
            time.sleep(gate["delay"])

        def predict(self, *args, **kwargs):
            return []

    module = types.ModuleType("ultralytics")
    module.YOLO = FakeYOLO
    monkeypatch.setitem(sys.modules, "ultralytics", module)
    return gate


def test_background_load_returns_immediately(slow_ultralytics):
    detector = RoadDefectDetector()
    started = time.perf_counter()
    detector.start_background_load()
    assert time.perf_counter() - started < 0.2
    assert detector.is_loading and not detector.is_ready

    assert detector.wait_until_loaded(timeout=5) is True
    assert detector.is_ready and not detector.is_loading
    assert detector.info().classes == ["pothole", "crack"]


def test_wait_gives_up_after_timeout(slow_ultralytics):
    slow_ultralytics["delay"] = 1.5
    detector = RoadDefectDetector()
    detector.start_background_load()
    assert detector.wait_until_loaded(timeout=0.1) is False
    assert detector.is_loading
    assert detector.wait_until_loaded(timeout=5) is True


def test_starting_twice_loads_once(slow_ultralytics):
    detector = RoadDefectDetector()
    detector.start_background_load()
    detector.start_background_load()
    assert detector.wait_until_loaded(timeout=5)
    detector.start_background_load()   # already loaded: no-op
    assert slow_ultralytics["loads"] == 1


# ------------------------------------------------------------- the API --
class LoadingStub(StubDetector):
    """Ready only once `release` is set - like a model mid-load."""

    def __init__(self, release: threading.Event, never: bool = False):
        super().__init__(ready=True)
        self.release, self.never = release, never

    @property
    def is_loading(self):
        return not self.release.is_set()

    @property
    def is_ready(self):
        return self.release.is_set()

    def wait_until_loaded(self, timeout):
        if not self.never:
            self.release.set()
        else:
            self.release.wait(timeout)
        return self.is_ready


@pytest.fixture
def loading_client():
    from fastapi.testclient import TestClient
    from app.main import app

    def make(never=False):
        stub = LoadingStub(threading.Event(), never=never)
        detection_service.set_detector(stub)
        return TestClient(app), stub
    yield make
    detection_service.set_detector(None)


def _analyze(client):
    return client.post("/analyze?include_pdf=false&include_image=false",
                       files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
                       data={"latitude": "17.4948", "longitude": "78.3996"})


def test_health_says_starting_while_model_loads(loading_client):
    client, _ = loading_client()
    with client:
        body = client.get("/health").json()
    assert body["status"] == "starting"
    assert body["model_loading"] is True and body["model_loaded"] is False


def test_analyze_waits_for_the_model_then_succeeds(loading_client):
    client, _ = loading_client()
    with client:
        r = _analyze(client)
    assert r.status_code == 200, r.text


def test_analyze_gives_a_clear_503_if_the_model_takes_too_long(loading_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "model_wait_seconds", 0.1)
    client, _ = loading_client(never=True)
    with client:
        r = _analyze(client)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "model_loading"
    assert "try again" in r.json()["error"]["message"]
