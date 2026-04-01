"""Tests for the correction engine and all correctors."""

from __future__ import annotations

from packages.csm.brand import (
    BrandColor,
    BrandFont,
    BrandRuleset,
    LayoutRules,
    SizeRule,
)
from packages.csm.models import (
    CSM,
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
from services.correction.correctors.alignment import correct_alignment
from services.correction.correctors.color import correct_colors
from services.correction.correctors.contrast import correct_contrast
from services.correction.correctors.font import correct_fonts
from services.correction.correctors.font_size import correct_font_sizes
from services.correction.engine import CorrectionEngine
from services.rules.models import Issue, Severity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bbox() -> BoundingBox:
    return BoundingBox(x=0, y=0, width=100, height=50)


def _brand() -> BrandRuleset:
    return BrandRuleset(
        name="Test Brand",
        colors=[
            BrandColor(
                name="Brand Blue", hex="#1B3A6B",
                r=27, g=58, b=107, tolerance_delta_e=10.0,
            ),
            BrandColor(
                name="Brand White", hex="#FFFFFF",
                r=255, g=255, b=255, tolerance_delta_e=5.0,
            ),
        ],
        fonts=[
            BrandFont(family="Inter", weight_min=100, weight_max=900),
            BrandFont(family="Roboto", weight_min=400, weight_max=700),
        ],
        size_rules=[
            SizeRule(role="title", min_pt=24.0, max_pt=48.0),
            SizeRule(role="body", min_pt=14.0, max_pt=28.0),
        ],
        layout_rules=LayoutRules(
            margin_left=0.5,
            margin_right=0.5,
            margin_top=0.5,
            margin_bottom=0.5,
            alignment_grid_pt=18.0,
        ),
    )


def _csm_with_slide(slide: Slide) -> CSM:
    return CSM(slides=[slide], width=9144000, height=6858000)


# ---------------------------------------------------------------------------
# CorrectionEngine tests
# ---------------------------------------------------------------------------

class TestCorrectionEngine:
    def test_empty_correctors(self) -> None:
        engine = CorrectionEngine()
        csm = _csm_with_slide(Slide(index=0, elements=[]))
        result = engine.run(csm, [], _brand())
        assert result.slides == csm.slides

    def test_correctors_run_in_order(self) -> None:
        """Each corrector sees the output of the previous one."""
        log: list[str] = []

        def corrector_a(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
            log.append("a")
            return csm

        def corrector_b(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
            log.append("b")
            return csm

        engine = CorrectionEngine([corrector_a, corrector_b])
        engine.run(_csm_with_slide(Slide(index=0, elements=[])), [], _brand())
        assert log == ["a", "b"]

    def test_register_adds_corrector(self) -> None:
        log: list[str] = []

        def my_corrector(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
            log.append("called")
            return csm

        engine = CorrectionEngine()
        engine.register(my_corrector)
        engine.run(_csm_with_slide(Slide(index=0, elements=[])), [], _brand())
        assert log == ["called"]

    def test_deep_copy_preserves_original(self) -> None:
        """The engine should not mutate the original CSM."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Hello", font=Font(family="Comic Sans"),
                                color=Color(hex="#FF0000", r=255, g=0, b=0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        original_hex = csm.slides[0].elements[0].paragraphs[0].runs[0].color.hex

        issue = Issue(
            id="color-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="color",
            severity=Severity.error,
            message="Off-brand",
            details={
                "actual_hex": "#FF0000",
                "actual_rgb": [255, 0, 0],
                "nearest_brand_hex": "#1B3A6B",
                "nearest_brand_rgb": [27, 58, 107],
                "delta_e": 50.0,
                "tolerance": 10.0,
                "description": "text color",
            },
        )
        engine = CorrectionEngine([correct_colors])
        engine.run(csm, [issue], _brand())

        # Original should be untouched
        assert csm.slides[0].elements[0].paragraphs[0].runs[0].color.hex == original_hex


# ---------------------------------------------------------------------------
# Color corrector tests
# ---------------------------------------------------------------------------

class TestColorCorrector:
    def test_swaps_off_brand_text_color(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Hello", font=Font(),
                                color=Color(hex="#FF0000", r=255, g=0, b=0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="color-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="color",
            severity=Severity.error,
            message="Off-brand",
            details={
                "actual_hex": "#FF0000",
                "actual_rgb": [255, 0, 0],
                "nearest_brand_hex": "#1B3A6B",
                "nearest_brand_rgb": [27, 58, 107],
                "delta_e": 50.0,
                "tolerance": 10.0,
                "description": "text color",
            },
        )
        result = correct_colors(csm, [issue], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.color.hex == "#1B3A6B"
        assert run.color.r == 27

    def test_swaps_shape_fill_color(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="shp1", bbox=_bbox(),
                    fill_color=Color(hex="#FF0000", r=255, g=0, b=0),
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="color-0-shp1-abc",
            slide_index=0,
            element_id="shp1",
            evaluator="color",
            severity=Severity.error,
            message="Off-brand",
            details={
                "actual_hex": "#FF0000",
                "actual_rgb": [255, 0, 0],
                "nearest_brand_hex": "#1B3A6B",
                "nearest_brand_rgb": [27, 58, 107],
                "delta_e": 50.0,
                "tolerance": 10.0,
                "description": "shape fill color",
            },
        )
        result = correct_colors(csm, [issue], _brand())
        assert result.slides[0].elements[0].fill_color.hex == "#1B3A6B"

    def test_swaps_table_cell_fill(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TableElement(
                    id="tbl1", bbox=_bbox(), rows=1, cols=1,
                    cells=[
                        TableCell(
                            row=0, col=0,
                            fill_color=Color(hex="#FF0000", r=255, g=0, b=0),
                        )
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="color-0-tbl1-abc",
            slide_index=0,
            element_id="tbl1",
            evaluator="color",
            severity=Severity.error,
            message="Off-brand",
            details={
                "actual_hex": "#FF0000",
                "actual_rgb": [255, 0, 0],
                "nearest_brand_hex": "#FFFFFF",
                "nearest_brand_rgb": [255, 255, 255],
                "delta_e": 50.0,
                "tolerance": 5.0,
                "description": "table cell fill",
            },
        )
        result = correct_colors(csm, [issue], _brand())
        assert result.slides[0].elements[0].cells[0].fill_color.hex == "#FFFFFF"

    def test_no_color_issues_returns_unchanged(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="OK", font=Font(),
                                color=Color(hex="#1B3A6B", r=27, g=58, b=107),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        result = correct_colors(csm, [], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.color.hex == "#1B3A6B"


# ---------------------------------------------------------------------------
# Font corrector tests
# ---------------------------------------------------------------------------

class TestFontCorrector:
    def test_substitutes_disallowed_font(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Hello", font=Font(family="Comic Sans", size_pt=14.0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="typo-family-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="typography",
            severity=Severity.error,
            message="Font 'Comic Sans' is not approved.",
            details={
                "check": "font_family",
                "actual_family": "Comic Sans",
                "allowed_families": ["Inter", "Roboto"],
                "sample_text": "Hello",
            },
        )
        result = correct_fonts(csm, [issue], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.font.family == "Inter"
        # Size should be preserved
        assert run.font.size_pt == 14.0

    def test_preserves_approved_fonts(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Hello", font=Font(family="Inter", size_pt=14.0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        result = correct_fonts(csm, [], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.font.family == "Inter"

    def test_fixes_font_in_shape(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="shp1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="Hi", font=Font(family="Arial", size_pt=12.0))
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="typo-family-0-shp1-abc",
            slide_index=0,
            element_id="shp1",
            evaluator="typography",
            severity=Severity.error,
            message="Font 'Arial' is not approved.",
            details={
                "check": "font_family",
                "actual_family": "Arial",
                "allowed_families": ["Inter", "Roboto"],
                "sample_text": "Hi",
            },
        )
        result = correct_fonts(csm, [issue], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.font.family == "Inter"


# ---------------------------------------------------------------------------
# Contrast corrector tests
# ---------------------------------------------------------------------------

class TestContrastCorrector:
    def test_adjusts_low_contrast_text(self) -> None:
        """Gray text on white background should be darkened to meet 4.5:1."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Faded",
                                font=Font(size_pt=14.0),
                                color=Color(hex="#AAAAAA", r=170, g=170, b=170),
                            )
                        ]),
                    ],
                )
            ],
            background=SlideBackground(
                solid_color=Color(hex="#FFFFFF", r=255, g=255, b=255),
            ),
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="accessibility-contrast-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="accessibility",
            severity=Severity.error,
            message="Low contrast (2.3:1)",
            details={
                "check": "wcag_aa_contrast",
                "contrast_ratio": 2.32,
                "threshold": 4.5,
                "text_color": "#AAAAAA",
                "bg_color": "#FFFFFF",
                "is_large_text": False,
                "size_pt": 14.0,
                "weight": None,
                "sample_text": "Faded",
            },
        )
        result = correct_contrast(csm, [issue], _brand())
        new_color = result.slides[0].elements[0].paragraphs[0].runs[0].color
        # The adjusted color should not be the original
        assert new_color.hex != "#AAAAAA"
        # Verify it's darker (lower RGB values since text was darkened against white bg)
        assert new_color.r < 170

    def test_no_contrast_issues_unchanged(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Dark",
                                font=Font(size_pt=14.0),
                                color=Color(hex="#000000", r=0, g=0, b=0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        result = correct_contrast(csm, [], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.color.hex == "#000000"

    def test_large_text_uses_lower_threshold(self) -> None:
        """Large text (>=18pt) only needs 3.0:1 contrast."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(),
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Big",
                                font=Font(size_pt=24.0),
                                color=Color(hex="#999999", r=153, g=153, b=153),
                            )
                        ]),
                    ],
                )
            ],
            background=SlideBackground(
                solid_color=Color(hex="#FFFFFF", r=255, g=255, b=255),
            ),
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="accessibility-contrast-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="accessibility",
            severity=Severity.error,
            message="Low contrast (2.8:1)",
            details={
                "check": "wcag_aa_contrast",
                "contrast_ratio": 2.85,
                "threshold": 3.0,
                "text_color": "#999999",
                "bg_color": "#FFFFFF",
                "is_large_text": True,
                "size_pt": 24.0,
                "weight": None,
                "sample_text": "Big",
            },
        )
        result = correct_contrast(csm, [issue], _brand())
        new_color = result.slides[0].elements[0].paragraphs[0].runs[0].color
        assert new_color.hex != "#999999"


# ---------------------------------------------------------------------------
# Font size corrector tests
# ---------------------------------------------------------------------------

class TestFontSizeCorrector:
    def test_bumps_small_title_to_minimum(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(), role="title",
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="Title", font=Font(size_pt=16.0))
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="typo-size-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="typography",
            severity=Severity.warning,
            message="Font size 16pt is below minimum 24pt for title text.",
            details={
                "check": "font_size",
                "actual_size_pt": 16.0,
                "min_pt": 24.0,
                "max_pt": 48.0,
                "role": "title",
                "sample_text": "Title",
            },
        )
        result = correct_font_sizes(csm, [issue], _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]
        assert run.font.size_pt == 24.0

    def test_scales_proportionally(self) -> None:
        """If one run is 16pt and another is 8pt, both scale by the same factor."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(), role="title",
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="Big", font=Font(size_pt=16.0)),
                            TextRun(text="Small", font=Font(size_pt=8.0)),
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="typo-size-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="typography",
            severity=Severity.warning,
            message="Font size 16pt is below minimum 24pt for title text.",
            details={
                "check": "font_size",
                "actual_size_pt": 16.0,
                "min_pt": 24.0,
                "max_pt": 48.0,
                "role": "title",
                "sample_text": "Big",
            },
        )
        result = correct_font_sizes(csm, [issue], _brand())
        runs = result.slides[0].elements[0].paragraphs[0].runs
        # Factor is 24/16 = 1.5
        assert runs[0].font.size_pt == 24.0
        assert runs[1].font.size_pt == 12.0

    def test_no_size_issues_unchanged(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(), role="body",
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(text="OK", font=Font(size_pt=16.0))
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        result = correct_font_sizes(csm, [], _brand())
        assert result.slides[0].elements[0].paragraphs[0].runs[0].font.size_pt == 16.0


# ---------------------------------------------------------------------------
# Alignment corrector tests
# ---------------------------------------------------------------------------

_EMU_PER_INCH = 914_400
_EMU_PER_PT = 12_700


class TestAlignmentCorrector:
    def test_snaps_to_grid(self) -> None:
        """An element off-grid should be snapped to the nearest grid line."""
        grid_pt = 18.0
        grid_emu = grid_pt * _EMU_PER_PT  # 228600
        # Place element at 1.5 grid units + 50000 off
        off_x = grid_emu * 1.5 + 50000
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=BoundingBox(x=off_x, y=grid_emu * 2 + 30000, width=100, height=50),
                    paragraphs=[],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue_x = Issue(
            id="layout-grid-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="layout",
            severity=Severity.info,
            message="Element off grid",
            details={"check": "alignment_grid", "axis": "x", "offset_pt": 3.9, "grid_pt": 18.0},
            bbox=BoundingBox(x=off_x, y=grid_emu * 2 + 30000, width=100, height=50),
        )
        issue_y = Issue(
            id="layout-grid-0-txt1-def",
            slide_index=0,
            element_id="txt1",
            evaluator="layout",
            severity=Severity.info,
            message="Element off grid",
            details={"check": "alignment_grid", "axis": "y", "offset_pt": 2.4, "grid_pt": 18.0},
            bbox=BoundingBox(x=off_x, y=grid_emu * 2 + 30000, width=100, height=50),
        )
        result = correct_alignment(csm, [issue_x, issue_y], _brand())
        elem = result.slides[0].elements[0]
        # x and y should be on grid
        assert elem.bbox.x % grid_emu == 0
        assert elem.bbox.y % grid_emu == 0

    def test_pushes_into_margin(self) -> None:
        """An element violating left margin should be pushed inward."""
        too_close_x = 0.2 * _EMU_PER_INCH  # 0.2 inches, min is 0.5
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=BoundingBox(x=too_close_x, y=_EMU_PER_INCH, width=100, height=50),
                    paragraphs=[],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issue = Issue(
            id="layout-margin-0-txt1-abc",
            slide_index=0,
            element_id="txt1",
            evaluator="layout",
            severity=Severity.warning,
            message="Too close to left edge",
            details={
                "check": "margin",
                "side": "left",
                "actual_inches": 0.2,
                "required_inches": 0.5,
            },
            bbox=BoundingBox(x=too_close_x, y=_EMU_PER_INCH, width=100, height=50),
        )
        result = correct_alignment(csm, [issue], _brand())
        elem = result.slides[0].elements[0]
        assert elem.bbox.x == 0.5 * _EMU_PER_INCH

    def test_no_layout_issues_unchanged(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1",
                    bbox=BoundingBox(x=_EMU_PER_INCH, y=_EMU_PER_INCH, width=100, height=50),
                    paragraphs=[],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        result = correct_alignment(csm, [], _brand())
        assert result.slides[0].elements[0].bbox.x == _EMU_PER_INCH


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_all_correctors_together(self) -> None:
        """Run the full pipeline with multiple issue types."""
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="txt1", bbox=_bbox(), role="title",
                    paragraphs=[
                        Paragraph(runs=[
                            TextRun(
                                text="Title",
                                font=Font(family="Comic Sans", size_pt=16.0),
                                color=Color(hex="#FF0000", r=255, g=0, b=0),
                            )
                        ]),
                    ],
                )
            ],
        )
        csm = _csm_with_slide(slide)
        issues = [
            Issue(
                id="color-0-txt1-abc",
                slide_index=0, element_id="txt1",
                evaluator="color", severity=Severity.error,
                message="Off-brand color",
                details={
                    "actual_hex": "#FF0000", "actual_rgb": [255, 0, 0],
                    "nearest_brand_hex": "#1B3A6B", "nearest_brand_rgb": [27, 58, 107],
                    "delta_e": 50.0, "tolerance": 10.0, "description": "text color",
                },
            ),
            Issue(
                id="typo-family-0-txt1-def",
                slide_index=0, element_id="txt1",
                evaluator="typography", severity=Severity.error,
                message="Font 'Comic Sans' not approved",
                details={
                    "check": "font_family", "actual_family": "Comic Sans",
                    "allowed_families": ["Inter", "Roboto"], "sample_text": "Title",
                },
            ),
            Issue(
                id="typo-size-0-txt1-ghi",
                slide_index=0, element_id="txt1",
                evaluator="typography", severity=Severity.warning,
                message="Font size 16pt below minimum 24pt",
                details={
                    "check": "font_size", "actual_size_pt": 16.0,
                    "min_pt": 24.0, "max_pt": 48.0,
                    "role": "title", "sample_text": "Title",
                },
            ),
        ]

        engine = CorrectionEngine([
            correct_colors,
            correct_fonts,
            correct_contrast,
            correct_font_sizes,
            correct_alignment,
        ])
        result = engine.run(csm, issues, _brand())
        run = result.slides[0].elements[0].paragraphs[0].runs[0]

        # Color was corrected
        assert run.color.hex == "#1B3A6B"
        # Font was corrected
        assert run.font.family == "Inter"
        # Size was scaled up
        assert run.font.size_pt == 24.0
