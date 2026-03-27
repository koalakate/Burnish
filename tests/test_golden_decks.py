"""Golden deck integration tests — regression gate for the check engine.

Each test parses a generated PPTX fixture through the full pipeline
(parse → rule engine → DQS) and asserts expected outcomes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.csm.brand import BrandRuleset
from services.ingestion.pptx_parser import parse_pptx
from services.rules.dqs import DQSReport, calculate_dqs
from services.rules.engine import RuleEngine
from services.rules.evaluators.accessibility import evaluate_accessibility
from services.rules.evaluators.color import evaluate_colors
from services.rules.evaluators.content import evaluate_content
from services.rules.evaluators.image import evaluate_images
from services.rules.evaluators.layout import evaluate_layout
from services.rules.evaluators.typography import evaluate_typography
from services.rules.models import SlideIssueSet
from services.vision.scorer import VisionScore

_GOLDEN = Path(__file__).parent / "golden_decks"
_BRAND_JSON = _GOLDEN / "sample_brand.json"


@pytest.fixture(autouse=True, scope="module")
def _generate_fixtures():
    """Ensure PPTX fixtures exist before the test module runs."""
    from tests.golden_decks.generate_fixtures import generate_all

    generate_all()


@pytest.fixture(scope="module")
def brand() -> BrandRuleset:
    return BrandRuleset.model_validate_json(_BRAND_JSON.read_text())


def _build_engine() -> RuleEngine:
    engine = RuleEngine()
    engine.register(evaluate_colors)
    engine.register(evaluate_typography)
    engine.register(evaluate_accessibility)
    engine.register(evaluate_images)
    engine.register(evaluate_layout)
    engine.register(evaluate_content)
    return engine


def _perfect_vision(slide_count: int) -> list[VisionScore]:
    """Return perfect vision scores to isolate rule-engine testing."""
    return [
        VisionScore(visual_quality=10, layout_balance=10, readability=10, overall_impression=10)
        for _ in range(slide_count)
    ]


def _run_pipeline(pptx_path: Path, brand: BrandRuleset) -> tuple[list[SlideIssueSet], DQSReport]:
    csm = parse_pptx(pptx_path)
    engine = _build_engine()
    rule_issues = engine.run(csm, brand)

    # Extract accessibility issues for DQS
    acc_issues = [
        issue
        for slide_set in rule_issues
        for issue in slide_set.issues
        if issue.evaluator == "accessibility"
    ]

    vision_scores = _perfect_vision(len(csm.slides))
    dqs_report = calculate_dqs(rule_issues, vision_scores, acc_issues)
    return rule_issues, dqs_report


# -------------------------------------------------------------------
# brand_violations.pptx
# -------------------------------------------------------------------
class TestBrandViolations:
    @pytest.fixture(autouse=True, scope="class")
    def _run(self, brand):
        pptx = _GOLDEN / "brand_violations.pptx"
        issues, report = _run_pipeline(pptx, brand)
        self.__class__._issues = issues
        self.__class__._report = report

    def test_off_brand_color_detected(self):
        """Slide 0 has bright red text — should trigger color evaluator."""
        slide0_issues = self._issues[0].issues
        color_issues = [i for i in slide0_issues if i.evaluator == "color"]
        assert len(color_issues) > 0, "Expected color compliance issue for off-brand red"

    def test_wrong_font_detected(self):
        """Slide 1 has Comic Sans — should trigger typography evaluator."""
        slide1_issues = self._issues[1].issues
        typo_issues = [i for i in slide1_issues if i.evaluator == "typography"]
        font_family_issues = [
            i for i in typo_issues if "Comic Sans" in i.message
        ]
        assert len(font_family_issues) > 0, "Expected font-family issue for Comic Sans"

    def test_undersized_title_detected(self):
        """Slide with title layout has 10pt title — should trigger size warning."""
        # The title-layout slide is index 2 or 3 depending on fixture structure.
        # Check all slides for a typography size issue.
        all_issues = [
            i
            for ss in self._issues
            for i in ss.issues
            if i.evaluator == "typography" and "size" in i.message.lower()
        ]
        assert len(all_issues) > 0, "Expected font-size issue for undersized title"

    def test_dqs_below_perfect(self):
        """Brand violations should drag DQS below 100 (perfect vision inflates scores)."""
        assert self._report.overall_dqs < 100


# -------------------------------------------------------------------
# accessibility_fails.pptx
# -------------------------------------------------------------------
class TestAccessibilityFails:
    @pytest.fixture(autouse=True, scope="class")
    def _run(self, brand):
        pptx = _GOLDEN / "accessibility_fails.pptx"
        issues, report = _run_pipeline(pptx, brand)
        self.__class__._issues = issues
        self.__class__._report = report

    def test_low_contrast_detected(self):
        """Slide 0 has light gray on white — should fail WCAG AA."""
        slide0_issues = self._issues[0].issues
        acc_issues = [i for i in slide0_issues if i.evaluator == "accessibility"]
        assert len(acc_issues) > 0, "Expected accessibility issue for low contrast"

    def test_missing_alt_text_detected(self):
        """Slide 1 has an image without alt text."""
        slide1_issues = self._issues[1].issues
        img_issues = [
            i for i in slide1_issues
            if i.evaluator == "image" and "alt" in i.message.lower()
        ]
        assert len(img_issues) > 0, "Expected image issue for missing alt text"

    def test_dark_on_dark_detected(self):
        """Slide 2 has dark text on dark background — should fail WCAG AA."""
        slide2_issues = self._issues[2].issues
        acc_issues = [i for i in slide2_issues if i.evaluator == "accessibility"]
        assert len(acc_issues) > 0, "Expected accessibility issue for dark-on-dark"

    def test_dqs_penalized_for_accessibility(self):
        """Accessibility failures should lower the DQS below 100."""
        assert self._report.overall_dqs < 100


# -------------------------------------------------------------------
# layout_issues.pptx
# -------------------------------------------------------------------
class TestLayoutIssues:
    @pytest.fixture(autouse=True, scope="class")
    def _run(self, brand):
        pptx = _GOLDEN / "layout_issues.pptx"
        issues, report = _run_pipeline(pptx, brand)
        self.__class__._issues = issues
        self.__class__._report = report

    def test_overcrowded_slide_detected(self):
        """Slide 0 has 12 elements — should exceed max_elements_per_slide (10)."""
        slide0_issues = self._issues[0].issues
        layout_issues = [i for i in slide0_issues if i.evaluator == "layout"]
        crowd_issues = [i for i in layout_issues if "element" in i.message.lower()]
        assert len(crowd_issues) > 0, "Expected layout issue for overcrowded slide"

    def test_margin_violation_detected(self):
        """Slide 1 has an element at 0.1 inches — inside the 0.75-inch margin."""
        slide1_issues = self._issues[1].issues
        layout_issues = [i for i in slide1_issues if i.evaluator == "layout"]
        margin_issues = [
            i for i in layout_issues
            if "edge" in i.message.lower() or "margin" in i.message.lower()
        ]
        assert len(margin_issues) > 0, "Expected layout issue for margin violation"

    def test_excessive_bullets_detected(self):
        """Slide 2 has 9 bullets — exceeds max_bullets (7)."""
        slide2_issues = self._issues[2].issues
        content_issues = [i for i in slide2_issues if i.evaluator == "content"]
        bullet_issues = [i for i in content_issues if "bullet" in i.message.lower()]
        assert len(bullet_issues) > 0, "Expected content issue for excessive bullets"

    def test_dqs_reflects_layout_problems(self):
        assert self._report.overall_dqs < 95


# -------------------------------------------------------------------
# clean_deck.pptx
# -------------------------------------------------------------------
class TestCleanDeck:
    @pytest.fixture(autouse=True, scope="class")
    def _run(self, brand):
        pptx = _GOLDEN / "clean_deck.pptx"
        issues, report = _run_pipeline(pptx, brand)
        self.__class__._issues = issues
        self.__class__._report = report

    def test_no_error_issues(self):
        """A clean deck should have zero error-severity issues."""
        errors = [
            i
            for ss in self._issues
            for i in ss.issues
            if i.severity == "error"
        ]
        assert len(errors) == 0, f"Clean deck has unexpected errors: {errors}"

    def test_dqs_at_least_95(self):
        """Clean deck with perfect vision scores should reach DQS >= 95."""
        assert self._report.overall_dqs >= 95, (
            f"Expected DQS >= 95 for clean deck, got {self._report.overall_dqs}"
        )

    def test_all_slides_scored(self):
        """Every slide should have a DQS entry."""
        csm = parse_pptx(_GOLDEN / "clean_deck.pptx")
        assert len(self._report.slides) == len(csm.slides)


# -------------------------------------------------------------------
# Full pipeline smoke test
# -------------------------------------------------------------------
def test_all_fixtures_parseable(brand):
    """Every generated fixture should parse without error."""
    for name in ("brand_violations", "accessibility_fails", "layout_issues", "clean_deck"):
        pptx = _GOLDEN / f"{name}.pptx"
        csm = parse_pptx(pptx)
        assert len(csm.slides) > 0, f"{name}.pptx parsed to empty CSM"


def test_engine_returns_one_issue_set_per_slide(brand):
    """Rule engine output should have one SlideIssueSet per slide."""
    for name in ("brand_violations", "accessibility_fails", "layout_issues", "clean_deck"):
        pptx = _GOLDEN / f"{name}.pptx"
        csm = parse_pptx(pptx)
        engine = _build_engine()
        result = engine.run(csm, brand)
        assert len(result) == len(csm.slides), (
            f"{name}: expected {len(csm.slides)} issue sets, got {len(result)}"
        )
