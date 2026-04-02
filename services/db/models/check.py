import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class CheckStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class TriggerType(enum.StrEnum):
    manual = "manual"
    upload = "upload"
    cicd = "cicd"
    schedule = "schedule"
    api = "api"


class Severity(enum.StrEnum):
    error = "error"
    warning = "warning"
    info = "info"


class CorrectionStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class CheckRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "check_runs"

    deck_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decks.id"))
    ruleset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brand_rulesets.id")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    triggered_by: Mapped[TriggerType] = mapped_column(Enum(TriggerType), default=TriggerType.manual)
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus), default=CheckStatus.queued)
    dqs_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue_count_error: Mapped[int] = mapped_column(Integer, default=0)
    issue_count_warning: Mapped[int] = mapped_column(Integer, default=0)
    issue_count_info: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_pptx_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    slide_results: Mapped[list["SlideCheckResult"]] = relationship(back_populates="check_run")


class SlideCheckResult(Base, UUIDMixin):
    __tablename__ = "slide_check_results"

    check_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("check_runs.id")
    )
    slide_index: Mapped[int] = mapped_column(Integer)
    dqs_slide: Mapped[float] = mapped_column(Float, default=0.0)
    vision_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    thumbnail_ref: Mapped[str] = mapped_column(String(1024), default="")
    corrected_thumbnail_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    corrected_csm_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    check_run: Mapped["CheckRun"] = relationship(back_populates="slide_results")
    issues: Mapped[list["Issue"]] = relationship(back_populates="slide_result")


class Issue(Base, UUIDMixin):
    __tablename__ = "issues"

    slide_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slide_check_results.id")
    )
    rule_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    message: Mapped[str] = mapped_column(String(1024))
    element_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    element_bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    original_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correction_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_status: Mapped[CorrectionStatus | None] = mapped_column(
        Enum(CorrectionStatus), nullable=True
    )

    slide_result: Mapped["SlideCheckResult"] = relationship(back_populates="issues")
