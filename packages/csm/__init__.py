"""Canonical Slide Model (CSM) package."""

from packages.csm.brand import (
    BrandColor,
    BrandFont,
    BrandRuleset,
    CustomTolerances,
    LayoutRules,
    SizeRule,
)
from packages.csm.models import (
    CSM,
    BoundingBox,
    Color,
    Font,
    ImageElement,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    SlideElement,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)

__all__ = [
    "BoundingBox",
    "BrandColor",
    "BrandFont",
    "BrandRuleset",
    "Color",
    "CSM",
    "CustomTolerances",
    "Font",
    "ImageElement",
    "LayoutRules",
    "Paragraph",
    "ShapeElement",
    "SizeRule",
    "Slide",
    "SlideBackground",
    "SlideElement",
    "TableCell",
    "TableElement",
    "TextElement",
    "TextRun",
]
