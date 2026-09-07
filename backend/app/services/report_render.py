"""
Rebuild a filed report's PDF from what was stored.

The point of the storage policy in ``app/db/models.py`` is that derived media
is not kept: the annotated image, the defect crops and the PDF are all thrown
away and rebuilt on demand, which is what makes a report cost ~102 KB instead
of ~415 KB. This module is the "on demand" half of that bargain. Without it,
the document the whole product exists to produce lives only in the browser tab
where the analysis ran.

Two rules govern what comes out:

1. **The stored numbers win.** Nothing here re-runs the model. Scores, risk and
   detections are replayed from the row exactly as filed. Geometry that was
   never stored (the summed-versus-union area split) is recomputed from the
   stored boxes, which is pure arithmetic on numbers that cannot have changed.

2. **The document says it is a regeneration.** It carries the date it was
   rebuilt and the weights fingerprint the numbers were produced under, so a
   PDF rebuilt after a retrain can be told apart from the one that was filed.
   If the current configuration would score these same boxes differently -
   because AREA_METHOD or a band boundary was edited since - the report says
   so instead of quietly showing the new figure.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List

from PIL import Image

from app.config import Settings, get_settings
from app.db.models import Report
from app.models.schemas import Detection, RiskAssessment, RiskComponent
from app.services import image_service, pdf_service, risk_service, scoring_service
from app.utils.errors import ReportGenerationError, ReportNotRenderableError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# What the document should say about where this report has got to. The live
# analyse path has no status - nothing is filed at the moment it is produced.
SUBMISSION_STATUS = {
    "Draft": "Saved by the citizen as a draft - not yet filed with the authority",
    "Submitted": "Filed with the authority by the citizen",
    "Acknowledged": "Acknowledged by the municipal body",
    "Resolved": "Marked resolved by the municipal body",
}


def _maps_url(latitude: float, longitude: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"


def _raw_boxes(detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Stored detections carry ``bbox: [x1, y1, x2, y2]``; the imaging and scoring
    helpers want the corners as separate keys. One shape conversion, in one
    place, rather than two subtly different ones at each call site.
    """
    boxes = []
    for det in detections:
        bbox = det.get("bbox") or []
        if len(bbox) != 4:
            continue
        x1, y1, x2, y2 = (int(v) for v in bbox)
        boxes.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "class_id": int(det.get("class_id", 0)),
            "class_name": str(det.get("class_name", "defect")),
            "confidence": float(det.get("confidence", 0.0)),
        })
    return boxes


def _risk(report: Report, detections: List[Detection]) -> RiskAssessment:
    """
    The risk assessment as filed, or the closest honest reconstruction.

    Rows written before ``risk_detail`` existed have only the headline numbers,
    so the secondary fields are recomputed from the stored detections. Those
    are derived from constants in app/config.py, which is exactly why newer
    rows store the object instead of trusting that nobody edits them.
    """
    if report.risk_detail:
        try:
            return RiskAssessment(**report.risk_detail)
        except Exception:  # pragma: no cover - a malformed row should not 500
            logger.warning("risk_detail on %s did not validate; recomputing", report.reference)

    recomputed = risk_service.assess_risk(detections, float(report.defect_percentage))

    # Stored components are raw JSON. model_copy does NOT validate, so feeding
    # them in unchecked puts dicts where the PDF expects objects and turns a
    # bad row into a 500 at render time. Validate, and keep the recomputed
    # components if the stored ones do not fit the schema.
    components = recomputed.components
    if report.risk_components:
        try:
            components = [RiskComponent(**c) for c in report.risk_components]
        except Exception:
            logger.warning("risk_components on %s did not validate; recomputing",
                           report.reference)

    # Headline figures still come from the row: those are what was filed.
    return recomputed.model_copy(update={
        "risk_index": float(report.risk_index),
        "risk_level": report.risk_level,
        "priority_tier": report.priority_tier,
        "response_window": report.response_window or recomputed.response_window,
        "components": components,
    })


def build_pdf(report: Report, settings: Settings | None = None) -> bytes:
    """Render the stored report back into the PDF that was filed."""
    settings = settings or get_settings()

    if not report.image_bytes:
        raise ReportNotRenderableError(
            "This report was filed without its photograph, so the document "
            "cannot be rebuilt. Only reports saved with their evidence can be "
            "downloaded again."
        )

    try:
        image = Image.open(io.BytesIO(report.image_bytes))
        image.load()
    except Exception as exc:
        raise ReportGenerationError("The stored photograph could not be read.") from exc

    stored = list(report.detections or [])
    boxes = _raw_boxes(stored)
    width, height = image.size

    # Replay the geometry. score_image is deterministic given the same boxes,
    # so this reproduces the area breakdown that was never stored - and, as a
    # side effect, tells us whether today's settings still agree with the row.
    scored = scoring_service.score_image(boxes, width, height, settings)
    detections = risk_service.enrich_detections(scored["detections"])

    drift: List[str] = []
    if abs(float(report.road_health_score) - scored["road_health_score"]) > 0.05:
        drift.append(
            "Note: this report was filed with a road health score of %.2f. Under the "
            "scoring configuration now in force the same defects would score %.2f. "
            "Every figure in this document is the one that was filed."
            % (float(report.road_health_score), scored["road_health_score"])
        )

    risk = _risk(report, detections)

    annotated_jpeg, annotated_size = image_service.build_annotated_jpeg(
        image, boxes,
        max_side=settings.max_annotated_dimension,
        quality=settings.annotated_jpeg_quality,
    )
    crops = image_service.build_defect_crops(
        image, boxes,
        max_side=settings.crop_thumbnail_side,
        quality=settings.annotated_jpeg_quality,
        limit=settings.max_defect_crops,
    ) if settings.include_defect_crops else []

    filed_at = report.analysed_at or report.created_at
    regenerated_at = datetime.now(timezone.utc)

    return pdf_service.build_report({
        "reference": report.reference,
        "generated_at": filed_at,
        "regenerated_at": regenerated_at,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "maps_url": _maps_url(report.latitude, report.longitude),
        "sha256": report.image_sha256 or "",
        # Everything below is the row, not a fresh computation.
        "road_health_score": float(report.road_health_score),
        "road_condition": report.road_condition,
        "condition_colour": scoring_service.classify_road_condition(
            float(report.road_health_score))[1],
        "defect_percentage": float(report.defect_percentage),
        "area_method": scored["area_breakdown"].method,
        "summed_percentage": scored["area_breakdown"].summed_percentage,
        "union_percentage": scored["area_breakdown"].union_percentage,
        "defect_counts": report.defect_counts or scored["defect_counts"],
        "total_defects": report.total_defects,
        "detections": detections,
        "risk": risk,
        "complaint_description": report.complaint_description or "",
        "addressed_to": report.addressed_to or settings.municipal_authority,
        "region": settings.complaint_region,
        "annotated_jpeg": annotated_jpeg,
        "defect_crops": crops,
        "image_filename": "evidence.jpg",
        "image_size": annotated_size,
        "source_size": (report.image_width or width, report.image_height or height),
        # Provenance is the ROW's, never the model currently loaded in this
        # process. A server running retrained weights did not produce these
        # numbers and must not put its own name to them.
        "model_status": "trained",
        "model_name": report.model_name or "unknown",
        "model_version": report.model_version or "unknown",
        "model_classes": sorted((report.defect_counts or {}).keys()),
        "is_road_defect_model": True,
        "confidence_threshold": settings.confidence_threshold,
        "iou_threshold": settings.iou_threshold,
        "inference_image_size": report.inference_image_size or settings.inference_image_size,
        "app_name": settings.app_name,
        "submission_status": SUBMISSION_STATUS.get(
            report.status, "Prepared by the citizen"),
        "extra_warnings": drift,
    })
