"""
HTTP routes.

This layer does four things and nothing else:
  1. accept and validate the request,
  2. hand the work to the service layer,
  3. keep the event loop free while that work runs,
  4. shape the response.

All business logic lives in ``app/services``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, File, Form, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.models.schemas import (
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
    RootResponse,
)
from app.services.assessment_service import run_assessment
from app.services.detection_service import get_detector
from app.utils.errors import ServerBusyError
from app.utils.logging_config import get_logger
from app.utils.validation import read_upload, validate_coordinates, validate_declared_type

logger = get_logger(__name__)
router = APIRouter()

settings = get_settings()

# A free Render instance has a fraction of a CPU and 512 MB of RAM. Running two
# YOLO inferences at once there does not make anything faster - it just risks an
# out-of-memory kill. This semaphore serialises the expensive part of the
# pipeline; anything queued behind it simply waits its turn.
_inference_slots = asyncio.Semaphore(settings.max_concurrent_inferences)
_QUEUE_TIMEOUT_SECONDS = 55.0

_STARTED_AT = time.monotonic()


@router.get("/", response_model=RootResponse, tags=["status"], summary="API status")
async def root() -> RootResponse:
    return RootResponse(
        status="ok",
        message="Automated Road Health Assessment API is running",
        version=settings.app_version,
    )


@router.get("/health", response_model=HealthResponse, tags=["status"], summary="Health check")
async def health() -> HealthResponse:
    """
    Liveness/readiness probe for Render.

    Always answers 200 so the platform does not restart a container that is
    otherwise fine; ``status`` is ``degraded`` when no model is loaded.
    """
    detector = get_detector()
    return HealthResponse(
        status="ok" if detector.is_ready else "degraded",
        version=settings.app_version,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 2),
        model_loaded=detector.is_ready,
        model=detector.info(),
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["assessment"],
    summary="Analyse a road photograph and generate a complaint report",
    responses={
        400: {"model": ErrorResponse, "description": "No image / empty upload"},
        413: {"model": ErrorResponse, "description": "Image too large"},
        415: {"model": ErrorResponse, "description": "Unsupported image format"},
        422: {"model": ErrorResponse, "description": "Invalid image or coordinates"},
        503: {"model": ErrorResponse, "description": "Detection model unavailable or server busy"},
    },
)
async def analyze(
    image: UploadFile = File(..., description="Road photograph (JPG, PNG, WEBP or BMP)"),
    latitude: float = Form(..., description="GPS latitude, -90 to 90"),
    longitude: float = Form(..., description="GPS longitude, -180 to 180"),
    include_image: bool = Query(True, description="Include the base64 annotated JPEG in the response"),
    include_pdf: bool = Query(True, description="Include the base64 PDF report in the response"),
) -> AnalyzeResponse:
    """
    Full pipeline: validate -> detect -> score -> classify -> annotate -> PDF.

    The uploaded photograph is never written to disk. The response carries the
    structured results plus the annotated image and the PDF report as base64,
    so the browser can show the findings and offer an immediate download from
    a single request.

    Set ``?include_pdf=false`` for a fast, lightweight JSON-only response
    (useful for a live preview before the citizen commits to a report).
    """
    validate_declared_type(image.filename, image.content_type)
    lat, lon = validate_coordinates(latitude, longitude)
    image_bytes = await read_upload(image, settings)

    try:
        await asyncio.wait_for(_inference_slots.acquire(), timeout=_QUEUE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise ServerBusyError() from exc

    try:
        # CPU-bound work goes to a worker thread so other requests (and the
        # /health probe) are still served while YOLO runs.
        return await run_in_threadpool(
            run_assessment,
            image_bytes=image_bytes,
            filename=image.filename,
            latitude=lat,
            longitude=lon,
            settings=settings,
            include_annotated_image=include_image,
            include_report=include_pdf,
        )
    finally:
        _inference_slots.release()
        await image.close()
