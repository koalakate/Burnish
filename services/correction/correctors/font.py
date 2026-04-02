"""Font corrector — substitutes disallowed fonts with the first allowed brand font."""

from __future__ import annotations

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Paragraph
from services.rules.models import Issue


def _replace_font_family_in_runs(
    paragraphs: list[Paragraph],
    replacement_family: str,
    allowed_families: set[str],
) -> None:
    """Replace disallowed font families in all runs of the given paragraphs."""
    for para in paragraphs:
        for run in para.runs:
            if (
                run.font.family is not None
                and run.font.family not in allowed_families
            ):
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

    default_replacement = brand.fonts[0].family
    allowed_families = {f.family for f in brand.fonts}

    # Build map of (slide_index, element_id) -> replacement font
    # Prefer user-edited expected_value over default brand font
    affected: dict[tuple[int, str], str] = {}
    for issue in font_issues:
        edited = issue.details.get("expected_value")
        replacement = str(edited) if edited else default_replacement
        affected[(issue.slide_index, issue.element_id)] = replacement

    for slide in csm.slides:
        for elem in slide.elements:
            replacement_family = affected.get((slide.index, elem.id))
            if replacement_family is None:
                continue

            if elem.type == "text":
                _replace_font_family_in_runs(elem.paragraphs, replacement_family, allowed_families)
            elif elem.type == "shape":
                _replace_font_family_in_runs(elem.paragraphs, replacement_family, allowed_families)
            elif elem.type == "table":
                for cell in elem.cells:
                    _replace_font_family_in_runs(
                        cell.paragraphs, replacement_family, allowed_families,
                    )

    return csm
