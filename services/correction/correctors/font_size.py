"""Font size corrector — bumps sizes below the brand minimum to the minimum."""

from __future__ import annotations

from typing import Any

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Paragraph
from services.rules.models import Issue


def correct_font_sizes(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
    """Bump font sizes below the brand minimum to the minimum.

    For elements with a known role, uses the role's min_pt from the brand
    size rules.  Scales proportionally: if the text box has multiple sizes,
    the ratio between runs is preserved by applying the same scale factor.
    """
    size_issues = [
        i for i in issues
        if i.evaluator == "typography" and i.details.get("check") == "font_size"
    ]
    if not size_issues:
        return csm

    # Group issues by (slide_index, element_id) -> (factor, min_pt, max_pt)
    affected: dict[tuple[int, str], tuple[float, float, float]] = {}
    for issue in size_issues:
        d = issue.details
        raw_actual: Any = d.get("actual_size_pt", 0)
        raw_min: Any = d.get("min_pt", 0)
        raw_max: Any = d.get("max_pt", float("inf"))
        actual = float(raw_actual)
        min_pt = float(raw_min)
        max_pt = float(raw_max)

        if actual <= 0:
            continue

        # Prefer user-edited expected_value as the target size
        edited = d.get("expected_value")
        if edited is not None:
            try:
                target = float(str(edited))
                factor = target / actual
                key = (issue.slide_index, issue.element_id)
                affected[key] = (factor, min_pt, max_pt)
                continue
            except (ValueError, TypeError):
                pass

        if actual < min_pt:
            factor = min_pt / actual
        elif actual > max_pt and max_pt > 0:
            factor = max_pt / actual
        else:
            continue

        key = (issue.slide_index, issue.element_id)
        if key not in affected or factor > affected[key][0]:
            affected[key] = (factor, min_pt, max_pt)

    for slide in csm.slides:
        for elem in slide.elements:
            entry = affected.get((slide.index, elem.id))
            if entry is None:
                continue
            elem_factor, min_pt, max_pt = entry

            paragraphs_list: list[list[Paragraph]] = []
            if elem.type == "text":
                paragraphs_list = [elem.paragraphs]
            elif elem.type == "shape":
                paragraphs_list = [elem.paragraphs]
            elif elem.type == "table":
                paragraphs_list = [cell.paragraphs for cell in elem.cells]

            for paragraphs in paragraphs_list:
                for para in paragraphs:
                    for run in para.runs:
                        if run.font.size_pt is not None:
                            new_size = round(run.font.size_pt * elem_factor, 1)
                            # Clamp to max to avoid overshooting
                            if max_pt != float("inf"):
                                new_size = min(new_size, max_pt)
                            run.font = run.font.model_copy(
                                update={"size_pt": new_size},
                            )

    return csm
