"""
Report persistence.

Stores the outcome of an analysis: scores, the full detection list, coordinates,
provenance and the original photograph. Derived media (annotated image, PDF) is
not stored — it is regenerated on demand, which is why `model_name` and
`model_version` are recorded per row. A report re-rendered under a newer model
is not the same document, and the API says so rather than pretending.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.config import Settings, get_settings
from app.db.base import get_session
from app.db.models import Report, User
from app.utils.errors import (
    ForbiddenError,
    ImageTooLargeError,
    InvalidImageError,
    NotFoundError,
    UnsupportedImageTypeError,
)

router = APIRouter(tags=["reports"])

STATUSES = ("Draft", "Submitted", "Acknowledged", "Resolved")
StatusLiteral = Literal["Draft", "Submitted", "Acknowledged", "Resolved"]

# Who may move a report to which status.
#   citizen: may file their own report and withdraw it back to Draft
#   official: may acknowledge and resolve anything
CITIZEN_TRANSITIONS = {"Draft": {"Submitted"}, "Submitted": {"Draft"}}


# ----------------------------------------------------------------- schemas --
class ReportCreate(BaseModel):
    """The subset of an AnalyzeResponse worth persisting."""
    title: str | None = Field(default=None, max_length=240)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    road_health_score: float = Field(ge=0, le=100)
    road_condition: str = Field(max_length=20)
    defect_percentage: float = Field(ge=0)
    total_defects: int = Field(ge=0)
    defect_counts: dict[str, int] = Field(default_factory=dict)

    risk_index: float = Field(ge=0, le=100)
    risk_level: str = Field(max_length=20)
    priority_tier: str = Field(max_length=20)
    response_window: str | None = Field(default=None, max_length=120)
    risk_components: list[dict[str, Any]] = Field(default_factory=list)

    detections: list[dict[str, Any]] = Field(default_factory=list)

    model_name: str | None = Field(default=None, max_length=120)
    model_version: str | None = Field(default=None, max_length=64)
    inference_image_size: int | None = None

    image_sha256: str | None = Field(default=None, max_length=64)
    image_width: int | None = None
    image_height: int | None = None
    # The photograph is the evidence. Without it a report is an assertion about
    # a road nobody can look at, and GET /reports/{id}/image has nothing to
    # serve. Base64 of the ORIGINAL upload, not the annotated render - the
    # annotation is derived and can be recomputed; the photograph cannot.
    image_base64: str | None = Field(default=None, repr=False)
    image_mime: str | None = Field(default=None, max_length=40)

    complaint_description: str | None = None
    addressed_to: str | None = Field(default=None, max_length=240)
    analysed_at: datetime | None = None

    submit: bool = Field(default=False, description="File immediately instead of saving a draft")


class ReportOut(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    title: str | None
    latitude: float
    longitude: float
    road_health_score: float
    road_condition: str
    defect_percentage: float
    total_defects: int
    defect_counts: dict[str, Any]
    risk_index: float
    risk_level: str
    priority_tier: str
    response_window: str | None
    model_name: str | None
    model_version: str | None
    image_sha256: str | None
    has_image: bool
    created_at: datetime

    @classmethod
    def of(cls, r: Report) -> "ReportOut":
        return cls(
            id=r.id, reference=r.reference, status=r.status, title=r.title,
            latitude=r.latitude, longitude=r.longitude,
            road_health_score=float(r.road_health_score), road_condition=r.road_condition,
            defect_percentage=float(r.defect_percentage), total_defects=r.total_defects,
            defect_counts=r.defect_counts or {},
            risk_index=float(r.risk_index), risk_level=r.risk_level,
            priority_tier=r.priority_tier, response_window=r.response_window,
            model_name=r.model_name, model_version=r.model_version,
            image_sha256=r.image_sha256, has_image=r.image_bytes is not None,
            created_at=r.created_at,
        )


class ReportDetail(ReportOut):
    detections: list[dict[str, Any]]
    risk_components: list[dict[str, Any]]
    complaint_description: str | None
    addressed_to: str | None
    analysed_at: datetime | None


class StatusPatch(BaseModel):
    status: StatusLiteral


class ReportPage(BaseModel):
    items: list[ReportOut]
    total: int
    limit: int
    offset: int


class Stats(BaseModel):
    total: int
    by_condition: dict[str, int]
    by_risk_level: dict[str, int]
    by_status: dict[str, int]
    average_score: float | None
    worst: ReportOut | None


# ------------------------------------------------------------------ helpers --
def _reference() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d")
    return f"RHA-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def _decode_photo(body: ReportCreate, settings: Settings) -> tuple[bytes | None, str | None]:
    """
    Turn the submitted base64 photograph into bytes, or refuse it.

    Three ways this can be wrong, and all three are the client's fault rather
    than a server error: malformed base64, a file over the upload limit, and a
    payload that does not match the hash the client also sent (which would mean
    the stored evidence is not the image that was analysed).
    """
    if not body.image_base64:
        return None, None

    import base64
    import hashlib

    try:
        raw = base64.b64decode(body.image_base64, validate=True)
    except Exception:
        raise InvalidImageError("image_base64 is not valid base64.")

    if not raw:
        raise InvalidImageError("image_base64 decoded to an empty file.")

    if len(raw) > settings.max_image_size_bytes:
        raise ImageTooLargeError(
            f"The photograph is {len(raw) / 1e6:.1f} MB; the limit is "
            f"{settings.max_image_size_mb:.0f} MB."
        )

    if body.image_sha256:
        actual = hashlib.sha256(raw).hexdigest()
        if actual != body.image_sha256.lower():
            raise InvalidImageError(
                "The photograph does not match the image_sha256 sent with it. "
                "Storing it would attach the wrong evidence to this report."
            )

    mime = (body.image_mime or "image/jpeg").lower()
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise UnsupportedImageTypeError(f"Cannot store '{mime}'. Use JPG, PNG or WEBP.")
    return raw, mime


async def _owned(report_id: uuid.UUID, user: User, session: AsyncSession) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise NotFoundError("No report with that id.")
    # Officials may read any report; citizens only their own. Returning 404
    # rather than 403 avoids confirming that someone else's id exists.
    if report.user_id != user.id and user.role != "official":
        raise NotFoundError("No report with that id.")
    return report


# ------------------------------------------------------------------- routes --
@router.post("/reports", response_model=ReportDetail, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    image_bytes, image_mime = _decode_photo(body, settings)
    report = Report(
        user_id=user.id,
        reference=_reference(),
        status="Submitted" if body.submit else "Draft",
        image_bytes=image_bytes,
        image_mime=image_mime,
        **body.model_dump(exclude={"submit", "image_base64", "image_mime"}),
    )
    session.add(report)
    await session.flush()
    return ReportDetail(**ReportOut.of(report).model_dump(),
                        detections=report.detections or [],
                        risk_components=report.risk_components or [],
                        complaint_description=report.complaint_description,
                        addressed_to=report.addressed_to,
                        analysed_at=report.analysed_at)


@router.get("/reports", response_model=ReportPage)
async def list_reports(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    status_filter: str | None = Query(default=None, alias="status"),
    mine: bool = Query(default=True, description="Officials can set false to see every report"),
    # Bounding box for the map, so it does not download every report on earth.
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lon: float | None = Query(default=None, ge=-180, le=180),
    max_lon: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    where = []
    if mine or user.role != "official":
        where.append(Report.user_id == user.id)
    if status_filter:
        where.append(Report.status == status_filter)
    if None not in (min_lat, max_lat):
        where.append(Report.latitude.between(min_lat, max_lat))
    if None not in (min_lon, max_lon):
        where.append(Report.longitude.between(min_lon, max_lon))

    total = await session.scalar(select(func.count()).select_from(Report).where(*where)) or 0
    rows = (await session.scalars(
        select(Report).where(*where).order_by(Report.created_at.desc()).limit(limit).offset(offset)
    )).all()
    return ReportPage(items=[ReportOut.of(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/reports/stats", response_model=Stats)
async def stats(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    mine: bool = Query(default=True),
):
    where = [Report.user_id == user.id] if (mine or user.role != "official") else []

    async def bucket(col):
        rows = await session.execute(
            select(col, func.count()).where(*where).group_by(col))
        return {k: v for k, v in rows.all()}

    total = await session.scalar(select(func.count()).select_from(Report).where(*where)) or 0
    avg = await session.scalar(select(func.avg(Report.road_health_score)).where(*where))
    worst_row = await session.scalar(
        select(Report).where(*where).order_by(Report.risk_index.desc()).limit(1))

    return Stats(
        total=total,
        by_condition=await bucket(Report.road_condition),
        by_risk_level=await bucket(Report.risk_level),
        by_status=await bucket(Report.status),
        average_score=round(float(avg), 2) if avg is not None else None,
        worst=ReportOut.of(worst_row) if worst_row else None,
    )


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    r = await _owned(report_id, user, session)
    return ReportDetail(**ReportOut.of(r).model_dump(),
                        detections=r.detections or [],
                        risk_components=r.risk_components or [],
                        complaint_description=r.complaint_description,
                        addressed_to=r.addressed_to,
                        analysed_at=r.analysed_at)


@router.get("/reports/{report_id}/image")
async def get_report_image(
    report_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    r = await _owned(report_id, user, session)
    if not r.image_bytes:
        raise NotFoundError("No photograph was stored for this report.")
    return Response(content=r.image_bytes, media_type=r.image_mime or "image/jpeg")


@router.patch("/reports/{report_id}/status", response_model=ReportOut)
async def set_status(
    report_id: uuid.UUID,
    body: StatusPatch,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    r = await _owned(report_id, user, session)

    if user.role != "official":
        allowed = CITIZEN_TRANSITIONS.get(r.status, set())
        if body.status not in allowed:
            # This is the hole the localStorage prototype had: anyone could mark
            # anything resolved. Acknowledged/Resolved are the authority's to set.
            raise ForbiddenError(
                f"A citizen cannot move a report from {r.status} to {body.status}. "
                "Acknowledging and resolving is done by the municipal body."
            )

    r.status = body.status
    session.add(r)
    await session.flush()
    return ReportOut.of(r)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    r = await _owned(report_id, user, session)
    if r.user_id != user.id:
        raise ForbiddenError("Only the citizen who filed a report may delete it.")
    await session.delete(r)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
