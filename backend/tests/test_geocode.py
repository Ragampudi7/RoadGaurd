"""
Place names from OpenStreetMap, without ever calling OpenStreetMap.

A local HTTP server stands in for Nominatim and answers in its jsonv2 format.
What matters: the label is built from the real address parts; a point is
looked up once however often it is asked for; and any failure yields no
address rather than a wrong one.
"""
import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.config import get_settings
from app.services import geocode_service
from app.services.geocode_service import format_label

NAGOLE = {
    "place_id": 1, "category": "highway", "type": "residential",
    "display_name": "Snehapuri Colony Main Road, Snehapuri Colony, Nagole, "
                    "Uppal, Hyderabad, Medchal-Malkajgiri, Telangana, 500068, India",
    "address": {
        "road": "Snehapuri Colony Main Road", "neighbourhood": "Snehapuri Colony",
        "suburb": "Nagole", "city": "Hyderabad", "state_district": "Medchal-Malkajgiri",
        "state": "Telangana", "postcode": "500068", "country": "India", "country_code": "in",
    },
}


class FakeNominatim(BaseHTTPRequestHandler):
    calls = []
    mode = "ok"

    def do_GET(self):  # noqa: N802
        q = parse_qs(urlparse(self.path).query)
        FakeNominatim.calls.append({"path": urlparse(self.path).path, "q": q,
                                    "ua": self.headers.get("User-Agent")})
        if FakeNominatim.mode == "500":
            self.send_response(500); self.end_headers(); return
        body = {"error": "Unable to geocode"} if FakeNominatim.mode == "sea" else NAGOLE
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def nominatim(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeNominatim)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeNominatim.calls, FakeNominatim.mode = [], "ok"
    settings = get_settings()
    monkeypatch.setattr(settings, "geocoding_enabled", True)
    monkeypatch.setattr(settings, "geocoder_url", "http://127.0.0.1:%d" % server.server_port)
    monkeypatch.setattr(settings, "geocoder_min_interval_seconds", 0.0)
    geocode_service.clear_cache()
    yield FakeNominatim
    server.shutdown()
    geocode_service.clear_cache()


# ----------------------------------------------------------------- labels --
def test_label_is_street_locality_city():
    assert format_label(NAGOLE["address"]) == "Snehapuri Colony Main Road, Nagole, Hyderabad"
    # A colony that is not part of the road name is kept.
    assert format_label({"road": "Road No. 9", "neighbourhood": "Snehapuri Colony",
                         "suburb": "Nagole", "city": "Hyderabad"}) == \
        "Road No. 9, Snehapuri Colony, Nagole, Hyderabad"


def test_label_skips_missing_parts_and_duplicates():
    assert format_label({"suburb": "Koti", "city_district": "Koti", "city": "Hyderabad"}) == "Koti, Hyderabad"
    assert format_label({"town": "Siddipet"}) == "Siddipet"
    assert format_label({}) is None


# ----------------------------------------------------------------- lookups --
def test_lookup_returns_label_and_full_address(nominatim):
    found = geocode_service.reverse(17.3737, 78.5550)
    assert found["label"].startswith("Snehapuri Colony Main Road")
    assert "500068" in found["full"] and found["source"] == "OpenStreetMap"
    call = nominatim.calls[0]
    assert call["path"] == "/reverse" and call["q"]["format"] == ["jsonv2"]
    assert call["q"]["accept-language"] == ["en"]
    # OpenStreetMap's policy requires an identifying User-Agent.
    assert call["ua"].startswith("RoadGuard-AI/")


def test_same_spot_is_looked_up_once(nominatim):
    geocode_service.reverse(17.37370, 78.55500)
    geocode_service.reverse(17.37372, 78.55503)   # ~4 m away: same address
    assert len(nominatim.calls) == 1


def test_no_address_for_unmapped_point(nominatim):
    nominatim.mode = "sea"
    assert geocode_service.reverse(10.0, 70.0) is None


def test_server_error_gives_none_not_a_guess(nominatim):
    nominatim.mode = "500"
    assert geocode_service.reverse(17.3737, 78.5550) is None
    # ...and the failure is not cached: the next attempt tries again.
    nominatim.mode = "ok"
    assert geocode_service.reverse(17.3737, 78.5550) is not None


def test_unreachable_geocoder_gives_none(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "geocoding_enabled", True)
    monkeypatch.setattr(settings, "geocoder_url", "http://127.0.0.1:9")   # nothing listens
    monkeypatch.setattr(settings, "geocoder_timeout_seconds", 1.0)
    monkeypatch.setattr(settings, "geocoder_min_interval_seconds", 0.0)
    geocode_service.clear_cache()
    assert geocode_service.reverse(17.3737, 78.5550) is None


def test_disabled_geocoding_never_calls_out(nominatim, monkeypatch):
    monkeypatch.setattr(get_settings(), "geocoding_enabled", False)
    assert geocode_service.reverse(17.3737, 78.5550) is None
    assert nominatim.calls == []


# ----------------------------------------------------------------- API --
def test_reverse_endpoint(client, nominatim):
    r = client.get("/geocode/reverse", params={"latitude": 17.3737, "longitude": 78.555})
    assert r.status_code == 200
    assert r.json()["label"].startswith("Snehapuri Colony Main Road")


def test_reverse_endpoint_without_a_name(client, nominatim):
    nominatim.mode = "sea"
    r = client.get("/geocode/reverse", params={"latitude": 10.0, "longitude": 70.0})
    assert r.status_code == 200 and r.json()["label"] is None


def test_reverse_endpoint_rejects_bad_coordinates(client):
    assert client.get("/geocode/reverse", params={"latitude": 95, "longitude": 78}).status_code == 422


def test_analysis_names_the_place_in_response_complaint_and_pdf(client, nominatim):
    from pypdf import PdfReader
    from tests.conftest import make_jpeg

    r = client.post("/analyze?include_image=false&include_pdf=true",
                    files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
                    data={"latitude": "17.3737", "longitude": "78.5550"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["location"]["address"].startswith("Snehapuri Colony Main Road")
    assert "Snehapuri Colony Main Road, Nagole, Hyderabad (latitude 17.373700" \
        in body["complaint_description"]
    pdf = PdfReader(io.BytesIO(base64.b64decode(body["report"]["data"])))
    text = " ".join(p.extract_text() for p in pdf.pages)
    assert "Snehapuri Colony Main Road" in text


def test_analysis_still_works_when_geocoding_fails(client, nominatim):
    from tests.conftest import make_jpeg
    nominatim.mode = "500"
    r = client.post("/analyze?include_image=false&include_pdf=false",
                    files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
                    data={"latitude": "17.3737", "longitude": "78.5550"})
    assert r.status_code == 200
    assert r.json()["location"]["address"] is None
    assert "latitude 17.373700, longitude 78.555000" in r.json()["complaint_description"]
