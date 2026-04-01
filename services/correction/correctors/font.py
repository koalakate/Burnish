"""Font corrector — substitutes disallowed fonts with the first allowed brand font."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Paragraph
from services.rules.models import Issue


def _replace_font_family_in_runs(paragraphs: list[Paragraph], replacement_family: str) -> None:
    """Replace font family in all runs of the given paragraphs."""
    for para in paragraphs:
        for run in para.runs:
            if run.font.family is not None:
                run.font = run.font.model_copy(update={"family": replacement_family})


def correct_fonts(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
    """Substitute disallowed font families with the first allowed brand font.

    Preserves font size, weight, italic, and underline. Only changes the
    family name.
    """
    font_issues = [
        i for i in issues
        if i.evaluator == "typography" and i.details.get("check") == "font_family"
    ]
    if not font_issues or not brand.fonts:
        return csm

    replacement_family = brand.fonts[0].family

    # Build set of (slide_index, element_id) that need fixing
    affected: set[tuple[int, str]] = set()
    for issue in font_issues:
        affected.add((issue.slide_index, issue.element_id))

    for slide in csm.slides:
        for elem in slide.elements:
            if (slide.index, elem.id) not in affected:
                continue

            if elem.type == "text":
                _replace_font_family_in_runs(elem.paragraphs, replacement_family)
            elif elem.type == "shape":
                _replace_font_family_in_runs(elem.paragraphs, replacement_family)
            elif elem.type == "table":
                for cell in elem.cells:
                    _replace_font_family_in_runs(cell.paragraphs, replacement_family)

    return csm
