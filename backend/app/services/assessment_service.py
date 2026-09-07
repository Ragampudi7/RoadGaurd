"""
Assessment service - the orchestrator.

This is the single place that runs the whole pipeline end to end:

    bytes -> decode -> detect -> score -> classify -> risk
          -> annotate -> crops -> PDF -> response

Keeping the sequence here (rather than in the route) means the API layer stays
a thin HTTP adapter, and the pipeline can be unit-tested without a web server.

Everything is CPU-bound and synchronous; ``app/api/routes.py`` runs it in a
worker thread so the event loop stays responsive.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import Settings, get_settings
from app.models.schemas import (
    AnalyzeResponse,
    ImageInfo,
    Location,
    MediaPayload,
)
from app.services import image_service, pdf_service, risk_service, scoring_service
from app.services.detection_service import RoadDefectDetector, get_detector
from app.utils.logging_config import get_logger
from app.utils.validation import decode_image, safe_filename

logger = get_logger(__name__)

DEMO_BANNER = "DEMONSTRATION MODE - NOT ROAD-DEFECT DETECTIONS"


def _now(settings: Settings) -> datetime:
    """Current time in the report's configured timezone."""
    tz = timezone(timedelta(minutes=settings.report_timezone_offset_minutes))
    return datetime.now(tz)


def _reference(moment: datetime) -> str:
    return "RHA-%s-%s" % (moment.strftime("%Y%m%d"), uuid.uuid4().hex[:6].upper())


def _maps_url(latitude: float, longitude: float) -> str:
    return "https://www.google.com/maps/search/?api=1&query=%.6f,%.6f" % (latitude, longitude)


def run_assessment(
    *,
    image_bytes: bytes,
    filename: Optional[str],
    latitude: float,
    longitude: float,
    settings: Optional[Settings] = None,
    detector: Optional[RoadDefectDetector] = None,
    include_annotated_image: bool = True,
    include_report: bool = True,
) -> AnalyzeResponse:
    """Run the complete assessment and return the API response model."""
    settings = settings or get_settings()
    detector = detector or get_detector()

    started = time.perf_counter()
    moment = _now(settings)
    reference = _reference(moment)
    display_name = safe_filename(filename)

    # An evidence digest anyone can recompute from the same file. It says
    # "this report was produced from exactly these bytes" - nothing more, and
    # in particular it is not a claim that anyone has verified the photograph.
    digest = hashlib.sha256(image_bytes).hexdigest()

    # 1. Decode and validate the actual pixels.
    image = decode_image(image_bytes, settings)
    width, height = image.size

    # 2. Detect.
    raw_detections = detector.predict(image)
    logger.info(
        "%s | %s | %dx%d | %d detection(s)",
        reference, display_name, width, height, len(raw_detections),
    )

    # 3. Score, classify, then estimate risk.
    scored = scoring_service.score_image(raw_detections, width, height, settings)
    breakdown = scored["area_breakdown"]
    is_real_model = detector.is_road_defect_model

    detections = risk_service.enrich_detections(scored["detections"])
    risk = risk_service.assess_risk(detections, scored["defect_percentage"], settings)

    complaint = scoring_service.build_complaint_description(
        score=scored["road_health_score"],
        condition=scored["road_condition"],
        defect_counts=scored["defect_counts"],
        total_defects=scored["total_defects"],
        defect_percentage=scored["defect_percentage"],
        latitude=latitude,
        longitude=longitude,
        authority=settings.municipal_authority,
        is_road_defect_model=is_real_model,
        risk=risk if is_real_model else None,
    )

    # 4. Annotate and crop (in memory).
    annotated_payload: Optional[MediaPayload] = None
    annotated_jpeg: Optional[bytes] = None
    annotated_size = (width, height)
    crop_payloads: List[MediaPayload] = []
    crops: List[Tuple[bytes, Tuple[int, int]]] = []
    want_visuals = include_annotated_image or include_report

    if want_visuals:
        annotated_jpeg, annotated_size = image_service.build_annotated_jpeg(
            image,
            raw_detections,
            max_side=settings.max_annotated_dimension,
            quality=settings.annotated_jpeg_quality,
            banner=None if is_real_model else DEMO_BANNER,
        )
        if include_annotated_image:
            annotated_payload = MediaPayload(
                filename="%s_annotated.jpg" % reference,
                mime_type="image/jpeg",
                size_bytes=len(annotated_jpeg),
                data=image_service.to_base64(annotated_jpeg),
            )

        if settings.include_defect_crops and raw_detections:
            crops = image_service.build_defect_crops(
                image,
                raw_detections,
                max_side=settings.crop_thumbnail_side,
                quality=settings.annotated_jpeg_quality,
                limit=settings.max_defect_crops,
            )
            crop_payloads = [
                MediaPayload(
                    filename="%s_defect_%d.jpg" % (reference, index),
                    mime_type="image/jpeg",
                    size_bytes=len(data),
                    data=image_service.to_base64(data),
                )
                for index, (data, _size) in enumerate(crops, start=1)
            ]

    # 5. Build the PDF (also entirely in memory).
    report_payload: Optional[MediaPayload] = None
    if include_report:
        pdf_bytes = pdf_service.build_report({
            "reference": reference,
            "generated_at": moment,
            "latitude": latitude,
            "longitude": longitude,
            "maps_url": _maps_url(latitude, longitude),
            "sha256": digest,
            "road_health_score": scored["road_health_score"],
            "road_condition": scored["road_condition"],
            "condition_colour": scored["condition_colour"],
            "defect_percentage": scored["defect_percentage"],
            "area_method": breakdown.method,
            "summed_percentage": breakdown.summed_percentage,
            "union_percentage": breakdown.union_percentage,
            "defect_counts": scored["defect_counts"],
            "total_defects": scored["total_defects"],
            "detections": detections,
            "risk": risk,
            "complaint_description": complaint,
            "addressed_to": settings.municipal_authority,
            "region": settings.complaint_region,
            "annotated_jpeg": annotated_jpeg,
            "defect_crops": crops,
            "image_filename": display_name,
            "image_size": annotated_size,
            "source_size": (width, height),
            "model_status": detector.status,
            "model_name": detector.info().name,
            "model_version": detector.info().version,
            "model_classes": detector.info().classes,
            "is_road_defect_model": is_real_model,
            "confidence_threshold": settings.confidence_threshold,
            "iou_threshold": settings.iou_threshold,
            "inference_image_size": settings.inference_image_size,
            "app_name": settings.app_name,
        })
        report_payload = MediaPayload(
            filename="road_health_report_%s.pdf" % reference,
            mime_type="application/pdf",
            size_bytes=len(pdf_bytes),
            data=image_service.to_base64(pdf_bytes),
        )

    warnings = list(detector.warnings())
    if breakdown.overlap_detected and breakdown.method == "sum":
        warnings.append(
            "Some bounding boxes overlap. Following the project specification the box "
            "areas are summed, so the shared pixels are counted more than once "
            "(summed %.2f%% vs overlap-corrected %.2f%%). Set AREA_METHOD=union to "
            "score on the overlap-corrected figure instead."
            % (breakdown.summed_percentage, breakdown.union_percentage)
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return AnalyzeResponse(
        success=True,
        request_id=reference,
        analysed_at=moment.isoformat(timespec="seconds"),
        road_health_score=scored["road_health_score"],
        road_condition=scored["road_condition"],
        defect_percentage=scored["defect_percentage"],
        total_defects=scored["total_defects"],
        defect_counts=scored["defect_counts"],
        detections=detections,
        risk=risk,
        location=Location(
            latitude=latitude,
            longitude=longitude,
            maps_url=_maps_url(latitude, longitude),
        ),
        image=ImageInfo(
            filename=display_name,
            width=width,
            height=height,
            area_pixels=width * height,
            sha256=digest,
        ),
        area_breakdown=breakdown,
        model_info=detector.info(),
        complaint_description=complaint,
        addressed_to=settings.municipal_authority,
        processing_time_ms=elapsed_ms,
        warnings=warnings,
        annotated_image=annotated_payload,
        defect_crops=crop_payloads,
        report=report_payload,
    )
