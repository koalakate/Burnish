"""Tests for the image evaluator."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset, CustomTolerances
from packages.csm.models import (
    BoundingBox,
    ImageElement,
    Slide,
    TextElement,
    Font,
    Paragraph,
    TextRun,
)
from services.rules.evaluators.image import evaluate_images
from services.rules.models import Severity


def _bbox(w: float = 1000, h: float = 1000) -> BoundingBox:
    return BoundingBox(x=0, y=0, width=w, height=h)


def _brand(
    min_dpi: float | None = None,
    ar_tolerance: float | None = None,
) -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        custom_tolerances=CustomTolerances(
            image_min_dpi=min_dpi,
            aspect_ratio_tolerance=ar_tolerance,
        ),
    )


def _image(
    id: str = "img1",
    name: str = "Photo",
    dpi: float | None = None,
    original_width: int | None = None,
    original_height: int | None = None,
    bbox_w: float = 1000,
    bbox_h: float = 1000,
    alt_text: str | None = None,
) -> ImageElement:
    return ImageElement(
        id=id,
        name=name,
        bbox=BoundingBox(x=100, y=100, width=bbox_w, height=bbox_h),
        dpi=dpi,
        original_width=original_width,
        original_height=original_height,
        alt_text=alt_text,
    )


# ---------------------------------------------------------------------------
# DPI checks
# ---------------------------------------------------------------------------


class TestDPI:
    def test_high_dpi_passes(self):
        """An image above minimum DPI should produce no issues."""
        brand = _brand(min_dpi=150)
        slide = Slide(index=0, elements=[_image(dpi=300, alt_text="A photo")])
        issues = evaluate_images(slide, brand)
        dpi_issues = [i for i in issues if i.details.get("check") == "image_dpi"]
        assert len(dpi_issues) == 0

    def test_low_dpi_emits_warning(self):
        """An image below minimum DPI should emit a warning."""
        brand = _brand(min_dpi=150)
        slide = Slide(index=0, elements=[_image(dpi=72, alt_text="A photo")])
        issues = evaluate_images(slide, brand)
        dpi_issues = [i for i in issues if i.details.get("check") == "image_dpi"]
        assert len(dpi_issues) == 1
        assert dpi_issues[0].severity == Severity.warning
        assert dpi_issues[0].details["actual_dpi"] == 72
        assert dpi_issues[0].details["min_dpi"] == 150

    def test_no_dpi_info_skips_check(self):
        """An image without DPI info should not be flagged for DPI."""
        brand = _brand(min_dpi=150)
        slide = Slide(index=0, elements=[_image(dpi=None, alt_text="A photo")])
        issues = evaluate_images(slide, brand)
        dpi_issues = [i for i in issues if i.details.get("check") == "image_dpi"]
        assert len(dpi_issues) == 0

    def test_default_min_dpi_is_150(self):
        """Without a custom tolerance, the default minimum DPI should be 150."""
        brand = _brand()  # no custom min_dpi
        slide = Slide(index=0, elements=[_image(dpi=100, alt_text="A photo")])
        issues = evaluate_images(slide, brand)
        dpi_issues = [i for i in issues if i.details.get("check") == "image_dpi"]
        assert len(dpi_issues) == 1
        assert dpi_issues[0].details["min_dpi"] == 150


# ---------------------------------------------------------------------------
# Aspect ratio checks
# ---------------------------------------------------------------------------


class TestAspectRatio:
    def test_undistorted_passes(self):
        """An image with preserved aspect ratio should pass."""
        brand = _brand(ar_tolerance=0.05)
        slide = Slide(
            index=0,
            elements=[
                _image(
                    original_width=800,
                    original_height=600,
                    bbox_w=400,  # same ratio: 4:3
                    bbox_h=300,
                    alt_text="A photo",
                )
            ],
        )
        issues = evaluate_images(slide, brand)
        ar_issues = [i for i in issues if i.details.get("check") == "aspect_ratio"]
        assert len(ar_issues) == 0

    def test_distorted_emits_warning(self):
        """An image with significant aspect ratio change should emit a warning."""
        brand = _brand(ar_tolerance=0.05)
        slide = Slide(
            index=0,
            elements=[
                _image(
                    original_width=800,
                    original_height=600,  # 4:3 = 1.333
                    bbox_w=800,
                    bbox_h=400,  # 2:1 = 2.0 → distortion = 50%
                    alt_text="A photo",
                )
            ],
        )
        issues = evaluate_images(slide, brand)
        ar_issues = [i for i in issues if i.details.get("check") == "aspect_ratio"]
        assert len(ar_issues) == 1
        assert ar_issues[0].severity == Severity.warning
        assert ar_issues[0].details["distortion_pct"] > 5

    def test_no_original_dims_skips_check(self):
        """Without original dimensions, aspect ratio check should be skipped."""
        brand = _brand(ar_tolerance=0.05)
        slide = Slide(
            index=0,
            elements=[_image(original_width=None, original_height=None, alt_text="A photo")],
        )
        issues = evaluate_images(slide, brand)
        ar_issues = [i for i in issues if i.details.get("check") == "aspect_ratio"]
        assert len(ar_issues) == 0

    def test_slight_distortion_within_tolerance(self):
        """A minor aspect ratio change within tolerance should pass."""
        brand = _brand(ar_tolerance=0.05)
        slide = Slide(
            index=0,
            elements=[
                _image(
                    original_width=1000,
                    original_height=1000,  # 1:1
                    bbox_w=1000,
                    bbox_h=960,  # distortion = 4.2% < 5%
                    alt_text="A photo",
                )
            ],
        )
        issues = evaluate_images(slide, brand)
        ar_issues = [i for i in issues if i.details.get("check") == "aspect_ratio"]
        assert len(ar_issues) == 0


# ---------------------------------------------------------------------------
# Alt text checks
# ---------------------------------------------------------------------------


class TestAltText:
    def test_with_alt_text_passes(self):
        """An image with alt text should not be flagged."""
        brand = _brand()
        slide = Slide(index=0, elements=[_image(alt_text="A descriptive caption")])
        issues = evaluate_images(slide, brand)
        alt_issues = [i for i in issues if i.details.get("check") == "alt_text"]
        assert len(alt_issues) == 0

    def test_missing_alt_text_emits_error(self):
        """An image without alt text should emit an error."""
        brand = _brand()
        slide = Slide(index=0, elements=[_image(alt_text=None)])
        issues = evaluate_images(slide, brand)
        alt_issues = [i for i in issues if i.details.get("check") == "alt_text"]
        assert len(alt_issues) == 1
        assert alt_issues[0].severity == Severity.error

    def test_empty_alt_text_emits_error(self):
        """An image with empty string alt text should emit an error."""
        brand = _brand()
        slide = Slide(index=0, elements=[_image(alt_text="")])
        issues = evaluate_images(slide, brand)
        alt_issues = [i for i in issues if i.details.get("check") == "alt_text"]
        assert len(alt_issues) == 1

    def test_whitespace_alt_text_emits_error(self):
        """An image with whitespace-only alt text should emit an error."""
        brand = _brand()
        slide = Slide(index=0, elements=[_image(alt_text="   ")])
        issues = evaluate_images(slide, brand)
        alt_issues = [i for i in issues if i.details.get("check") == "alt_text"]
        assert len(alt_issues) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_non_image_elements_ignored(self):
        """Non-image elements should be skipped entirely."""
        brand = _brand()
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="t1",
                    bbox=_bbox(),
                    paragraphs=[Paragraph(runs=[TextRun(text="Hello", font=Font())])],
                )
            ],
        )
        issues = evaluate_images(slide, brand)
        assert len(issues) == 0

    def test_empty_slide_no_issues(self):
        """An empty slide should produce no image issues."""
        brand = _brand()
        slide = Slide(index=0, elements=[])
        issues = evaluate_images(slide, brand)
        assert len(issues) == 0

    def test_correct_slide_index(self):
        """Issues should reference the correct slide index."""
        brand = _brand()
        slide = Slide(index=4, elements=[_image(alt_text=None)])
        issues = evaluate_images(slide, brand)
        assert all(i.slide_index == 4 for i in issues)

    def test_multiple_issues_on_one_image(self):
        """An image can have multiple issues simultaneously."""
        brand = _brand(min_dpi=150, ar_tolerance=0.05)
        slide = Slide(
            index=0,
            elements=[
                _image(
                    dpi=72,
                    original_width=800,
                    original_height=600,
                    bbox_w=800,
                    bbox_h=400,
                    alt_text=None,
                )
            ],
        )
        issues = evaluate_images(slide, brand)
        checks = {i.details.get("check") for i in issues}
        assert "image_dpi" in checks
        assert "aspect_ratio" in checks
        assert "alt_text" in checks
