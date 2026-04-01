"""Alignment corrector — snaps elements to the nearest grid line."""

from __future__ import annotations

from typing import Any

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM
from services.rules.models import Issue

# 1 point = 12700 EMU
_EMU_PER_PT = 12_700
_EMU_PER_INCH = 914_400


def _snap_to_grid(value: float, grid_emu: float) -> float:
    """Snap a value to the nearest grid line."""
    if grid_emu <= 0:
        return value
    return round(value / grid_emu) * grid_emu


def correct_alignment(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
    """Snap elements to the nearest grid line and enforce margins.

    Handles two types of layout issues:
    - alignment_grid: snaps x/y to the nearest grid point
    - margin: pushes elements inward to meet minimum margin
    """
    layout_issues = [i for i in issues if i.evaluator == "layout"]
    if not layout_issues:
        return csm

    rules = brand.layout_rules
    grid_emu = rules.alignment_grid_pt * _EMU_PER_PT

    # Collect fixes per (slide_index, element_id)
    grid_fixes: set[tuple[int, str]] = set()
    margin_fixes: dict[tuple[int, str], dict[str, float]] = {}

    for issue in layout_issues:
        check = issue.details.get("check", "")
        key = (issue.slide_index, issue.element_id)

        if check == "alignment_grid":
            grid_fixes.add(key)
        elif check == "margin":
            side = str(issue.details.get("side", ""))
            raw_required: Any = issue.details.get("required_inches", 0)
            required = float(raw_required)
            margin_fixes.setdefault(key, {})[side] = required

    for slide in csm.slides:
        for elem in slide.elements:
            key = (slide.index, elem.id)

            # Margin correction: push element to meet minimum margin
            margins = margin_fixes.get(key)
            if margins:
                if "left" in margins:
                    min_x = margins["left"] * _EMU_PER_INCH
                    if elem.bbox.x < min_x:
                        elem.bbox = elem.bbox.model_copy(update={"x": min_x})
                if "top" in margins:
                    min_y = margins["top"] * _EMU_PER_INCH
                    if elem.bbox.y < min_y:
                        elem.bbox = elem.bbox.model_copy(update={"y": min_y})

            # Grid snap correction
            if key in grid_fixes and grid_emu > 0:
                new_x = _snap_to_grid(elem.bbox.x, grid_emu)
                new_y = _snap_to_grid(elem.bbox.y, grid_emu)
                elem.bbox = elem.bbox.model_copy(
                    update={"x": new_x, "y": new_y},
                )

    return csm
