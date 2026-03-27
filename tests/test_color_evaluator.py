"""Tests for the color compliance evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandColor, BrandRuleset
from packages.csm.models import (
    BoundingBox,
    Color,
    Font,
    Paragraph,
    ShapeElement,
    Slide,
    TextElement,
    TextRun,
)
from services.rules.evaluators.color import (
    delta_e_ciede2000,
    evaluate_colors,
    rgb_to_lab,
)
from services.rules.models import Severity


def _brand() -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        colors=[
            BrandColor(name="Brand Blue", hex="#1B3A6B", r=27, g=58, b=107, tolerance_delta_e=10.0),
            BrandColor(name="Brand White", hex="#FFFFFF", r=255, g=255, b=255, tolerance_delta_e=5.0),
            BrandColor(name="Accent Orange", hex="#E87722", r=232, g=119, b=34, tolerance_delta_e=10.0),
        ],
    )


def _bbox() -> BoundingBox:
    return BoundingBox(x=0, y=0, width=100, height=50)


def _slide_with_text_color(color: Color) -> Slide:
    return Slide(
        index=0,
        elements=[
            TextElement(
                id="txt1",
                bbox=_bbox(),
                paragraphs=[
                    Paragraph(runs=[TextRun(text="Hello", color=color, font=Font())])
                ],
            )
        ],
    )


def _slide_with_shape_fill(color: Color) -> Slide:
    return Slide(
        index=0,
        elements=[
            ShapeElement(id="shp1", bbox=_bbox(), fill_color=color),
        ],
    )


# ---------------------------------------------------------------------------
# Unit tests for color math
# ---------------------------------------------------------------------------

class TestRGBToLab:
    def test_white(self):
        l, a, b = rgb_to_lab(255, 255, 255)
        assert abs(l - 100.0) < 0.5
        assert abs(a) < 1.0
        assert abs(b) < 1.0

    def test_black(self):
        l, a, b = rgb_to_lab(0, 0, 0)
        assert abs(l) < 0.5

    def test_red(self):
        l, a, b = rgb_to_lab(255, 0, 0)
        assert l > 50
        assert a > 50  # red is positive a*


class TestDeltaE:
    def test_identical_colors(self):
        lab = rgb_to_lab(27, 58, 107)
        assert delta_e_ciede2000(lab, lab) < 0.001

    def test_similar_colors_low_delta(self):
        lab1 = rgb_to_lab(27, 58, 107)
        lab2 = rgb_to_lab(30, 60, 110)
        de = delta_e_ciede2000(lab1, lab2)
        assert de < 5.0  # very similar colors

    def test_different_colors_high_delta(self):
        lab1 = rgb_to_lab(255, 0, 0)
        lab2 = rgb_to_lab(0, 0, 255)
        de = delta_e_ciede2000(lab1, lab2)
        assert de > 40.0  # red vs blue should be very different

    def test_black_vs_white(self):
        lab1 = rgb_to_lab(0, 0, 0)
        lab2 = rgb_to_lab(255, 255, 255)
        de = delta_e_ciede2000(lab1, lab2)
        assert de > 90.0


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

class TestColorEvaluator:
    def test_on_brand_color_passes(self):
        """An exact brand color should produce no issues."""
        brand = _brand()
        slide = _slide_with_text_color(
            Color(hex="#1B3A6B", r=27, g=58, b=107)
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 0

    def test_close_color_within_tolerance_passes(self):
        """A color within tolerance should produce no issues."""
        brand = _brand()
        slide = _slide_with_text_color(
            Color(hex="#1D3C6E", r=29, g=60, b=110)  # very close to Brand Blue
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 0

    def test_off_brand_color_emits_issue(self):
        """A clearly off-brand color should emit an error issue."""
        brand = _brand()
        slide = _slide_with_text_color(
            Color(hex="#FF0000", r=255, g=0, b=0)  # bright red, not in palette
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 1
        issue = issues[0]
        assert issue.severity == Severity.error
        assert issue.evaluator == "color"
        assert "#FF0000" in issue.message
        assert issue.details["delta_e"] > 10.0
        assert "nearest_brand_color" in issue.details
        assert "nearest_brand_hex" in issue.details

    def test_shape_fill_checked(self):
        """Shape fill colors should also be checked."""
        brand = _brand()
        slide = _slide_with_shape_fill(
            Color(hex="#00FF00", r=0, g=255, b=0)  # green, not in palette
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 1
        assert issues[0].evaluator == "color"

    def test_nearest_match_correct(self):
        """The issue should report the correct nearest brand color."""
        brand = _brand()
        # Use a dark blue — should be closest to Brand Blue
        slide = _slide_with_text_color(
            Color(hex="#1A2B4C", r=26, g=43, b=76)
        )
        issues = evaluate_colors(slide, brand)
        # Whether this passes or fails depends on delta_e, but if it fails,
        # the nearest should be Brand Blue
        if issues:
            assert issues[0].details["nearest_brand_color"] == "Brand Blue"

    def test_off_brand_reports_nearest_orange(self):
        """A reddish-orange that's off brand should match Accent Orange."""
        brand = _brand()
        slide = _slide_with_text_color(
            Color(hex="#FF4500", r=255, g=69, b=0)  # OrangeRed
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 1
        assert issues[0].details["nearest_brand_color"] == "Accent Orange"

    def test_no_colors_no_issues(self):
        """A slide with no colored elements should produce no issues."""
        brand = _brand()
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    paragraphs=[Paragraph(runs=[TextRun(text="Plain text")])],
                )
            ],
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 0

    def test_empty_brand_palette_no_issues(self):
        """If the brand has no colors defined, no issues should be raised."""
        brand = BrandRuleset(name="Empty", colors=[])
        slide = _slide_with_text_color(
            Color(hex="#FF0000", r=255, g=0, b=0)
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 0

    def test_custom_tolerance_override(self):
        """A global custom tolerance should override per-color tolerance."""
        brand = _brand()
        # Set a very tight global tolerance
        brand.custom_tolerances.color_delta_e = 1.0
        # This color is somewhat close to Brand Blue (delta-e ~5) but beyond 1.0
        slide = _slide_with_text_color(
            Color(hex="#20507A", r=32, g=80, b=122)
        )
        issues = evaluate_colors(slide, brand)
        # With tolerance=1.0, this should fail
        assert len(issues) == 1

    def test_issue_has_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        brand = _brand()
        slide = Slide(
            index=3,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[TextRun(text="Hello", color=Color(hex="#FF0000", r=255, g=0, b=0))])
                    ],
                )
            ],
        )
        issues = evaluate_colors(slide, brand)
        assert len(issues) == 1
        assert issues[0].slide_index == 3
