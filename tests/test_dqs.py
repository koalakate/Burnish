"""Tests for DQS (Design Quality Score) calculation."""

from __future__ import annotations

from services.rules.dqs import (
    DQSReport,
    SlideDQS,
    _compute_accessibility_score,
    _compute_rule_score,
    _compute_vision_score,
    calculate_dqs,
)
from services.rules.models import Issue, Severity, SlideIssueSet
from services.vision.scorer import VisionScore


def _make_issue(
    slide_index: int = 0,
    severity: Severity = Severity.error,
    evaluator: str = "test",
) -> Issue:
    return Issue(
        id=f"test-{slide_index}-{severity}",
        slide_index=slide_index,
        evaluator=evaluator,
        severity=severity,
        message="test issue",
    )


def _perfect_vision() -> VisionScore:
    return VisionScore(
        visual_quality=10, layout_balance=10, readability=10, overall_impression=10
    )


def _mid_vision() -> VisionScore:
    return VisionScore(
        visual_quality=5, layout_balance=5, readability=5, overall_impression=5
    )


def _worst_vision() -> VisionScore:
    return VisionScore(
        visual_quality=1, layout_balance=1, readability=1, overall_impression=1
    )


class TestRuleScore:
    def test_no_issues(self) -> None:
        assert _compute_rule_score([]) == 100.0

    def test_errors_penalize(self) -> None:
        issues = [_make_issue(severity=Severity.error) for _ in range(3)]
        assert _compute_rule_score(issues) == 70.0

    def test_mixed_severities(self) -> None:
        issues = [
            _make_issue(severity=Severity.error),      # -10
            _make_issue(severity=Severity.warning),     # -3
            _make_issue(severity=Severity.info),        # -1
        ]
        assert _compute_rule_score(issues) == 86.0

    def test_clamps_to_zero(self) -> None:
        issues = [_make_issue(severity=Severity.error) for _ in range(15)]
        assert _compute_rule_score(issues) == 0.0


class TestVisionScore:
    def test_perfect(self) -> None:
        assert _compute_vision_score(_perfect_vision()) == 100.0

    def test_minimum(self) -> None:
        assert _compute_vision_score(_worst_vision()) == 0.0

    def test_mid(self) -> None:
        score = _compute_vision_score(_mid_vision())
        # (5 - 1) * 100/9 ≈ 44.44
        assert 44.0 <= score <= 45.0

    def test_none(self) -> None:
        assert _compute_vision_score(None) == 0.0


class TestAccessibilityScore:
    def test_no_violations(self) -> None:
        assert _compute_accessibility_score([]) == 100.0

    def test_one_violation(self) -> None:
        assert _compute_accessibility_score([_make_issue()]) == 85.0

    def test_clamps_to_zero(self) -> None:
        issues = [_make_issue() for _ in range(10)]
        assert _compute_accessibility_score(issues) == 0.0


class TestCalculateDQS:
    def test_perfect_deck(self) -> None:
        """A deck with no issues and perfect vision scores gets DQS 100."""
        rule_issues = [SlideIssueSet(slide_index=0, issues=[])]
        vision_scores = [_perfect_vision()]
        report = calculate_dqs(rule_issues, vision_scores, [])

        assert len(report.slides) == 1
        slide = report.slides[0]
        assert slide.rule_score == 100.0
        assert slide.vision_score == 100.0
        assert slide.accessibility_score == 100.0
        assert report.overall_dqs == 100.0

    def test_all_failing_deck(self) -> None:
        """A deck with max issues and worst vision gets DQS 0."""
        errors = [_make_issue(severity=Severity.error) for _ in range(15)]
        rule_issues = [SlideIssueSet(slide_index=0, issues=errors)]
        vision_scores = [_worst_vision()]
        acc_issues = [_make_issue(slide_index=0, evaluator="accessibility") for _ in range(10)]

        report = calculate_dqs(rule_issues, vision_scores, acc_issues)

        assert report.slides[0].rule_score == 0.0
        assert report.slides[0].vision_score == 0.0
        assert report.slides[0].accessibility_score == 0.0
        assert report.overall_dqs == 0.0

    def test_known_issues_deck(self) -> None:
        """Deck with specific known issues yields expected score."""
        # Slide 0: 2 errors (-20), mid vision, 1 accessibility violation (-15)
        rule_issues = [
            SlideIssueSet(
                slide_index=0,
                issues=[
                    _make_issue(severity=Severity.error),
                    _make_issue(severity=Severity.error),
                ],
            )
        ]
        vision_scores = [_mid_vision()]
        acc_issues = [_make_issue(slide_index=0, evaluator="accessibility")]

        report = calculate_dqs(rule_issues, vision_scores, acc_issues)
        slide = report.slides[0]

        assert slide.rule_score == 80.0       # 100 - 20
        assert slide.accessibility_score == 85.0  # 100 - 15
        # vision: (5-1)*100/9 ≈ 44.44
        expected_dqs = round(0.4 * 80.0 + 0.3 * slide.vision_score + 0.3 * 85.0, 2)
        assert slide.dqs == expected_dqs
        assert report.overall_dqs == expected_dqs

    def test_multi_slide_average(self) -> None:
        """Overall DQS is the average of per-slide DQS values."""
        rule_issues = [
            SlideIssueSet(slide_index=0, issues=[]),
            SlideIssueSet(
                slide_index=1,
                issues=[
                    _make_issue(slide_index=1, severity=Severity.error)
                    for _ in range(10)
                ],
            ),
        ]
        vision_scores = [_perfect_vision(), _perfect_vision()]
        report = calculate_dqs(rule_issues, vision_scores, [])

        assert report.slides[0].dqs == 100.0
        assert report.slides[1].rule_score == 0.0
        expected_overall = round((report.slides[0].dqs + report.slides[1].dqs) / 2, 2)
        assert report.overall_dqs == expected_overall

    def test_empty_deck(self) -> None:
        """Empty deck returns 0 overall DQS."""
        report = calculate_dqs([], [], [])
        assert report.slides == []
        assert report.overall_dqs == 0.0

    def test_report_serialization(self) -> None:
        """DQSReport can round-trip through JSON."""
        report = DQSReport(
            slides=[SlideDQS(
                slide_index=0, rule_score=80, vision_score=70,
                accessibility_score=90, dqs=80,
            )],
            overall_dqs=80,
        )
        json_str = report.model_dump_json()
        restored = DQSReport.model_validate_json(json_str)
        assert restored == report
