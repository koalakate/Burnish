"""Brand ruleset model — defines the design rules a presentation is checked against."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BrandColor(BaseModel):
    """An allowed brand color with Delta-E tolerance."""

    name: str = Field(description="Human-readable color name, e.g. 'Brand Blue'")
    hex: str = Field(description="Hex color string, e.g. '#1B3A6B'")
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)
    tolerance_delta_e: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum Delta-E (CIELAB) distance to still count as on-brand",
    )


class BrandFont(BaseModel):
    """An allowed font family with optional weight range."""

    family: str = Field(description="Font family name, e.g. 'Inter'")
    weight_min: int = Field(default=100, ge=100, le=900)
    weight_max: int = Field(default=900, ge=100, le=900)


class SizeRule(BaseModel):
    """Min/max font size constraints for an element role."""

    role: str = Field(description="Element role: title, body, caption, subtitle")
    min_pt: float = Field(default=0.0, ge=0.0)
    max_pt: float = Field(default=200.0, ge=0.0)


class LayoutRules(BaseModel):
    """Layout constraints for slides."""

    margin_left: float = Field(default=0.5, ge=0.0, description="Left margin in inches")
    margin_right: float = Field(default=0.5, ge=0.0, description="Right margin in inches")
    margin_top: float = Field(default=0.5, ge=0.0, description="Top margin in inches")
    margin_bottom: float = Field(default=0.5, ge=0.0, description="Bottom margin in inches")
    max_elements_per_slide: int = Field(default=12, ge=1)
    alignment_grid_pt: float = Field(
        default=0.0,
        ge=0.0,
        description="Grid snap size in points; 0 means no grid enforcement",
    )


class CustomTolerances(BaseModel):
    """Per-evaluator override tolerances."""

    color_delta_e: float | None = Field(
        default=None, description="Override default Delta-E tolerance for color checks"
    )
    contrast_ratio_normal: float | None = Field(
        default=None, description="Override WCAG AA contrast ratio for normal text"
    )
    contrast_ratio_large: float | None = Field(
        default=None, description="Override WCAG AA contrast ratio for large text"
    )
    max_words_per_slide: int | None = Field(
        default=None, description="Override max word count per slide"
    )
    max_bullets_per_slide: int | None = Field(
        default=None, description="Override max bullet count per slide"
    )
    image_min_dpi: float | None = Field(
        default=None, description="Override minimum image DPI"
    )
    aspect_ratio_tolerance: float | None = Field(
        default=None, description="Override aspect ratio distortion tolerance (fraction)"
    )


class BrandRuleset(BaseModel):
    """Complete brand ruleset that defines all design rules for checking a presentation."""

    name: str = Field(default="Untitled Brand", description="Brand name")
    colors: list[BrandColor] = Field(default_factory=list, description="Allowed brand colors")
    fonts: list[BrandFont] = Field(default_factory=list, description="Allowed font families")
    size_rules: list[SizeRule] = Field(
        default_factory=list, description="Font size constraints by element role"
    )
    layout_rules: LayoutRules = Field(default_factory=LayoutRules)
    custom_tolerances: CustomTolerances = Field(default_factory=CustomTolerances)
