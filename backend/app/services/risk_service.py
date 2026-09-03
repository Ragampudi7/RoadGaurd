"""
Road-risk estimation.

The health score answers *"how much of this photograph is damaged?"*. That is
not the question a municipal desk needs answered, which is *"how urgently
should someone be sent?"* - so this module computes a separate **Road Risk
Index** (0-100, higher is worse) along with a per-defect severity band and a
suggested remediation.

    raw        = 0.50*extent + 0.30*worst_defect + 0.20*density   # each 0-100
    hazard     = area-weighted mean class weight (pothole 1.00 ... patch 0.45)
    confidence = mean detection confidence, floored at 0.50
    risk_index = min(100, raw * hazard * confidence)

``hazard`` is why a pothole outranks a hairline crack of the same size;
``confidence`` is why an unsure model produces a correspondingly softer claim.

Every band, weight, full scale and class weight is project-defined and lives in
``app/config.py``. None of it comes from IRC, MoRTH, GHMC or any other official
standard, and the report states that on its face. "Severity" here is an
*extent* proxy - how much of the frame a defect occupies - because a photograph
carries no depth and no scale.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from app.config import (
    DEFAULT_CLASS_WEIGHT,
    DEFECT_CLASS_WEIGHTS,
    DEFECT_SEVERITY_BANDS,
    LOW_CONFIDENCE_DOWNGRADE_BELOW,
    RECOMMENDED_ACTIONS,
    RISK_BANDS,
    SEVERITY_ORDER,
    Settings,
    get_settings,
)
from app.models.schemas import Detection, RiskAssessment, RiskComponent

CONFIDENCE_FLOOR = 0.50


# ---------------------------------------------------------------------------
# Per-defect
# ---------------------------------------------------------------------------


def class_weight(class_name: str) -> float:
    """
    How hazardous this defect class is to a road user, relative to a pothole.

    Keys are matched as substrings in insertion order, so "D40_Pothole" scores
    as a pothole and "alligator_crack" matches "alligator" before "crack".
    """
    name = (class_name or "").lower()
    for key, weight in DEFECT_CLASS_WEIGHTS.items():
        if key in name:
            return weight
    return DEFAULT_CLASS_WEIGHT


def severity_for(area_percentage: float, confidence: float) -> Tuple[str, int, str]:
    """
    Band one defect by the share of the frame its box covers.

    A detection the model is unsure about is demoted one band, so a large
    low-confidence blob cannot manufacture a "Critical" finding. Returns
    ``(label, rank, hex colour)`` where rank 0 = Minor .. 3 = Critical.
    """
    label = DEFECT_SEVERITY_BANDS[-1][1]
    for lower_bound, band_label, _colour in DEFECT_SEVERITY_BANDS:
        if area_percentage >= lower_bound:
            label = band_label
            break

    rank = SEVERITY_ORDER.index(label)
    if confidence < LOW_CONFIDENCE_DOWNGRADE_BELOW:
        rank = max(0, rank - 1)
    label = SEVERITY_ORDER[rank]

    colour = next(c for _b, l, c in DEFECT_SEVERITY_BANDS if l == label)
    return label, rank, colour


def recommended_action(class_name: str, severity: str) -> str:
    """
    A suggested repair for this class at this severity.

    Offered to the engineering wing as a starting point - the report labels it
    as such, and it is not an engineering directive.
    """
    name = (class_name or "").lower()
    family = "default"
    for key in RECOMMENDED_ACTIONS:
        if key != "default" and key in name:
            family = key
            break
    table = RECOMMENDED_ACTIONS.get(family, RECOMMENDED_ACTIONS["default"])
    return table.get(severity, RECOMMENDED_ACTIONS["default"].get(severity, ""))


def enrich_detections(detections: Sequence[Detection]) -> List[Detection]:
    """Attach severity and a remediation suggestion, preserving detection order."""
    enriched: List[Detection] = []
    for det in detections:
        label, rank, colour = severity_for(det.area_percentage, det.confidence)
        enriched.append(
            det.model_copy(
                update={
                    "severity": label,
                    "severity_rank": rank,
                    "severity_colour": colour,
                    "recommended_action": recommended_action(det.class_name, label),
                }
            )
        )
    return enriched


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------


def classify_risk(index: float) -> Tuple[str, str, str, str]:
    """``(level, hex colour, grievance tier, response window)`` for a risk index."""
    for lower_bound, level, colour, tier, window in RISK_BANDS:
        if index >= lower_bound:
            return level, colour, tier, window
    last = RISK_BANDS[-1]
    return last[1], last[2], last[3], last[4]


def _component(name: str, value: float, unit: str, display: str,
               full_scale: float, weight: float) -> RiskComponent:
    return RiskComponent(
        name=name,
        value=round(value, 2),
        unit=unit,
        value_display=display,
        full_scale=float(full_scale),
        score=round(min(100.0, max(0.0, value) / float(full_scale) * 100.0), 2),
        weight=round(weight, 4),
    )


def _summary(index: float, level: str, tier: str, window: str, max_severity: str,
             count: int, defect_percentage: float) -> str:
    return (
        "Modelled risk is %s (%.1f / 100). The worst single defect is rated %s, "
        "%d defect%s cover about %.2f%% of the photographed surface, and the "
        "suggested grievance tier is %s - %s."
        % (level.lower(), index, max_severity.lower(), count,
           "" if count == 1 else "s", defect_percentage, tier, window.lower())
    )


def assess_risk(
    detections: Sequence[Detection],
    defect_percentage: float,
    settings: Optional[Settings] = None,
) -> RiskAssessment:
    """Combine extent, worst-defect size and density into one 0-100 index."""
    settings = settings or get_settings()
    count = len(detections)

    if count == 0:
        level, colour, tier, window = classify_risk(0.0)
        return RiskAssessment(
            risk_index=0.0,
            risk_level=level,
            risk_colour=colour,
            priority_tier=tier,
            response_window=window,
            components=[
                _component("Extent", 0.0, "of the frame damaged",
                           "0.00% of the frame damaged",
                           settings.risk_extent_full_scale, 0.5),
                _component("Worst defect", 0.0, "of the frame in one box",
                           "no defects detected",
                           settings.risk_severity_full_scale, 0.3),
                _component("Density", 0.0, "defects detected",
                           "0 defects detected",
                           float(settings.risk_density_full_scale), 0.2),
            ],
            hazard_factor=0.0,
            confidence_factor=0.0,
            max_severity="None",
            dominant_defect=None,
            summary="No defects were detected in this photograph, so no road risk "
                    "is modelled for this location.",
        )

    # --- weights, normalised so they always sum to 1 -----------------------
    raw_weights = (
        max(0.0, settings.risk_weight_extent),
        max(0.0, settings.risk_weight_severity),
        max(0.0, settings.risk_weight_density),
    )
    total_weight = sum(raw_weights) or 1.0
    w_extent, w_severity, w_density = (w / total_weight for w in raw_weights)

    worst_box = max(det.area_percentage for det in detections)

    components = [
        _component("Extent", defect_percentage, "of the frame damaged",
                   "%.2f%% of the frame damaged" % defect_percentage,
                   settings.risk_extent_full_scale, w_extent),
        _component("Worst defect", worst_box, "of the frame in one box",
                   "%.2f%% of the frame in one box" % worst_box,
                   settings.risk_severity_full_scale, w_severity),
        _component("Density", float(count), "defects detected",
                   "%d defect%s detected" % (count, "" if count == 1 else "s"),
                   float(settings.risk_density_full_scale), w_density),
    ]

    raw = sum(component.score * component.weight for component in components)

    # Hazard: area-weighted, so one big pothole outweighs several small cracks.
    total_area = sum(det.area for det in detections) or 1
    hazard = sum(class_weight(det.class_name) * det.area for det in detections) / total_area
    hazard = round(min(1.0, max(0.0, hazard)), 4)

    # Confidence: an unsure model makes a softer claim, but never below half.
    confidence = max(CONFIDENCE_FLOOR,
                     sum(det.confidence for det in detections) / float(count))
    confidence = round(min(1.0, confidence), 4)

    index = round(min(100.0, max(0.0, raw * hazard * confidence)), 2)
    level, colour, tier, window = classify_risk(index)

    worst = max(detections, key=lambda det: (det.severity_rank, det.area_percentage))

    area_by_class: Dict[str, int] = {}
    for det in detections:
        area_by_class[det.class_name] = area_by_class.get(det.class_name, 0) + det.area
    dominant = max(area_by_class.items(), key=lambda item: item[1])[0]

    return RiskAssessment(
        risk_index=index,
        risk_level=level,
        risk_colour=colour,
        priority_tier=tier,
        response_window=window,
        components=components,
        hazard_factor=hazard,
        confidence_factor=confidence,
        max_severity=worst.severity,
        dominant_defect=dominant,
        summary=_summary(index, level, tier, window, worst.severity, count,
                         defect_percentage),
    )
