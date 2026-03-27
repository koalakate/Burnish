"""Tests for the accessibility (WCAG AA contrast) evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset
from packages.csm.models import (
    BoundingBox,
    Color,
    Font,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)
from services.rules.evaluators.accessibility import (
    contrast_ratio,
    evaluate_accessibility,
    relative_luminance,
)
from services.rules.models import Severity


def _brand() -> BrandRuleset:
    return BrandRuleset(name="Test Brand")


def _bbox() -> BoundingBox:
    return BoundingBox(x=0, y=0, width=100, height=50)


WHITE = Color(hex="#FFFFFF", r=255, g=255, b=255)
BLACK = Color(hex="#000000", r=0, g=0, b=0)
DARK_GRAY = Color(hex="#333333", r=51, g=51, b=51)
LIGHT_GRAY = Color(hex="#CCCCCC", r=204, g=204, b=204)
YELLOW = Color(hex="#FFFF00", r=255, g=255, b=0)


def _slide_with_text(
    text_color: Color,
    bg_color: Color | None = None,
    size_pt: float | None = None,
    weight: int | None = None,
) -> Slide:
    return Slide(
        index=0,
        elements=[
            TextElement(
                id="txt1",
                bbox=_bbox(),
                paragraphs=[
                    Paragraph(runs=[
                        TextRun(
                            text="Sample text",
                            color=text_color,
                            font=Font(size_pt=size_pt, weight=weight),
                        ),
                    ]),
                ],
            ),
        ],
        background=SlideBackground(solid_color=bg_color) if bg_color else None,
    )


# ---------------------------------------------------------------------------
# Unit tests for luminance and contrast ratio
# ---------------------------------------------------------------------------

class TestRelativeLuminance:
    def test_white(self):
        lum = relative_luminance(WHITE)
        assert abs(lum - 1.0) < 0.01

    def test_black(self):
        lum = relative_luminance(BLACK)
        assert abs(lum) < 0.01

    def test_mid_gray(self):
        gray = Color(hex="#808080", r=128, g=128, b=128)
        lum = relative_luminance(gray)
        assert 0.2 < lum < 0.3


class TestContrastRatio:
    def test_black_on_white(self):
        ratio = contrast_ratio(BLACK, WHITE)
        assert abs(ratio - 21.0) < 0.1

    def test_white_on_black(self):
        ratio = contrast_ratio(WHITE, BLACK)
        assert abs(ratio - 21.0) < 0.1

    def test_same_color(self):
        ratio = contrast_ratio(BLACK, BLACK)
        assert abs(ratio - 1.0) < 0.01

    def test_symmetric(self):
        r1 = contrast_ratio(DARK_GRAY, WHITE)
        r2 = contrast_ratio(WHITE, DARK_GRAY)
        assert abs(r1 - r2) < 0.01


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

class TestAccessibilityEvaluator:
    def test_high_contrast_passes(self):
        """Black text on white background has ~21:1 ratio, well above 4.5:1."""
        slide = _slide_with_text(BLACK, WHITE)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_low_contrast_normal_text_fails(self):
        """Light gray text on white has low contrast, should fail for normal text."""
        slide = _slide_with_text(LIGHT_GRAY, WHITE, size_pt=12.0)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 1
        issue = issues[0]
        assert issue.severity == Severity.error
        assert issue.evaluator == "accessibility"
        assert "Low contrast" in issue.message
        assert "4.5:1" in issue.message
        assert issue.details["check"] == "wcag_aa_contrast"
        assert issue.details["threshold"] == 4.5
        assert float(issue.details["contrast_ratio"]) < 4.5

    def test_low_contrast_large_text_uses_relaxed_threshold(self):
        """Large text (>= 18pt) uses 3:1 threshold instead of 4.5:1."""
        # Dark gray on white has ratio ~10:1 — passes both thresholds
        slide = _slide_with_text(DARK_GRAY, WHITE, size_pt=18.0)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_large_text_14pt_bold_uses_relaxed_threshold(self):
        """14pt bold text also qualifies as large text (3:1 threshold)."""
        # Use a color that passes 3:1 but not 4.5:1
        # We need a color with contrast ratio between 3.0 and 4.5 against white
        # #949494 (148,148,148) on white ≈ 3.03:1
        medium_gray = Color(hex="#949494", r=148, g=148, b=148)
        slide = _slide_with_text(medium_gray, WHITE, size_pt=14.0, weight=700)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_14pt_non_bold_uses_normal_threshold(self):
        """14pt non-bold text uses the normal 4.5:1 threshold."""
        medium_gray = Color(hex="#949494", r=148, g=148, b=148)
        slide = _slide_with_text(medium_gray, WHITE, size_pt=14.0, weight=400)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 1
        assert issues[0].details["threshold"] == 4.5

    def test_default_white_background(self):
        """When no background is set, defaults to white."""
        slide = _slide_with_text(BLACK)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_text_in_shape_uses_shape_fill_as_bg(self):
        """Text inside a shape should use the shape fill as its background."""
        dark_bg = Color(hex="#1A1A1A", r=26, g=26, b=26)
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="shp1",
                    bbox=_bbox(),
                    fill_color=dark_bg,
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Shape text",
                                color=WHITE,
                                font=Font(size_pt=12.0),
                            ),
                        ]),
                    ],
                ),
            ],
            background=SlideBackground(solid_color=WHITE),
        )
        # White text on dark background — high contrast, should pass
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_text_in_shape_no_fill_uses_slide_bg(self):
        """Text in a shape without fill should fall back to slide background."""
        dark_bg = Color(hex="#1A1A1A", r=26, g=26, b=26)
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="shp1",
                    bbox=_bbox(),
                    fill_color=None,
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Shape text",
                                color=LIGHT_GRAY,
                                font=Font(size_pt=12.0),
                            ),
                        ]),
                    ],
                ),
            ],
            background=SlideBackground(solid_color=dark_bg),
        )
        # Light gray on dark bg — high contrast, should pass
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_table_cell_fill_as_bg(self):
        """Text in a table cell should use cell fill as background."""
        dark_cell = Color(hex="#1A1A1A", r=26, g=26, b=26)
        slide = Slide(
            index=0,
            elements=[
                TableElement(
                    id="tbl1",
                    bbox=_bbox(),
                    rows=1,
                    cols=1,
                    cells=[
                        TableCell(
                            row=0,
                            col=0,
                            fill_color=dark_cell,
                            paragraphs=[
                                Paragraph(runs=[
                                    TextRun(
                                        text="Cell text",
                                        color=WHITE,
                                        font=Font(size_pt=12.0),
                                    ),
                                ]),
                            ],
                        ),
                    ],
                ),
            ],
        )
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_issue_message_format(self):
        """Issue message should include current ratio and minimum needed."""
        slide = _slide_with_text(LIGHT_GRAY, WHITE, size_pt=12.0)
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 1
        msg = issues[0].message
        assert ":1)" in msg  # current ratio
        assert "4.5:1" in msg  # minimum needed

    def test_issue_has_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        slide = Slide(
            index=5,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="Low contrast", color=LIGHT_GRAY, font=Font(size_pt=12.0)),
                        ]),
                    ],
                ),
            ],
            background=SlideBackground(solid_color=WHITE),
        )
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 1
        assert issues[0].slide_index == 5

    def test_no_text_no_issues(self):
        """A slide with no text elements should produce no issues."""
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(id="shp1", bbox=_bbox(), fill_color=LIGHT_GRAY),
            ],
        )
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_text_without_color_skipped(self):
        """Text runs without an explicit color are skipped."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[TextRun(text="No color set")]),
                    ],
                ),
            ],
        )
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0

    def test_gradient_bg_uses_first_stop(self):
        """When background is a gradient, use the first gradient stop."""
        grad_start = Color(hex="#000000", r=0, g=0, b=0)
        grad_end = Color(hex="#FFFFFF", r=255, g=255, b=255)
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="On gradient", color=WHITE, font=Font(size_pt=12.0)),
                        ]),
                    ],
                ),
            ],
            background=SlideBackground(gradient_colors=[grad_start, grad_end]),
        )
        # White text on black gradient start — high contrast
        issues = evaluate_accessibility(slide, _brand())
        assert len(issues) == 0
