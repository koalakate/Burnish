"""Design Quality Score (DQS) calculation.

Combines rule-engine issues, GPT-4o vision scores, and accessibility
violations into a single 0-100 quality metric per slide and per deck.

Formula:
    DQS = 0.4 × rule_score + 0.3 × vision_score + 0.3 × accessibility_score
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from services.rules.models import Issue, Severity, SlideIssueSet
from services.vision.scorer import VisionScore

# Penalty weights per severity level
_SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.error: 10,
    Severity.warning: 3,
    Severity.info: 1,
}

_ACCESSIBILITY_PENALTY = 15


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


class SlideDQS(BaseModel):
    """DQS breakdown for a single slide."""

    slide_index: int = Field(ge=0)
    rule_score: float = Field(ge=0, le=100)
    vision_score: float = Field(ge=0, le=100)
    accessibility_score: float = Field(ge=0, le=100)
    dqs: float = Field(ge=0, le=100)


class DQSReport(BaseModel):
    """Full DQS report for an entire deck."""

    slides: list[SlideDQS] = Field(default_factory=list)
    overall_dqs: float = Field(ge=0, le=100)


def _compute_rule_score(issues: list[Issue]) -> float:
    """100 minus weighted penalty per issue, clamped to 0."""
    penalty = sum(_SEVERITY_PENALTY.get(i.severity, 0) for i in issues)
    return _clamp(100.0 - penalty)


def _compute_vision_score(score: VisionScore | None) -> float:
    """Average of GPT-4o dimension scores normalized to 0-100."""
    if score is None:
        return 0.0
    # VisionScore dimensions are 1-10; normalize to 0-100
    return _clamp((score.average - 1) * (100.0 / 9.0))


def _compute_accessibility_score(issues: list[Issue]) -> float:
    """100 minus 15 per WCAG AA violation, clamped to 0."""
    return _clamp(100.0 - _ACCESSIBILITY_PENALTY * len(issues))


def _compute_slide_dqs(
    rule_score: float, vision_score: float, accessibility_score: float
) -> float:
    return round(0.4 * rule_score + 0.3 * vision_score + 0.3 * accessibility_score, 2)


def calculate_dqs(
    rule_issues: list[SlideIssueSet],
    vision_scores: list[VisionScore],
    accessibility_issues: list[Issue],
) -> DQSReport:
    """Calculate per-slide and overall DQS.

    Args:
        rule_issues: Per-slide issue sets from the rule engine.
        vision_scores: Per-slide GPT-4o vision scores (may be empty).
        accessibility_issues: Flat list of accessibility issues (each carries slide_index).

    Returns:
        DQSReport with per-slide breakdown and overall deck DQS.
    """
    # Group accessibility issues by slide index
    acc_by_slide: dict[int, list[Issue]] = {}
    for issue in accessibility_issues:
        acc_by_slide.setdefault(issue.slide_index, []).append(issue)

    slide_count = len(rule_issues)
    slide_results: list[SlideDQS] = []

    for idx in range(slide_count):
        slide_rule_issues = rule_issues[idx].issues if idx < len(rule_issues) else []
        vision = vision_scores[idx] if idx < len(vision_scores) else None
        slide_acc_issues = acc_by_slide.get(idx, [])

        rs = _compute_rule_score(slide_rule_issues)
        vs = _compute_vision_score(vision)
        acs = _compute_accessibility_score(slide_acc_issues)
        dqs = _compute_slide_dqs(rs, vs, acs)

        slide_results.append(
            SlideDQS(
                slide_index=idx,
                rule_score=rs,
                vision_score=vs,
                accessibility_score=acs,
                dqs=dqs,
            )
        )

    if slide_results:
        overall = round(
            sum(s.dqs for s in slide_results) / len(slide_results), 2
        )
    else:
        overall = 0.0

    return DQSReport(slides=slide_results, overall_dqs=overall)
