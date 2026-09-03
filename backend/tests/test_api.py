"""End-to-end tests for the HTTP API, using the stub detector."""

from __future__ import annotations

import base64
import io

from PIL import Image

from tests.conftest import make_jpeg


def test_root_reports_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "running" in body["message"]


def test_health_reports_the_loaded_model(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model"]["is_road_defect_model"] is True


def _post(client, **kwargs):
    files = {"image": ("road.jpg", make_jpeg(), "image/jpeg")}
    data = {"latitude": "17.4948", "longitude": "78.3996"}
    files.update(kwargs.pop("files", {}))
    data.update(kwargs.pop("data", {}))
    return client.post("/analyze", files=files, data=data, **kwargs)


def test_analyze_happy_path(client):
    response = _post(client)
    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["total_defects"] == 3
    assert body["defect_counts"] == {"pothole": 2, "crack": 1}
    assert len(body["detections"]) == 3

    # 200x160 + 100x80 + 230x80 = 32000 + 8000 + 18400 = 58400 px of 480000
    assert body["defect_percentage"] == 12.17
    assert body["road_health_score"] == 87.83
    assert body["road_condition"] == "Fair"

    assert body["location"] == {
        "latitude": 17.4948,
        "longitude": 78.3996,
        "maps_url": "https://www.google.com/maps/search/?api=1&query=17.494800,78.399600",
    }
    assert body["image"]["width"] == 800 and body["image"]["height"] == 600
    assert body["request_id"].startswith("RHA-")
    assert body["addressed_to"]


def test_analyze_returns_a_real_pdf(client):
    body = _post(client).json()
    pdf = base64.b64decode(body["report"]["data"])
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert body["report"]["mime_type"] == "application/pdf"
    assert body["report"]["size_bytes"] == len(pdf)
    assert body["report"]["filename"].endswith(".pdf")


def test_analyze_returns_a_real_annotated_jpeg(client):
    body = _post(client).json()
    jpeg = base64.b64decode(body["annotated_image"]["data"])
    assert Image.open(io.BytesIO(jpeg)).format == "JPEG"
    assert body["annotated_image"]["size_bytes"] == len(jpeg)


def test_payloads_can_be_switched_off(client):
    response = client.post(
        "/analyze?include_pdf=false&include_image=false",
        files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
        data={"latitude": "17.4", "longitude": "78.4"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["report"] is None
    assert body["annotated_image"] is None


def test_clean_road_scores_100(client, empty_detector):
    body = _post(client).json()
    assert body["total_defects"] == 0
    assert body["road_health_score"] == 100.0
    assert body["road_condition"] == "Good"


def test_missing_image_is_a_readable_422(client):
    response = client.post("/analyze", data={"latitude": "17.4", "longitude": "78.4"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "image file is required" in body["error"]["message"]


def test_missing_coordinates_are_reported(client):
    response = client.post("/analyze", files={"image": ("r.jpg", make_jpeg(), "image/jpeg")})
    assert response.status_code == 422
    assert "latitude" in response.json()["error"]["message"].lower()


def test_out_of_range_latitude_is_rejected(client):
    response = _post(client, data={"latitude": "120.0"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "coordinates_invalid"


def test_out_of_range_longitude_is_rejected(client):
    response = _post(client, data={"longitude": "-200.0"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "coordinates_invalid"


def test_unsupported_file_type_is_rejected(client):
    response = _post(client, files={"image": ("notes.pdf", b"%PDF-1.4", "application/pdf")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "image_type_unsupported"


def test_corrupt_image_is_rejected(client):
    response = _post(client, files={"image": ("road.jpg", b"not an image at all", "image/jpeg")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "image_invalid"


def test_empty_upload_is_rejected(client):
    response = _post(client, files={"image": ("road.jpg", b"", "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "image_empty"


def test_oversized_image_is_rejected(client):
    from app.config import get_settings

    limit = get_settings().max_image_size_bytes
    payload = b"\xff\xd8" + b"0" * (limit + 1024)
    response = _post(client, files={"image": ("huge.jpg", payload, "image/jpeg")})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "image_too_large"


def test_model_unavailable_returns_503(client, broken_detector):
    response = _post(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"


def test_no_stack_trace_ever_reaches_the_client(client):
    response = _post(client, files={"image": ("road.jpg", b"broken", "image/jpeg")})
    text = response.text.lower()
    assert "traceback" not in text
    assert "/app/" not in text
    assert ".py" not in text


def test_cors_headers_are_present_for_the_configured_frontend(client):
    response = client.options(
        "/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
