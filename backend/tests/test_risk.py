"""Tests for the road-risk model."""

from __future__ import annotations

import hashlib

import pytest

from app.config import get_settings
from app.models.schemas import Detection
from app.services import risk_service
from tests.conftest import make_jpeg


def _detection(name: str = "pothole", confidence: float = 0.9,
               area_percentage: float = 5.0, area: int = 50000, index: int = 1) -> Detection:
    return Detection(
        id=index, class_id=0, class_name=name, confidence=confidence,
        bbox=[0, 0, 100, 100], area=area, area_percentage=area_percentage,
    )


# --- class hazard weights --------------------------------------------------


def test_class_weight_matches_as_a_substring():
    assert risk_service.class_weight("pothole") == 1.0
    assert risk_service.class_weight("D40_Pothole") == 1.0
    assert risk_service.class_weight("alligator_crack") == 0.65
    assert risk_service.class_weight("longitudinal crack") == 0.55


def test_unknown_class_gets_the_default_weight():
    from app.config import DEFAULT_CLASS_WEIGHT

    assert risk_service.class_weight("mystery_defect") == DEFAULT_CLASS_WEIGHT


def test_potholes_are_weighted_above_cracks():
    assert risk_service.class_weight("pothole") > risk_service.class_weight("crack")


# --- per-defect severity ---------------------------------------------------


@pytest.mark.parametrize("area_pct,expected", [
    (12.0, "Critical"), (8.0, "Critical"),
    (7.99, "High"), (3.0, "High"),
    (2.99, "Medium"), (1.0, "Medium"),
    (0.99, "Minor"), (0.0, "Minor"),
])
def test_severity_bands(area_pct, expected):
    assert risk_service.severity_for(area_pct, confidence=0.9)[0] == expected


def test_low_confidence_demotes_one_band():
    assert risk_service.severity_for(12.0, confidence=0.9)[0] == "Critical"
    assert risk_service.severity_for(12.0, confidence=0.30)[0] == "High"


def test_low_confidence_cannot_demote_below_minor():
    assert risk_service.severity_for(0.1, confidence=0.05)[0] == "Minor"


def test_recommended_action_is_class_and_severity_specific():
    pothole = risk_service.recommended_action("pothole", "Critical")
    crack = risk_service.recommended_action("alligator_crack", "Critical")
    assert pothole != crack
    assert "asphalt" in pothole.lower() or "excavate" in pothole.lower()
    assert risk_service.recommended_action("unknown_thing", "Minor")


def test_enrich_detections_fills_every_field():
    detections = risk_service.enrich_detections([_detection()])
    detection = detections[0]
    assert detection.severity in ("Minor", "Medium", "High", "Critical")
    assert detection.severity_rank >= 0
    assert detection.severity_colour.startswith("#")
    assert detection.recommended_action


# --- the index -------------------------------------------------------------


def test_no_detections_means_no_risk():
    assessment = risk_service.assess_risk([], 0.0, get_settings())
    assert assessment.risk_index == 0.0
    assert assessment.risk_level == "Low"
    assert assessment.priority_tier == "Routine"
    assert assessment.max_severity == "None"
    assert assessment.dominant_defect is None
    assert "no defects" in assessment.summary.lower()


def test_more_damage_produces_more_risk():
    settings = get_settings()
    light = risk_service.assess_risk(
        risk_service.enrich_detections([_detection(area_percentage=1.0, area=10000)]),
        1.0, settings)
    heavy = risk_service.assess_risk(
        risk_service.enrich_detections([
            _detection(area_percentage=12.0, area=120000, index=i) for i in range(1, 6)
        ]), 40.0, settings)
    assert heavy.risk_index > light.risk_index


def test_potholes_outrank_cracks_at_identical_geometry():
    settings = get_settings()
    common = dict(area_percentage=6.0, area=60000, confidence=0.9)
    potholes = risk_service.assess_risk(
        risk_service.enrich_detections([_detection("pothole", **common)]), 6.0, settings)
    cracks = risk_service.assess_risk(
        risk_service.enrich_detections([_detection("crack", **common)]), 6.0, settings)
    assert potholes.risk_index > cracks.risk_index
    assert potholes.hazard_factor > cracks.hazard_factor


def test_low_confidence_softens_the_index():
    settings = get_settings()
    common = dict(area_percentage=6.0, area=60000)
    confident = risk_service.assess_risk(
        risk_service.enrich_detections([_detection(confidence=0.95, **common)]), 6.0, settings)
    unsure = risk_service.assess_risk(
        risk_service.enrich_detections([_detection(confidence=0.30, **common)]), 6.0, settings)
    assert unsure.risk_index < confident.risk_index
    assert unsure.confidence_factor == 0.5     # floored, never below


def test_index_is_bounded_and_components_are_normalised():
    settings = get_settings()
    detections = risk_service.enrich_detections(
        [_detection(area_percentage=60.0, area=600000, index=i) for i in range(1, 30)])
    assessment = risk_service.assess_risk(detections, 100.0, settings)
    assert 0.0 <= assessment.risk_index <= 100.0
    assert assessment.risk_level == "Critical"
    assert assessment.priority_tier == "Priority-1"
    assert sum(c.weight for c in assessment.components) == pytest.approx(1.0, abs=0.01)
    assert all(0.0 <= c.score <= 100.0 for c in assessment.components)


def test_dominant_defect_is_the_biggest_area_not_the_biggest_count():
    settings = get_settings()
    detections = risk_service.enrich_detections([
        _detection("crack", area=10000, area_percentage=1.0, index=1),
        _detection("crack", area=10000, area_percentage=1.0, index=2),
        _detection("pothole", area=90000, area_percentage=9.0, index=3),
    ])
    assert risk_service.assess_risk(detections, 11.0, settings).dominant_defect == "pothole"


@pytest.mark.parametrize("index,level,tier", [
    (100.0, "Critical", "Priority-1"), (75.0, "Critical", "Priority-1"),
    (74.99, "High", "Priority-2"), (50.0, "High", "Priority-2"),
    (49.99, "Moderate", "Priority-3"), (25.0, "Moderate", "Priority-3"),
    (24.99, "Low", "Routine"), (0.0, "Low", "Routine"),
])
def test_risk_bands(index, level, tier):
    got_level, _colour, got_tier, _window = risk_service.classify_risk(index)
    assert (got_level, got_tier) == (level, tier)


# --- through the API -------------------------------------------------------


def test_analyze_returns_a_full_risk_block(client):
    body = client.post(
        "/analyze",
        files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
        data={"latitude": "17.4948", "longitude": "78.3996"},
    ).json()

    risk = body["risk"]
    assert 0.0 <= risk["risk_index"] <= 100.0
    assert risk["risk_level"] in ("Low", "Moderate", "High", "Critical")
    assert risk["priority_tier"]
    assert risk["response_window"]
    assert [c["name"] for c in risk["components"]] == ["Extent", "Worst defect", "Density"]
    assert all(c["value_display"] for c in risk["components"])
    assert risk["max_severity"] in ("Minor", "Medium", "High", "Critical")


def test_every_detection_carries_severity_and_an_action(client):
    body = client.post(
        "/analyze",
        files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
        data={"latitude": "17.4948", "longitude": "78.3996"},
    ).json()
    assert body["detections"]
    for detection in body["detections"]:
        assert detection["severity"] in ("Minor", "Medium", "High", "Critical")
        assert detection["recommended_action"]
        assert detection["severity_colour"].startswith("#")


def test_evidence_hash_matches_the_uploaded_bytes(client):
    payload = make_jpeg()
    body = client.post(
        "/analyze",
        files={"image": ("road.jpg", payload, "image/jpeg")},
        data={"latitude": "17.4948", "longitude": "78.3996"},
    ).json()
    assert body["image"]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_one_crop_is_returned_per_detection(client):
    body = client.post(
        "/analyze",
        files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
        data={"latitude": "17.4948", "longitude": "78.3996"},
    ).json()
    assert len(body["defect_crops"]) == len(body["detections"])
    for crop in body["defect_crops"]:
        assert crop["mime_type"] == "image/jpeg"
        assert crop["size_bytes"] > 0


def test_complaint_statement_mentions_the_risk_tier(client):
    body = client.post(
        "/analyze",
        files={"image": ("road.jpg", make_jpeg(), "image/jpeg")},
        data={"latitude": "17.4948", "longitude": "78.3996"},
    ).json()
    assert body["risk"]["priority_tier"] in body["complaint_description"]
