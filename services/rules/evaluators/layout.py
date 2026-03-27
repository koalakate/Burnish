"""Layout evaluator — checks margins, element count, and alignment consistency."""

from __future__ import annotations

import uuid

from packages.csm.brand import BrandRuleset
from packages.csm.models import Slide
from services.rules.models import Issue, Severity

# python-pptx stores positions in EMU; 1 inch = 914400 EMU.
_EMU_PER_INCH = 914_400


def evaluate_layout(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check layout compliance for a single slide.

    Checks:
    - Elements too close to the slide edge (margin violations).
    - Too many elements on one slide.
    - Elements not snapped to the alignment grid.
    """
    rules = brand.layout_rules
    issues: list[Issue] = []

    # --- Margin checks ---
    margin_left_emu = rules.margin_left * _EMU_PER_INCH
    margin_top_emu = rules.margin_top * _EMU_PER_INCH

    for elem in slide.elements:
        bb = elem.bbox
        elem_id = elem.id or elem.name or "unknown"

        # Left margin
        if bb.x < margin_left_emu:
            issues.append(Issue(
                id=f"layout-margin-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="layout",
                severity=Severity.warning,
                message=(
                    f"Element '{elem.name}' is too close to the left edge "
                    f"({bb.x / _EMU_PER_INCH:.2f}\" from left, minimum {rules.margin_left}\")."
                ),
                details={
                    "check": "margin",
                    "side": "left",
                    "actual_inches": bb.x / _EMU_PER_INCH,
                    "required_inches": rules.margin_left,
                },
                bbox=bb,
            ))

        # Top margin
        if bb.y < margin_top_emu:
            issues.append(Issue(
                id=f"layout-margin-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="layout",
                severity=Severity.warning,
                message=(
                    f"Element '{elem.name}' is too close to the top edge "
                    f"({bb.y / _EMU_PER_INCH:.2f}\" from top, minimum {rules.margin_top}\")."
                ),
                details={
                    "check": "margin",
                    "side": "top",
                    "actual_inches": bb.y / _EMU_PER_INCH,
                    "required_inches": rules.margin_top,
                },
                bbox=bb,
            ))

    # --- Element count check ---
    max_elements = rules.max_elements_per_slide
    elem_count = len(slide.elements)
    if elem_count > max_elements:
        issues.append(Issue(
            id=f"layout-count-{slide.index}-{uuid.uuid4().hex[:8]}",
            slide_index=slide.index,
            element_id="",
            evaluator="layout",
            severity=Severity.warning,
            message=(
                f"Slide has {elem_count} elements, exceeding the maximum "
                f"of {max_elements}. Consider simplifying the layout."
            ),
            details={
                "check": "element_count",
                "actual_count": elem_count,
                "max_count": max_elements,
            },
        ))

    # --- Alignment grid check ---
    grid_pt = rules.alignment_grid_pt
    if grid_pt > 0:
        # Convert grid from points to EMU (1 pt = 12700 EMU)
        grid_emu = grid_pt * 12_700
        for elem in slide.elements:
            bb = elem.bbox
            elem_id = elem.id or elem.name or "unknown"
            x_off = bb.x % grid_emu
            y_off = bb.y % grid_emu
            # Allow small rounding tolerance (1 EMU)
            if x_off > 1 and (grid_emu - x_off) > 1:
                issues.append(Issue(
                    id=f"layout-grid-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                    slide_index=slide.index,
                    element_id=elem_id,
                    evaluator="layout",
                    severity=Severity.info,
                    message=(
                        f"Element '{elem.name}' is {x_off / 12_700:.1f}pt off the "
                        f"horizontal alignment grid ({grid_pt}pt)."
                    ),
                    details={
                        "check": "alignment_grid",
                        "axis": "x",
                        "offset_pt": x_off / 12_700,
                        "grid_pt": grid_pt,
                    },
                    bbox=bb,
                ))
            if y_off > 1 and (grid_emu - y_off) > 1:
                issues.append(Issue(
                    id=f"layout-grid-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                    slide_index=slide.index,
                    element_id=elem_id,
                    evaluator="layout",
                    severity=Severity.info,
                    message=(
                        f"Element '{elem.name}' is {y_off / 12_700:.1f}pt off the "
                        f"vertical alignment grid ({grid_pt}pt)."
                    ),
                    details={
                        "check": "alignment_grid",
                        "axis": "y",
                        "offset_pt": y_off / 12_700,
                        "grid_pt": grid_pt,
                    },
                    bbox=bb,
                ))

    return issues
