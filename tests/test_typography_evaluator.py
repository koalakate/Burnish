"""Tests for the typography evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandFont, BrandRuleset, SizeRule
from packages.csm.models import (
    BoundingBox,
    Font,
    Paragraph,
    ShapeElement,
    Slide,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)
from services.rules.evaluators.typography import evaluate_typography
from services.rules.models import Severity


def _bbox() -> BoundingBox:
    return BoundingBox(x=0, y=0, width=100, height=50)


def _brand() -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        fonts=[
            BrandFont(family="Inter", weight_min=300, weight_max=700),
            BrandFont(family="Roboto", weight_min=400, weight_max=900),
        ],
        size_rules=[
            SizeRule(role="title", min_pt=24.0, max_pt=48.0),
            SizeRule(role="body", min_pt=12.0, max_pt=24.0),
            SizeRule(role="caption", min_pt=8.0, max_pt=14.0),
        ],
    )


def _slide_with_text(
    font: Font,
    role: str | None = "body",
    text: str = "Hello world",
) -> Slide:
    return Slide(
        index=0,
        elements=[
            TextElement(
                id="txt1",
                bbox=_bbox(),
                role=role,
                paragraphs=[Paragraph(runs=[TextRun(text=text, font=font)])],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Font family checks
# ---------------------------------------------------------------------------


class TestFontFamily:
    def test_approved_font_passes(self):
        """An approved font family should produce no issues."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Inter", size_pt=14.0, weight=400))
        issues = evaluate_typography(slide, brand)
        assert len(issues) == 0

    def test_approved_font_case_insensitive(self):
        """Font matching should be case-insensitive."""
        brand = _brand()
        slide = _slide_with_text(Font(family="inter", size_pt=14.0, weight=400))
        issues = evaluate_typography(slide, brand)
        assert len(issues) == 0

    def test_unapproved_font_emits_error(self):
        """A font not in the approved list should emit an error."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Comic Sans", size_pt=14.0, weight=400))
        issues = evaluate_typography(slide, brand)
        family_issues = [i for i in issues if i.details.get("check") == "font_family"]
        assert len(family_issues) == 1
        issue = family_issues[0]
        assert issue.severity == Severity.error
        assert issue.evaluator == "typography"
        assert "Comic Sans" in issue.message
        assert "'Inter'" in issue.message
        assert "'Roboto'" in issue.message
        assert issue.details["actual_family"] == "Comic Sans"

    def test_no_font_family_no_issue(self):
        """A run with no font family set should not produce a family issue."""
        brand = _brand()
        slide = _slide_with_text(Font(family=None, size_pt=14.0))
        issues = evaluate_typography(slide, brand)
        family_issues = [i for i in issues if i.details.get("check") == "font_family"]
        assert len(family_issues) == 0

    def test_empty_brand_fonts_no_issues(self):
        """If no brand fonts are defined, no issues should be raised."""
        brand = BrandRuleset(name="Empty", fonts=[])
        slide = _slide_with_text(Font(family="Comic Sans", size_pt=14.0))
        issues = evaluate_typography(slide, brand)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Font size checks
# ---------------------------------------------------------------------------


class TestFontSize:
    def test_size_within_range_passes(self):
        """A font size within the allowed range should produce no issues."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=16.0, weight=400), role="body"
        )
        issues = evaluate_typography(slide, brand)
        assert len(issues) == 0

    def test_size_below_minimum_emits_warning(self):
        """A font size below the minimum for the role should emit a warning."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=10.0, weight=400), role="body"
        )
        issues = evaluate_typography(slide, brand)
        size_issues = [i for i in issues if i.details.get("check") == "font_size"]
        assert len(size_issues) == 1
        issue = size_issues[0]
        assert issue.severity == Severity.warning
        assert "10.0pt" in issue.message
        assert "12.0pt" in issue.message
        assert issue.details["role"] == "body"

    def test_size_above_maximum_emits_warning(self):
        """A font size above the maximum for the role should emit a warning."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=60.0, weight=400), role="title"
        )
        issues = evaluate_typography(slide, brand)
        size_issues = [i for i in issues if i.details.get("check") == "font_size"]
        assert len(size_issues) == 1
        assert size_issues[0].severity == Severity.warning
        assert "60.0pt" in size_issues[0].message

    def test_no_role_skips_size_check(self):
        """Elements without a role should not be checked for size."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=4.0, weight=400), role=None
        )
        issues = evaluate_typography(slide, brand)
        size_issues = [i for i in issues if i.details.get("check") == "font_size"]
        assert len(size_issues) == 0

    def test_no_size_skips_size_check(self):
        """Runs without a font size set should not be checked for size."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=None, weight=400), role="body"
        )
        issues = evaluate_typography(slide, brand)
        size_issues = [i for i in issues if i.details.get("check") == "font_size"]
        assert len(size_issues) == 0

    def test_title_size_check(self):
        """Title text below 24pt should emit a warning."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Inter", size_pt=18.0, weight=400), role="title"
        )
        issues = evaluate_typography(slide, brand)
        size_issues = [i for i in issues if i.details.get("check") == "font_size"]
        assert len(size_issues) == 1
        assert "title" in size_issues[0].message


# ---------------------------------------------------------------------------
# Font weight checks
# ---------------------------------------------------------------------------


class TestFontWeight:
    def test_weight_within_range_passes(self):
        """A font weight within the approved range should produce no issues."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Inter", size_pt=14.0, weight=400))
        issues = evaluate_typography(slide, brand)
        assert len(issues) == 0

    def test_weight_outside_range_emits_info(self):
        """A font weight outside the approved range should emit an info issue."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Inter", size_pt=14.0, weight=100))
        issues = evaluate_typography(slide, brand)
        weight_issues = [i for i in issues if i.details.get("check") == "font_weight"]
        assert len(weight_issues) == 1
        issue = weight_issues[0]
        assert issue.severity == Severity.info
        assert "100" in issue.message
        assert "300" in issue.message
        assert "700" in issue.message

    def test_weight_not_checked_for_unapproved_font(self):
        """Weight should not be checked if the font family is unapproved."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Comic Sans", size_pt=14.0, weight=100))
        issues = evaluate_typography(slide, brand)
        weight_issues = [i for i in issues if i.details.get("check") == "font_weight"]
        assert len(weight_issues) == 0

    def test_no_weight_skips_check(self):
        """Runs without a font weight set should not be checked for weight."""
        brand = _brand()
        slide = _slide_with_text(Font(family="Inter", size_pt=14.0, weight=None))
        issues = evaluate_typography(slide, brand)
        weight_issues = [i for i in issues if i.details.get("check") == "font_weight"]
        assert len(weight_issues) == 0


# ---------------------------------------------------------------------------
# Shape and table text coverage
# ---------------------------------------------------------------------------


class TestShapeAndTableText:
    def test_shape_text_checked(self):
        """Text inside shapes should be checked for font compliance."""
        brand = _brand()
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="shp1",
                    bbox=_bbox(),
                    paragraphs=[
                        Paragraph(
                            runs=[
                                TextRun(
                                    text="Shape text",
                                    font=Font(family="Comic Sans", size_pt=14.0),
                                )
                            ]
                        )
                    ],
                )
            ],
        )
        issues = evaluate_typography(slide, brand)
        family_issues = [i for i in issues if i.details.get("check") == "font_family"]
        assert len(family_issues) == 1

    def test_table_text_checked(self):
        """Text inside table cells should be checked for font compliance."""
        brand = _brand()
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
                            paragraphs=[
                                Paragraph(
                                    runs=[
                                        TextRun(
                                            text="Cell text",
                                            font=Font(family="Arial", size_pt=12.0),
                                        )
                                    ]
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        issues = evaluate_typography(slide, brand)
        family_issues = [i for i in issues if i.details.get("check") == "font_family"]
        assert len(family_issues) == 1


# ---------------------------------------------------------------------------
# Combined checks
# ---------------------------------------------------------------------------


class TestCombinedChecks:
    def test_multiple_issues_on_single_run(self):
        """A run can have both wrong font and wrong weight (though weight
        is only checked for approved fonts, so this tests wrong font + wrong size)."""
        brand = _brand()
        slide = _slide_with_text(
            Font(family="Comic Sans", size_pt=6.0, weight=400), role="body"
        )
        issues = evaluate_typography(slide, brand)
        checks = {i.details.get("check") for i in issues}
        assert "font_family" in checks
        assert "font_size" in checks

    def test_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        brand = _brand()
        slide = Slide(
            index=5,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=_bbox(),
                    role="body",
                    paragraphs=[
                        Paragraph(
                            runs=[
                                TextRun(
                                    text="Hello",
                                    font=Font(family="Comic Sans", size_pt=14.0),
                                )
                            ]
                        )
                    ],
                )
            ],
        )
        issues = evaluate_typography(slide, brand)
        assert all(i.slide_index == 5 for i in issues)
