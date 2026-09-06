"""
Database schema.

Storage policy: metadata is stored, derived media is not. A report keeps the
scores, the full detection list and the ORIGINAL photograph; the annotated image
and the PDF are regenerated on demand from those. That is roughly 2 KB of row
plus ~100 KB of photo per report, against ~415 KB if every derived artefact were
kept — the difference between about 10,000 reports and about 2,400 on a 1 GB
tier.

The cost of regenerating is that output can drift: rerun a stored report against
a retrained model and the boxes move. `model_name` and `model_version` are
recorded per report so a regenerated document can be compared against the model
that produced the original, rather than silently claiming to be the same report.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer,
    LargeBinary, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # bcrypt hash. The plaintext is never stored, logged or returned.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    # 'citizen' files reports; 'official' may move any report's status.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="citizen")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    reports: Mapped[list["Report"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        # Case-insensitive uniqueness without requiring the citext extension,
        # which is not guaranteed to be enabled on a managed instance.
        Index("ix_users_email_lower", "email", unique=True, postgresql_ops={"email": "text_pattern_ops"}),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reference: Mapped[str] = mapped_column(String(40), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft")
    title: Mapped[str | None] = mapped_column(String(240))

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # --- scoring -----------------------------------------------------------
    road_health_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    road_condition: Mapped[str] = mapped_column(String(20), nullable=False)
    defect_percentage: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    total_defects: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defect_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # --- risk --------------------------------------------------------------
    risk_index: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    response_window: Mapped[str | None] = mapped_column(String(120))
    risk_components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Full detection list, kept verbatim so a report can be re-rendered without
    # re-running the model.
    detections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # --- provenance --------------------------------------------------------
    model_name: Mapped[str | None] = mapped_column(String(120))
    model_version: Mapped[str | None] = mapped_column(String(64))
    inference_image_size: Mapped[int | None] = mapped_column(Integer)

    # --- evidence ----------------------------------------------------------
    image_sha256: Mapped[str | None] = mapped_column(String(64))
    image_width: Mapped[int | None] = mapped_column(Integer)
    image_height: Mapped[int | None] = mapped_column(Integer)
    image_mime: Mapped[str | None] = mapped_column(String(40))
    image_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    image_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    complaint_description: Mapped[str | None] = mapped_column(Text)
    addressed_to: Mapped[str | None] = mapped_column(String(240))

    analysed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="reports")

    __table_args__ = (
        UniqueConstraint("reference", name="uq_reports_reference"),
        # History is always "this user's reports, newest first".
        Index("ix_reports_user_created", "user_id", "created_at"),
        # The queue filters by status; the map filters by a bounding box.
        Index("ix_reports_status", "status"),
        Index("ix_reports_bbox", "latitude", "longitude"),
    )
