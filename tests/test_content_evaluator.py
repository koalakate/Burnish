"""Tests for the content evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset, CustomTolerances
from packages.csm.models import (
    BoundingBox,
    Font,
    Paragraph,
    Slide,
    TextElement,
    TextRun,
)
from services.rules.evaluators.content import evaluate_content
from services.rules.models import Severity


def _bbox() -> BoundingBox:
    return BoundingBox(x=0, y=0, width=100, height=50)


def _brand(max_words: int | None = None, max_bullets: int | None = None) -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        custom_tolerances=CustomTolerances(
            max_words_per_slide=max_words,
            max_bullets_per_slide=max_bullets,
        ),
    )


def _text_elem(
    id: str,
    paragraphs: list[Paragraph],
    role: str | None = "body",
    name: str = "",
) -> TextElement:
    return TextElement(
        id=id,
        name=name or f"Element {id}",
        bbox=_bbox(),
        role=role,
        paragraphs=paragraphs,
    )


def _para(text: str, level: int = 0) -> Paragraph:
    return Paragraph(runs=[TextRun(text=text, font=Font())], level=level)


# ---------------------------------------------------------------------------
# Text density checks
# ---------------------------------------------------------------------------


class TestTextDensity:
    def test_under_limit_passes(self):
        """A slide with few words should produce no density issues."""
        brand = _brand(max_words=50)
        slide = Slide(
            index=0,
            elements=[_text_elem("t1", [_para("Hello world")])],
        )
        issues = evaluate_content(slide, brand)
        density_issues = [i for i in issues if i.details.get("check") == "text_density"]
        assert len(density_issues) == 0

    def test_over_limit_emits_warning(self):
        """A slide exceeding the word limit should emit a warning."""
        brand = _brand(max_words=5)
        slide = Slide(
            index=0,
            elements=[_text_elem("t1", [_para("one two three four five six seven")])],
        )
        issues = evaluate_content(slide, brand)
        density_issues = [i for i in issues if i.details.get("check") == "text_density"]
        assert len(density_issues) == 1
        assert density_issues[0].severity == Severity.warning
        assert density_issues[0].details["actual_words"] == 7
        assert density_issues[0].details["max_words"] == 5

    def test_default_limit_is_150(self):
        """Without a custom tolerance, the default limit should be 150 words."""
        brand = _brand()  # no custom max_words
        words = " ".join(f"word{i}" for i in range(151))
        slide = Slide(
            index=0,
            elements=[_text_elem("t1", [_para(words)])],
        )
        issues = evaluate_content(slide, brand)
        density_issues = [i for i in issues if i.details.get("check") == "text_density"]
        assert len(density_issues) == 1
        assert density_issues[0].details["max_words"] == 150


# ---------------------------------------------------------------------------
# Bullet count checks
# ---------------------------------------------------------------------------


class TestBulletCount:
    def test_under_limit_passes(self):
        """A text element with few bullets should pass."""
        brand = _brand(max_bullets=7)
        paras = [_para(f"Bullet {i}", level=1) for i in range(5)]
        slide = Slide(index=0, elements=[_text_elem("t1", paras)])
        issues = evaluate_content(slide, brand)
        bullet_issues = [i for i in issues if i.details.get("check") == "bullet_count"]
        assert len(bullet_issues) == 0

    def test_over_limit_emits_warning(self):
        """A text element with too many bullets should emit a warning."""
        brand = _brand(max_bullets=3)
        paras = [_para(f"Bullet {i}", level=1) for i in range(5)]
        slide = Slide(index=0, elements=[_text_elem("t1", paras)])
        issues = evaluate_content(slide, brand)
        bullet_issues = [i for i in issues if i.details.get("check") == "bullet_count"]
        assert len(bullet_issues) == 1
        assert bullet_issues[0].severity == Severity.warning
        assert bullet_issues[0].details["actual_bullets"] == 5

    def test_level_zero_not_counted_as_bullet(self):
        """Paragraphs at level 0 should not be counted as bullets."""
        brand = _brand(max_bullets=1)
        paras = [_para(f"Line {i}", level=0) for i in range(10)]
        slide = Slide(index=0, elements=[_text_elem("t1", paras)])
        issues = evaluate_content(slide, brand)
        bullet_issues = [i for i in issues if i.details.get("check") == "bullet_count"]
        assert len(bullet_issues) == 0

    def test_empty_bullets_not_counted(self):
        """Empty bullet paragraphs should not be counted."""
        brand = _brand(max_bullets=1)
        paras = [Paragraph(runs=[TextRun(text="   ")], level=1) for _ in range(5)]
        slide = Slide(index=0, elements=[_text_elem("t1", paras)])
        issues = evaluate_content(slide, brand)
        bullet_issues = [i for i in issues if i.details.get("check") == "bullet_count"]
        assert len(bullet_issues) == 0


# ---------------------------------------------------------------------------
# Empty placeholder checks
# ---------------------------------------------------------------------------


class TestEmptyPlaceholders:
    def test_non_empty_passes(self):
        """A text element with content should not be flagged."""
        brand = _brand()
        slide = Slide(index=0, elements=[_text_elem("t1", [_para("Content")])])
        issues = evaluate_content(slide, brand)
        empty_issues = [i for i in issues if i.details.get("check") == "empty_placeholder"]
        assert len(empty_issues) == 0

    def test_empty_element_emits_info(self):
        """An empty text placeholder should emit an info issue."""
        brand = _brand()
        slide = Slide(
            index=0,
            elements=[_text_elem("t1", [Paragraph(runs=[])], name="Title Placeholder")],
        )
        issues = evaluate_content(slide, brand)
        empty_issues = [i for i in issues if i.details.get("check") == "empty_placeholder"]
        assert len(empty_issues) == 1
        assert empty_issues[0].severity == Severity.info
        assert "Title Placeholder" in empty_issues[0].message

    def test_whitespace_only_is_empty(self):
        """A text element with only whitespace should be considered empty."""
        brand = _brand()
        slide = Slide(
            index=0,
            elements=[_text_elem("t1", [_para("   ")])],
        )
        issues = evaluate_content(slide, brand)
        empty_issues = [i for i in issues if i.details.get("check") == "empty_placeholder"]
        assert len(empty_issues) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_slide_no_issues(self):
        """An empty slide should produce no content issues."""
        brand = _brand()
        slide = Slide(index=0, elements=[])
        issues = evaluate_content(slide, brand)
        assert len(issues) == 0

    def test_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        brand = _brand(max_words=1)
        slide = Slide(
            index=3,
            elements=[_text_elem("t1", [_para("too many words here")])],
        )
        issues = evaluate_content(slide, brand)
        assert all(i.slide_index == 3 for i in issues)
