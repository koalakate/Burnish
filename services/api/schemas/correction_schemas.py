from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CorrectionItem(BaseModel):
    id: str
    rule_type: str
    severity: str
    message: str
    element_id: str | None = None
    element_bbox: dict[str, Any] | None = None
    original_value: str | None = None
    expected_value: str | None = None
    correction_status: str | None = None


class SlideCorrectionGroup(BaseModel):
    slide_index: int
    corrections: list[CorrectionItem] = []


class CorrectionsListResponse(BaseModel):
    check_run_id: str
    slides: list[SlideCorrectionGroup] = []
    total: int = 0


class EditCorrectionRequest(BaseModel):
    value: str


class CorrectionActionResponse(BaseModel):
    id: str
    correction_status: str


class FixAllResponse(BaseModel):
    check_run_id: str
    accepted_count: int
    status: str


class ExportResponse(BaseModel):
    check_run_id: str
    download_url: str
    dqs_after: float | None = None
