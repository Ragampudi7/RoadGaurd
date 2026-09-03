"""Tests for the scoring mathematics - the heart of the project."""

from __future__ import annotations

from app.config import get_settings
from app.services.scoring_service import (
    box_area,
    build_complaint_description,
    classify_road_condition,
    percentage,
    score_image,
    summed_area,
    union_area,
)


def test_box_area_is_width_times_height():
    assert box_area(100, 120, 300, 280) == 200 * 160


def test_box_area_never_negative():
    assert box_area(300, 280, 100, 120) == 0


def test_summed_area_double_counts_overlap():
    boxes = [
        {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
        {"x1": 50, "y1": 50, "x2": 150, "y2": 150},
    ]
    assert summed_area(boxes) == 20000          # 10000 + 10000
    assert union_area(boxes) == 17500           # 20000 - 2500 shared pixels


def test_union_equals_sum_when_boxes_are_disjoint():
    boxes = [
        {"x1": 0, "y1": 0, "x2": 10, "y2": 10},
        {"x1": 50, "y1": 50, "x2": 60, "y2": 60},
    ]
    assert union_area(boxes) == summed_area(boxes) == 200


def test_union_of_no_boxes_is_zero():
    assert union_area([]) == 0
    assert summed_area([]) == 0


def test_classification_bands():
    assert classify_road_condition(100.0)[0] == "Good"
    assert classify_road_condition(90.0)[0] == "Good"
    assert classify_road_condition(89.99)[0] == "Fair"
    assert classify_road_condition(70.0)[0] == "Fair"
    assert classify_road_condition(69.99)[0] == "Poor"
    assert classify_road_condition(40.0)[0] == "Poor"
    assert classify_road_condition(39.99)[0] == "Dangerous"
    assert classify_road_condition(0.0)[0] == "Dangerous"


def test_percentage_handles_zero_area():
    assert percentage(10, 0) == 0.0


def test_score_image_end_to_end_maths():
    # One 200x100 box in a 1000x1000 image -> 20000 / 1000000 = 2.00%
    detections = [{"class_id": 0, "class_name": "pothole", "confidence": 0.9,
                   "x1": 0, "y1": 0, "x2": 200, "y2": 100}]
    result = score_image(detections, 1000, 1000, get_settings())

    assert result["defect_percentage"] == 2.0
    assert result["road_health_score"] == 98.0
    assert result["road_condition"] == "Good"
    assert result["total_defects"] == 1
    assert result["defect_counts"] == {"pothole": 1}
    assert result["detections"][0].area == 20000
    assert result["detections"][0].id == 1


def test_score_image_with_no_detections_is_a_perfect_score():
    result = score_image([], 640, 480, get_settings())
    assert result["defect_percentage"] == 0.0
    assert result["road_health_score"] == 100.0
    assert result["road_condition"] == "Good"
    assert result["area_breakdown"].overlap_detected is False


def test_overlap_is_reported_in_the_breakdown():
    detections = [
        {"class_id": 0, "class_name": "pothole", "confidence": 0.9,
         "x1": 0, "y1": 0, "x2": 100, "y2": 100},
        {"class_id": 0, "class_name": "pothole", "confidence": 0.8,
         "x1": 50, "y1": 50, "x2": 150, "y2": 150},
    ]
    breakdown = score_image(detections, 1000, 1000, get_settings())["area_breakdown"]
    assert breakdown.overlap_detected is True
    assert breakdown.summed_percentage > breakdown.union_percentage


def test_percentage_is_clamped_to_100():
    # Twelve full-frame boxes would sum to 1200% without the clamp.
    detections = [
        {"class_id": 0, "class_name": "pothole", "confidence": 0.9,
         "x1": 0, "y1": 0, "x2": 100, "y2": 100}
        for _ in range(12)
    ]
    result = score_image(detections, 100, 100, get_settings())
    assert result["defect_percentage"] == 100.0
    assert result["road_health_score"] == 0.0
    assert result["road_condition"] == "Dangerous"


def test_complaint_description_mentions_the_key_facts():
    text = build_complaint_description(
        score=61.5, condition="Poor", defect_counts={"pothole": 3, "crack": 2},
        total_defects=5, defect_percentage=38.5,
        latitude=17.4948, longitude=78.3996, authority="GHMC",
    )
    assert "17.494800" in text and "78.399600" in text
    assert "3 pothole" in text and "2 crack" in text
    assert "61.50" in text and "POOR" in text and "GHMC" in text


def test_complaint_description_when_nothing_is_detected():
    text = build_complaint_description(
        score=100.0, condition="Good", defect_counts={}, total_defects=0,
        defect_percentage=0.0, latitude=17.0, longitude=78.0, authority="GHMC",
    )
    assert "did not detect any surface defects" in text


def test_complaint_description_is_honest_in_demo_mode():
    text = build_complaint_description(
        score=90.0, condition="Good", defect_counts={"person": 1}, total_defects=1,
        defect_percentage=10.0, latitude=17.0, longitude=78.0, authority="GHMC",
        is_road_defect_model=False,
    )
    assert "demonstration mode" in text
    assert "must not be submitted" in text
