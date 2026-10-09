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
from app.services import geocode_service
from app.services.assessment_service import run_assessment
from app.services.detection_service import get_detector
from app.utils.errors import ServerBusyError
from app.utils.geotag import check_location_source
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
    from app.db.base import database_enabled, engine_ready

    detector = get_detector()
    # Three distinct states, and the difference matters to whoever is reading
    # this probe: no database asked for, one asked for and working, or one
    # asked for and unreachable. The last is the only one that needs someone.
    if not database_enabled(settings):
        persistence = "disabled"
    else:
        persistence = "enabled" if engine_ready() else "unavailable"

    return HealthResponse(
        status="ok" if detector.is_ready else "degraded",
        version=settings.app_version,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 2),
        model_loaded=detector.is_ready,
        model=detector.info(),
        persistence=persistence,
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
    location_source: Optional[str] = Form(
        None,
        description="How the coordinates were obtained: 'photo' (the GPS embedded in this image - "
                    "verified here), 'device' (live GPS at in-app capture) or 'map' (pinned by hand)",
    ),
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
    location = check_location_source(location_source, lat, lon, image_bytes)
    # Usually a cache hit: the upload screen looked this point up already.
    # Done before taking an inference slot so a slow lookup never holds one.
    location["address"] = await run_in_threadpool(geocode_service.reverse, lat, lon)

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
            location=location,
            settings=settings,
            include_annotated_image=include_image,
            include_report=include_pdf,
        )
    finally:
        _inference_slots.release()
        await image.close()


@router.get(
    "/geocode/reverse",
    tags=["assessment"],
    summary="Place name for a point (OpenStreetMap), for previewing a complaint location",
)
async def reverse_geocode(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
) -> dict:
    """
    Returns ``{"latitude", "longitude", "label", "full", "source"}``. ``label``
    is null when no place name is available - the client then shows the
    coordinates, never a guess. Lookups are cached and rate-limited server-side
    to respect OpenStreetMap's usage policy.
    """
    lat, lon = validate_coordinates(latitude, longitude)
    found = await run_in_threadpool(geocode_service.reverse, lat, lon)
    return {
        "latitude": lat,
        "longitude": lon,
        "label": found["label"] if found else None,
        "full": found["full"] if found else None,
        "source": found["source"] if found else None,
    }
