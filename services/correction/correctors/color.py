"""Color corrector — swaps off-brand colors to the nearest brand palette color."""

from __future__ import annotations

from typing import Any

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Color, Paragraph
from services.rules.models import Issue


def _make_color(hex_str: str, r: int, g: int, b: int) -> Color:
    """Create a Color from RGB values."""
    return Color(hex=hex_str, r=r, g=g, b=b)


def _replace_color_in_runs(
    paragraphs: list[Paragraph],
    element_id: str,
    replacements: dict[str, Color],
) -> None:
    """Replace text run colors that match a known off-brand hex."""
    for para in paragraphs:
        for run in para.runs:
            if run.color is not None and run.color.hex in replacements:
                run.color = replacements[run.color.hex]


def correct_colors(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
    """Swap off-brand colors to the nearest brand palette color.

    Uses the ``nearest_brand_hex`` and ``nearest_brand_rgb`` fields from
    color evaluator issue details.
    """
    color_issues = [i for i in issues if i.evaluator == "color"]
    if not color_issues:
        return csm

    # Build a per-slide, per-element map of hex -> replacement Color
    # Key: (slide_index, element_id, actual_hex) -> replacement Color
    replacements: dict[tuple[int, str, str], Color] = {}
    for issue in color_issues:
        d = issue.details
        actual_hex = str(d.get("actual_hex", ""))
        brand_hex = str(d.get("nearest_brand_hex", ""))
        brand_rgb: Any = d.get("nearest_brand_rgb", [0, 0, 0])
        if actual_hex and brand_hex:
            rgb: list[int] = [int(v) for v in brand_rgb]
            if len(rgb) < 3:
                continue
            replacement = _make_color(brand_hex, rgb[0], rgb[1], rgb[2])
            replacements[(issue.slide_index, issue.element_id, actual_hex)] = replacement

    for slide in csm.slides:
        for elem in slide.elements:
            # Collect all hex replacements for this element on this slide
            elem_replacements: dict[str, Color] = {}
            for (si, eid, ahex), repl in replacements.items():
                if si == slide.index and eid == elem.id:
                    elem_replacements[ahex] = repl

            if not elem_replacements:
                continue

            if elem.type == "text":
                _replace_color_in_runs(elem.paragraphs, elem.id, elem_replacements)
            elif elem.type == "shape":
                if elem.fill_color is not None and elem.fill_color.hex in elem_replacements:
                    elem.fill_color = elem_replacements[elem.fill_color.hex]
                if elem.line_color is not None and elem.line_color.hex in elem_replacements:
                    elem.line_color = elem_replacements[elem.line_color.hex]
                _replace_color_in_runs(elem.paragraphs, elem.id, elem_replacements)
            elif elem.type == "table":
                for cell in elem.cells:
                    if cell.fill_color is not None and cell.fill_color.hex in elem_replacements:
                        cell.fill_color = elem_replacements[cell.fill_color.hex]
                    _replace_color_in_runs(cell.paragraphs, elem.id, elem_replacements)

    return csm
