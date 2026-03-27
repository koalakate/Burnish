"""Issue and severity models for the rule engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from packages.csm.models import BoundingBox


class Severity(StrEnum):
    """Severity level for a detected issue."""

    error = "error"
    warning = "warning"
    info = "info"


class Issue(BaseModel):
    """A single issue detected on a slide."""

    id: str = Field(description="Unique identifier for this issue instance")
    slide_index: int = Field(ge=0, description="Zero-based slide index")
    element_id: str = Field(default="", description="ID of the element with the issue")
    evaluator: str = Field(description="Name of the evaluator that found this issue")
    severity: Severity
    message: str = Field(description="Human-readable description of the issue")
    details: dict[str, object] = Field(
        default_factory=dict,
        description="Structured details for the correction engine",
    )
    bbox: BoundingBox | None = Field(
        default=None, description="Bounding box of the affected element"
    )


class SlideIssueSet(BaseModel):
    """All issues found on a single slide."""

    slide_index: int = Field(ge=0)
    issues: list[Issue] = Field(default_factory=list)
