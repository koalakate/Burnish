"""Tests for the rule engine skeleton and Issue model."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from packages.csm.brand import BrandRuleset
from packages.csm.models import (
    BoundingBox,
    CSM,
    Slide,
    TextElement,
)

from services.rules.engine import RuleEngine
from services.rules.models import Issue, Severity, SlideIssueSet


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_slide(index: int = 0) -> Slide:
    return Slide(
        index=index,
        elements=[
            TextElement(
                id="txt1",
                name="Title",
                bbox=BoundingBox(x=0, y=0, width=100, height=50),
                role="title",
            )
        ],
    )


def _make_csm(slide_count: int = 2) -> CSM:
    return CSM(
        slides=[_make_slide(i) for i in range(slide_count)],
        width=960,
        height=540,
    )


def _dummy_evaluator(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Always returns one issue per slide."""
    return [
        Issue(
            id=f"dummy-{slide.index}",
            slide_index=slide.index,
            element_id="txt1",
            evaluator="dummy",
            severity=Severity.warning,
            message="This is a dummy issue.",
            details={"reason": "testing"},
            bbox=BoundingBox(x=0, y=0, width=100, height=50),
        )
    ]


def _noop_evaluator(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Returns no issues."""
    return []


# ---------------------------------------------------------------------------
# Issue model tests
# ---------------------------------------------------------------------------


class TestIssueModel:
    def test_issue_construction(self) -> None:
        issue = Issue(
            id="color-001",
            slide_index=0,
            element_id="shape5",
            evaluator="color",
            severity=Severity.error,
            message="Off-brand color",
        )
        assert issue.id == "color-001"
        assert issue.severity == Severity.error
        assert issue.details == {}
        assert issue.bbox is None

    def test_issue_json_round_trip(self) -> None:
        issue = Issue(
            id="typo-002",
            slide_index=1,
            element_id="txt3",
            evaluator="typography",
            severity=Severity.info,
            message="Font weight not in range",
            details={"weight": 300, "allowed_min": 400},
            bbox=BoundingBox(x=10, y=20, width=200, height=30),
        )
        json_str = issue.model_dump_json()
        issue2 = Issue.model_validate_json(json_str)
        assert issue2 == issue

    def test_severity_values(self) -> None:
        assert Severity.error.value == "error"
        assert Severity.warning.value == "warning"
        assert Severity.info.value == "info"

    def test_issue_negative_slide_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Issue(
                id="bad",
                slide_index=-1,
                evaluator="test",
                severity=Severity.error,
                message="nope",
            )


class TestSlideIssueSet:
    def test_construction(self) -> None:
        issue_set = SlideIssueSet(slide_index=0, issues=[])
        assert issue_set.slide_index == 0
        assert issue_set.issues == []

    def test_json_round_trip(self) -> None:
        issues = [
            Issue(
                id="a",
                slide_index=0,
                evaluator="test",
                severity=Severity.warning,
                message="msg",
            )
        ]
        sis = SlideIssueSet(slide_index=0, issues=issues)
        json_str = sis.model_dump_json()
        sis2 = SlideIssueSet.model_validate_json(json_str)
        assert sis2 == sis


# ---------------------------------------------------------------------------
# RuleEngine tests
# ---------------------------------------------------------------------------


class TestRuleEngine:
    def test_engine_with_dummy_evaluator(self) -> None:
        engine = RuleEngine(evaluators=[_dummy_evaluator])
        csm = _make_csm(slide_count=2)
        brand = BrandRuleset()

        result = engine.run(csm, brand)

        assert len(result) == 2
        assert all(isinstance(s, SlideIssueSet) for s in result)
        assert result[0].slide_index == 0
        assert result[1].slide_index == 1
        assert len(result[0].issues) == 1
        assert result[0].issues[0].evaluator == "dummy"
        assert result[0].issues[0].severity == Severity.warning

    def test_engine_no_evaluators(self) -> None:
        engine = RuleEngine()
        csm = _make_csm(slide_count=1)
        brand = BrandRuleset()

        result = engine.run(csm, brand)

        assert len(result) == 1
        assert result[0].issues == []

    def test_engine_register(self) -> None:
        engine = RuleEngine()
        engine.register(_dummy_evaluator)
        csm = _make_csm(slide_count=1)
        brand = BrandRuleset()

        result = engine.run(csm, brand)
        assert len(result[0].issues) == 1

    def test_engine_multiple_evaluators(self) -> None:
        engine = RuleEngine(evaluators=[_dummy_evaluator, _noop_evaluator])
        csm = _make_csm(slide_count=1)
        brand = BrandRuleset()

        result = engine.run(csm, brand)
        assert len(result[0].issues) == 1

    def test_engine_deduplicates_issues(self) -> None:
        """Two evaluators returning the same issue ID should be deduplicated."""
        engine = RuleEngine(evaluators=[_dummy_evaluator, _dummy_evaluator])
        csm = _make_csm(slide_count=1)
        brand = BrandRuleset()

        result = engine.run(csm, brand)
        assert len(result[0].issues) == 1

    def test_engine_empty_csm(self) -> None:
        engine = RuleEngine(evaluators=[_dummy_evaluator])
        csm = CSM()
        brand = BrandRuleset()

        result = engine.run(csm, brand)
        assert result == []

    def test_engine_async(self) -> None:
        engine = RuleEngine(evaluators=[_dummy_evaluator])
        csm = _make_csm(slide_count=3)
        brand = BrandRuleset()

        result = asyncio.run(engine.run_async(csm, brand))

        assert len(result) == 3
        for i, slide_set in enumerate(result):
            assert slide_set.slide_index == i
            assert len(slide_set.issues) == 1
