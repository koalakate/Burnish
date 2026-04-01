from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CheckRunResponse(BaseModel):
    id: str
    deck_id: str
    status: str
    dqs_overall: float | None = None
    issue_count_error: int = 0
    issue_count_warning: int = 0
    issue_count_info: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class CheckTriggerResponse(BaseModel):
    check_run_id: str
    status: str


class SlideResultSummary(BaseModel):
    slide_index: int
    dqs_slide: float
    thumbnail_url: str | None = None


class CheckRunDetailResponse(CheckRunResponse):
    slides: list[SlideResultSummary] = []


class IssueResponse(BaseModel):
    id: str
    rule_type: str
    severity: str
    message: str
    element_id: str | None = None
    element_bbox: dict[str, Any] | None = None
    original_value: str | None = None
    expected_value: str | None = None
    correction_status: str | None = None


class SlideDetailResponse(BaseModel):
    slide_index: int
    dqs_slide: float
    thumbnail_url: str | None = None
    issues: list[IssueResponse] = []
