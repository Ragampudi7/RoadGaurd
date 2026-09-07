"""
Tests for the two report-layer bugs a test client cannot see on its own.

Both were found by driving a real browser against a running server, and both
are invisible to httpx: a browser sends a CORS preflight before a PATCH, and a
browser is what turns a File into base64. Keeping them here means the next
person to add a verb or an image field finds out from pytest instead.
"""

from __future__ import annotations

import base64
import hashlib

import pytest

from app.api.reports import ReportCreate, _decode_photo
from app.config import get_settings
from app.utils.errors import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageTypeError,
)

PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    b"IQAAAABJRU5ErkJggg=="
)


def _body(**kw) -> ReportCreate:
    base = dict(
        latitude=17.4948, longitude=78.3996,
        road_health_score=80.0, road_condition="Fair",
        defect_percentage=20.0, total_defects=1,
        risk_index=50.0, risk_level="Moderate", priority_tier="Priority-3",
    )
    base.update(kw)
    return ReportCreate(**base)


# --------------------------------------------------------------- preflight --
def test_preflight_allows_every_verb_the_api_actually_exposes(client):
    """
    A verb missing from allow_methods fails the browser's OPTIONS with a 400
    that never reaches a route, so every test-client call still passes while
    the feature is completely broken in a browser. That is exactly how the
    status endpoint shipped unusable.
    """
    settings = get_settings()
    origin = settings.cors_origins[0]

    for verb in ("GET", "POST", "PATCH", "DELETE"):
        response = client.options(
            "/reports",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": verb,
            },
        )
        assert response.status_code == 200, f"{verb} preflight was rejected"
        allowed = response.headers.get("access-control-allow-methods", "")
        assert verb in allowed, f"{verb} missing from {allowed!r}"


# ------------------------------------------------------------ photo decode --
def test_no_photo_is_allowed():
    assert _decode_photo(_body(), get_settings()) == (None, None)


def test_photo_round_trips():
    raw, mime = _decode_photo(
        _body(image_base64=base64.b64encode(PNG).decode(), image_mime="image/png"),
        get_settings(),
    )
    assert raw == PNG
    assert mime == "image/png"


def test_photo_must_match_the_hash_sent_with_it():
    """
    The report claims a SHA-256 that a reader can recompute from the evidence.
    If the bytes and the digest disagree, one of them is describing a different
    photograph, and storing either would put the wrong image behind a complaint.
    """
    with pytest.raises(InvalidImageError):
        _decode_photo(
            _body(
                image_base64=base64.b64encode(PNG).decode(),
                image_sha256=hashlib.sha256(b"a different file").hexdigest(),
            ),
            get_settings(),
        )


def test_matching_hash_is_accepted_case_insensitively():
    digest = hashlib.sha256(PNG).hexdigest().upper()
    raw, _ = _decode_photo(
        _body(image_base64=base64.b64encode(PNG).decode(), image_sha256=digest),
        get_settings(),
    )
    assert raw == PNG


def test_malformed_base64_is_rejected():
    with pytest.raises(InvalidImageError):
        _decode_photo(_body(image_base64="not base64 at all!!"), get_settings())


def test_empty_payload_is_rejected():
    with pytest.raises(InvalidImageError):
        _decode_photo(_body(image_base64=base64.b64encode(b"").decode() or "===="),
                      get_settings())


def test_oversized_photo_is_rejected():
    settings = get_settings()
    huge = b"\x00" * (settings.max_image_size_bytes + 1)
    with pytest.raises(ImageTooLargeError):
        _decode_photo(_body(image_base64=base64.b64encode(huge).decode()), settings)


def test_unsupported_mime_is_rejected():
    with pytest.raises(UnsupportedImageTypeError):
        _decode_photo(
            _body(image_base64=base64.b64encode(PNG).decode(), image_mime="image/gif"),
            get_settings(),
        )


# ------------------------------------------------------- weights provenance --
def test_weights_fingerprint_follows_the_file(tmp_path):
    """
    model_version is content-hashed rather than hand-maintained. A number
    someone has to remember to bump is a number that lies after the first
    retrain, and every stored report would then claim weights it never saw.
    """
    from app.services.detection_service import RoadDefectDetector

    class FakeModel:
        class model:
            yaml = {"yaml_file": "yolo11n.yaml"}

    weights = tmp_path / "best.pt"
    weights.write_bytes(b"pretend these are weights")
    first = RoadDefectDetector._fingerprint(weights, FakeModel(), str(weights))

    assert first.startswith("yolo11n-"), first
    assert len(first.split("-")[-1]) == 8
    # Same file, same answer.
    assert RoadDefectDetector._fingerprint(weights, FakeModel(), str(weights)) == first

    weights.write_bytes(b"pretend these are DIFFERENT weights")
    assert RoadDefectDetector._fingerprint(weights, FakeModel(), str(weights)) != first


def test_pretrained_fallback_is_labelled_as_such(tmp_path):
    from app.services.detection_service import RoadDefectDetector

    class FakeModel:
        class model:
            yaml = {"yaml_file": "yolo11n.yaml"}

    assert RoadDefectDetector._fingerprint(None, FakeModel(), "yolo11n.pt") == "yolo11n-pretrained"


# --------------------------------------------------------------- cors hosts --
@pytest.mark.parametrize(
    "given, expected",
    [
        # What Render's blueprint actually passes: a bare hostname.
        ("roadguard-ui.onrender.com", "https://roadguard-ui.onrender.com"),
        ("https://roadguard-ui.onrender.com/", "https://roadguard-ui.onrender.com"),
        ("http://localhost:5173", "http://localhost:5173"),
        ("localhost:5173", "http://localhost:5173"),
        ("127.0.0.1:3000", "http://127.0.0.1:3000"),
        ("*", "*"),
    ],
)
def test_cors_entries_become_real_origins(given, expected):
    """
    A bare hostname in the allow-list matches no Origin header the browser will
    ever send, so every request is refused by CORS and the server log shows a
    perfectly ordinary preflight. Adding the scheme here is what keeps that
    from being the first thing that happens after a deploy.
    """
    from app.config import _as_origin

    assert _as_origin(given) == expected


# ------------------------------------------------------------ who is staff --
@pytest.mark.parametrize(
    "allow_list, address, expected",
    [
        ("", "anyone@example.com", "citizen"),
        ("@ghmc.gov.in", "engineer@ghmc.gov.in", "official"),
        ("@ghmc.gov.in", "ENGINEER@GHMC.GOV.IN", "official"),
        ("@ghmc.gov.in", "engineer@ghmc.gov.in.evil.com", "citizen"),
        ("@ghmc.gov.in", "citizen@example.com", "citizen"),
        ("named@x.com", "named@x.com", "official"),
        ("named@x.com", "other@x.com", "citizen"),
        ("a@x.com, @y.gov", "someone@y.gov", "official"),
    ],
)
def test_official_allow_list(allow_list, address, expected):
    """
    The role comes from deployment configuration, never from the request.

    The third case is the one that matters: a suffix match on "@ghmc.gov.in"
    must not hand the role to anyone who can register
    ghmc.gov.in.attacker.com, so the comparison is on the end of the address
    and the entry carries its own leading "@".
    """
    from app.config import Settings

    assert Settings(official_emails=allow_list).role_for(address) == expected


# ----------------------------------------------------- who may change what --
def test_neither_role_can_do_the_other_s_job():
    """
    The two transition tables are the grievance workflow. A citizen files and
    withdraws; an authority acknowledges and resolves. Neither reaches into
    the other's half - a citizen self-resolving would make the status
    meaningless, and an official un-filing a complaint would erase one.
    """
    from app.api.reports import CITIZEN_TRANSITIONS, OFFICIAL_TRANSITIONS

    citizen_can = {t for targets in CITIZEN_TRANSITIONS.values() for t in targets}
    official_can = {t for targets in OFFICIAL_TRANSITIONS.values() for t in targets}

    assert "Acknowledged" not in citizen_can and "Resolved" not in citizen_can
    assert "Draft" not in official_can
    # A citizen may take a report back before the authority has touched it.
    assert CITIZEN_TRANSITIONS["Submitted"] == {"Draft"}
    # An authority may reopen a resolution that did not hold.
    assert "Acknowledged" in OFFICIAL_TRANSITIONS["Resolved"]
