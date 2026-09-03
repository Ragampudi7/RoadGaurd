"""
Scoring service - all of the project's mathematics in one place.

The chain, exactly as specified:

    box_area            = (x2 - x1) * (y2 - y1)
    image_area          = width * height
    total_defect_area   = sum(box_area for every detection)
    defect_percentage   = total_defect_area / image_area * 100
    road_health_score   = max(0, 100 - defect_percentage)

Overlapping boxes
-----------------
Version 1 follows the specification and simply SUMS the box areas.  Two
potholes whose boxes overlap therefore have their shared pixels counted
twice, which slightly over-states the damage (and, with many overlapping
boxes, can even push the summed percentage above 100%).

Because that is a real limitation worth being able to discuss, the exact
overlap-free area is *also* computed on every request (``union``) and both
figures are returned in ``area_breakdown``.  Set ``AREA_METHOD=union`` in the
environment to score on the overlap-corrected figure instead - no code change
required.
"""

from __future__ import annotations

from bisect import bisect_left
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from app.config import ROAD_CONDITION_BANDS, Settings, get_settings
from app.models.schemas import AreaBreakdown, Detection


def box_area(x1: int, y1: int, x2: int, y2: int) -> int:
    """Area of a single bounding box in pixels (never negative)."""
    return max(0, x2 - x1) * max(0, y2 - y1)


def summed_area(boxes: Sequence[Dict[str, Any]]) -> int:
    """Total area with overlaps counted once per box (the specification)."""
    return sum(box_area(b["x1"], b["y1"], b["x2"], b["y2"]) for b in boxes)


def union_area(boxes: Sequence[Dict[str, Any]]) -> int:
    """
    Exact area of the union of all boxes - every damaged pixel counted once.

    Uses coordinate compression: the distinct x and y edges cut the image into
    a small grid (at most 2N x 2N cells for N boxes), each cell is either
    fully inside a box or fully outside it, so marking cells and summing their
    real areas gives the exact union without ever allocating a pixel mask.
    """
    if not boxes:
        return 0

    xs = sorted({b["x1"] for b in boxes} | {b["x2"] for b in boxes})
    ys = sorted({b["y1"] for b in boxes} | {b["y2"] for b in boxes})
    if len(xs) < 2 or len(ys) < 2:
        return 0

    covered = np.zeros((len(ys) - 1, len(xs) - 1), dtype=bool)
    for b in boxes:
        if b["x2"] <= b["x1"] or b["y2"] <= b["y1"]:
            continue
        col_start = bisect_left(xs, b["x1"])
        col_end = bisect_left(xs, b["x2"])
        row_start = bisect_left(ys, b["y1"])
        row_end = bisect_left(ys, b["y2"])
        covered[row_start:row_end, col_start:col_end] = True

    cell_widths = np.diff(np.asarray(xs, dtype=np.int64))
    cell_heights = np.diff(np.asarray(ys, dtype=np.int64))
    cell_areas = cell_heights[:, None] * cell_widths[None, :]
    return int(cell_areas[covered].sum())


def classify_road_condition(score: float) -> Tuple[str, str]:
    """
    Map a health score to (label, hex colour) using the project-defined bands
    in ``app/config.py``.  These bands are our own convention, not an official
    government standard.
    """
    for lower_bound, label, colour in ROAD_CONDITION_BANDS:
        if score >= lower_bound:
            return label, colour
    # Defensive: the last band starts at 0.0, so this is unreachable.
    return ROAD_CONDITION_BANDS[-1][1], ROAD_CONDITION_BANDS[-1][2]


def percentage(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def score_image(
    raw_detections: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    settings: Settings = None,
) -> Dict[str, Any]:
    """
    Turn raw detections into the full scored result.

    Returns a dict with typed ``detections``, an ``AreaBreakdown``, the
    percentage, the score, the condition label/colour and per-class counts.
    """
    settings = settings or get_settings()
    image_area = max(1, image_width * image_height)

    detections: List[Detection] = []
    defect_counts: Dict[str, int] = {}

    for index, raw in enumerate(raw_detections, start=1):
        area = box_area(raw["x1"], raw["y1"], raw["x2"], raw["y2"])
        detections.append(
            Detection(
                id=index,
                class_id=int(raw["class_id"]),
                class_name=str(raw["class_name"]),
                confidence=round(float(raw["confidence"]), 4),
                bbox=[raw["x1"], raw["y1"], raw["x2"], raw["y2"]],
                area=area,
                area_percentage=round(percentage(area, image_area), 2),
            )
        )
        name = str(raw["class_name"])
        defect_counts[name] = defect_counts.get(name, 0) + 1

    total_summed = summed_area(raw_detections)
    total_union = union_area(raw_detections)

    summed_pct = percentage(total_summed, image_area)
    union_pct = percentage(total_union, image_area)

    chosen_pct = summed_pct if settings.area_method == "sum" else union_pct
    # A percentage above 100 is only possible with the summed method; clamp it
    # so the reported figure and the score always stay in a sane range.
    defect_percentage = round(min(chosen_pct, 100.0), 2)
    health_score = round(max(0.0, 100.0 - defect_percentage), 2)
    condition, colour = classify_road_condition(health_score)

    breakdown = AreaBreakdown(
        method=settings.area_method,
        summed_area_pixels=total_summed,
        union_area_pixels=total_union,
        summed_percentage=round(summed_pct, 2),
        union_percentage=round(union_pct, 2),
        overlap_detected=total_summed > total_union,
    )

    return {
        "detections": detections,
        "defect_counts": dict(sorted(defect_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "total_defects": len(detections),
        "area_breakdown": breakdown,
        "defect_percentage": defect_percentage,
        "road_health_score": health_score,
        "road_condition": condition,
        "condition_colour": colour,
        "image_area": image_area,
    }


def build_complaint_description(
    score: float,
    condition: str,
    defect_counts: Dict[str, int],
    total_defects: int,
    defect_percentage: float,
    latitude: float,
    longitude: float,
    authority: str,
    is_road_defect_model: bool = True,
    risk: Any = None,
) -> str:
    """
    Compose the grievance paragraph used in the PDF and the API response.

    ``risk`` is the optional :class:`RiskAssessment`; when present the statement
    also carries the modelled risk band and the suggested grievance tier, which
    is what tells a municipal desk how to queue the complaint.
    """
    if not is_road_defect_model:
        return (
            "This assessment was generated in demonstration mode using a generic "
            "pretrained object-detection model, not a road-defect model. The findings "
            "below are for software testing only and must not be submitted as a "
            "grievance."
        )

    if total_defects == 0:
        return (
            "An automated assessment of the road surface at latitude %.6f, longitude "
            "%.6f did not detect any surface defects in the submitted photograph. The "
            "computed Road Health Score is %.2f out of 100, indicating a %s condition. "
            "No repair action is requested at this location at present."
            % (latitude, longitude, score, condition.upper())
        )

    if defect_counts:
        parts = [
            "%d %s%s" % (count, name.replace("_", " "), "s" if count != 1 else "")
            for name, count in defect_counts.items()
        ]
        if len(parts) == 1:
            summary = parts[0]
        else:
            summary = ", ".join(parts[:-1]) + " and " + parts[-1]
    else:
        summary = "%d road defect(s)" % total_defects

    risk_sentence = ""
    if risk is not None:
        risk_sentence = (
            " The estimated Road Risk Index is %.1f out of 100, placing this location in "
            "the %s risk band; the suggested grievance tier is %s (%s). The most serious "
            "individual defect is rated %s severity."
            % (risk.risk_index, risk.risk_level.upper(), risk.priority_tier,
               risk.response_window.lower(), risk.max_severity.lower())
        )

    return (
        "Road surface defects were detected in a photograph captured at latitude "
        "%.6f, longitude %.6f. Automated analysis identified %s, covering approximately "
        "%.2f%% of the photographed road surface. The computed Road Health Score is "
        "%.2f out of 100, indicating a %s road condition.%s The %s is kindly requested "
        "to inspect the location and undertake the necessary repair work."
        % (
            latitude,
            longitude,
            summary,
            defect_percentage,
            score,
            condition.upper(),
            risk_sentence,
            authority,
        )
    )
