"""Tests for the layout evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset, LayoutRules
from packages.csm.models import (
    BoundingBox,
    Font,
    Paragraph,
    Slide,
    TextElement,
    TextRun,
)
from services.rules.evaluators.layout import evaluate_layout, _EMU_PER_INCH
from services.rules.models import Severity


def _brand(
    margin: float = 0.5,
    max_elements: int = 12,
    grid_pt: float = 0.0,
) -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        layout_rules=LayoutRules(
            margin_left=margin,
            margin_right=margin,
            margin_top=margin,
            margin_bottom=margin,
            max_elements_per_slide=max_elements,
            alignment_grid_pt=grid_pt,
        ),
    )


def _text_elem(id: str, x: float, y: float, w: float = 100000, h: float = 50000) -> TextElement:
    return TextElement(
        id=id,
        name=f"Element {id}",
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
        paragraphs=[Paragraph(runs=[TextRun(text="Hello")])],
    )


# ---------------------------------------------------------------------------
# Margin checks
# ---------------------------------------------------------------------------


class TestMargins:
    def test_element_within_margins_passes(self):
        """Elements inside the margin area should produce no issues."""
        brand = _brand(margin=0.5)
        # Place element at 1 inch from left and top — well within margins
        slide = Slide(index=0, elements=[_text_elem("e1", _EMU_PER_INCH, _EMU_PER_INCH)])
        issues = evaluate_layout(slide, brand)
        margin_issues = [i for i in issues if i.details.get("check") == "margin"]
        assert len(margin_issues) == 0

    def test_element_too_close_to_left_edge(self):
        """An element closer than the left margin should emit a warning."""
        brand = _brand(margin=0.5)
        # Place element at 0.2 inches from left — violates 0.5" margin
        slide = Slide(index=0, elements=[_text_elem("e1", 0.2 * _EMU_PER_INCH, _EMU_PER_INCH)])
        issues = evaluate_layout(slide, brand)
        margin_issues = [i for i in issues if i.details.get("check") == "margin" and i.details.get("side") == "left"]
        assert len(margin_issues) == 1
        assert margin_issues[0].severity == Severity.warning

    def test_element_too_close_to_top_edge(self):
        """An element closer than the top margin should emit a warning."""
        brand = _brand(margin=0.5)
        slide = Slide(index=0, elements=[_text_elem("e1", _EMU_PER_INCH, 0.1 * _EMU_PER_INCH)])
        issues = evaluate_layout(slide, brand)
        margin_issues = [i for i in issues if i.details.get("check") == "margin" and i.details.get("side") == "top"]
        assert len(margin_issues) == 1

    def test_element_at_origin_violates_both_margins(self):
        """An element at (0, 0) violates both left and top margins."""
        brand = _brand(margin=0.5)
        slide = Slide(index=0, elements=[_text_elem("e1", 0, 0)])
        issues = evaluate_layout(slide, brand)
        margin_issues = [i for i in issues if i.details.get("check") == "margin"]
        sides = {i.details["side"] for i in margin_issues}
        assert "left" in sides
        assert "top" in sides

    def test_zero_margin_no_violations(self):
        """With zero margins, no margin violations should occur."""
        brand = _brand(margin=0.0)
        slide = Slide(index=0, elements=[_text_elem("e1", 0, 0)])
        issues = evaluate_layout(slide, brand)
        margin_issues = [i for i in issues if i.details.get("check") == "margin"]
        assert len(margin_issues) == 0


# ---------------------------------------------------------------------------
# Element count checks
# ---------------------------------------------------------------------------


class TestElementCount:
    def test_under_limit_passes(self):
        """A slide with fewer elements than the limit should pass."""
        brand = _brand(max_elements=5)
        slide = Slide(
            index=0,
            elements=[_text_elem(f"e{i}", _EMU_PER_INCH, _EMU_PER_INCH) for i in range(3)],
        )
        issues = evaluate_layout(slide, brand)
        count_issues = [i for i in issues if i.details.get("check") == "element_count"]
        assert len(count_issues) == 0

    def test_at_limit_passes(self):
        """A slide with exactly the maximum element count should pass."""
        brand = _brand(max_elements=3)
        slide = Slide(
            index=0,
            elements=[_text_elem(f"e{i}", _EMU_PER_INCH, _EMU_PER_INCH) for i in range(3)],
        )
        issues = evaluate_layout(slide, brand)
        count_issues = [i for i in issues if i.details.get("check") == "element_count"]
        assert len(count_issues) == 0

    def test_over_limit_emits_warning(self):
        """A slide exceeding the element limit should emit a warning."""
        brand = _brand(max_elements=2)
        slide = Slide(
            index=0,
            elements=[_text_elem(f"e{i}", _EMU_PER_INCH, _EMU_PER_INCH) for i in range(5)],
        )
        issues = evaluate_layout(slide, brand)
        count_issues = [i for i in issues if i.details.get("check") == "element_count"]
        assert len(count_issues) == 1
        issue = count_issues[0]
        assert issue.severity == Severity.warning
        assert issue.details["actual_count"] == 5
        assert issue.details["max_count"] == 2


# ---------------------------------------------------------------------------
# Alignment grid checks
# ---------------------------------------------------------------------------


class TestAlignmentGrid:
    def test_no_grid_no_issues(self):
        """With grid_pt=0, no alignment issues should be raised."""
        brand = _brand(grid_pt=0.0)
        slide = Slide(index=0, elements=[_text_elem("e1", 12345, 67890)])
        issues = evaluate_layout(slide, brand)
        grid_issues = [i for i in issues if i.details.get("check") == "alignment_grid"]
        assert len(grid_issues) == 0

    def test_on_grid_passes(self):
        """Elements snapped to the grid should produce no issues."""
        grid_pt = 36.0  # 36pt grid
        grid_emu = grid_pt * 12_700
        brand = _brand(grid_pt=grid_pt)
        slide = Slide(index=0, elements=[_text_elem("e1", grid_emu * 3, grid_emu * 2)])
        issues = evaluate_layout(slide, brand)
        grid_issues = [i for i in issues if i.details.get("check") == "alignment_grid"]
        assert len(grid_issues) == 0

    def test_off_grid_emits_info(self):
        """Elements not snapped to the grid should emit info issues."""
        grid_pt = 36.0
        grid_emu = grid_pt * 12_700
        brand = _brand(grid_pt=grid_pt)
        # Place element halfway between grid lines
        offset = grid_emu * 2 + grid_emu / 2
        slide = Slide(index=0, elements=[_text_elem("e1", offset, offset)])
        issues = evaluate_layout(slide, brand)
        grid_issues = [i for i in issues if i.details.get("check") == "alignment_grid"]
        assert len(grid_issues) == 2  # x and y
        assert all(i.severity == Severity.info for i in grid_issues)
        axes = {i.details["axis"] for i in grid_issues}
        assert axes == {"x", "y"}


# ---------------------------------------------------------------------------
# Combined and edge cases
# ---------------------------------------------------------------------------


class TestCombined:
    def test_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        brand = _brand(margin=0.5)
        slide = Slide(index=7, elements=[_text_elem("e1", 0, 0)])
        issues = evaluate_layout(slide, brand)
        assert all(i.slide_index == 7 for i in issues)

    def test_empty_slide_no_issues(self):
        """An empty slide should produce no layout issues."""
        brand = _brand()
        slide = Slide(index=0, elements=[])
        issues = evaluate_layout(slide, brand)
        assert len(issues) == 0
