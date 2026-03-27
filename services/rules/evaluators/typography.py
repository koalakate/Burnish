"""Typography evaluator — checks fonts against the brand ruleset."""

from __future__ import annotations

import uuid

from packages.csm.brand import BrandFont, BrandRuleset, SizeRule
from packages.csm.models import Font, Slide
from services.rules.models import Issue, Severity


def _collect_runs(
    slide: Slide,
) -> list[tuple[str, str | None, Font, str]]:
    """Extract all text runs as (element_id, role, font, sample_text) tuples."""
    runs: list[tuple[str, str | None, Font, str]] = []
    for elem in slide.elements:
        if elem.type == "text":
            role = elem.role
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.text.strip():
                        runs.append((elem.id, role, run.font, run.text))
        elif elem.type == "shape":
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.text.strip():
                        runs.append((elem.id, None, run.font, run.text))
        elif elem.type == "table":
            for cell in elem.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            runs.append((elem.id, None, run.font, run.text))
    return runs


def _check_font_family(
    font: Font,
    brand_fonts: list[BrandFont],
) -> BrandFont | None:
    """Return None if the font family is approved, or None brand fonts exist.

    Returns the first matching BrandFont if approved, None if not approved.
    We return the match so callers can inspect it; a None return means unapproved.
    """
    if font.family is None:
        return brand_fonts[0] if brand_fonts else None
    family_lower = font.family.lower()
    for bf in brand_fonts:
        if bf.family.lower() == family_lower:
            return bf
    return None


def evaluate_typography(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check all text runs in a slide for typography compliance.

    Checks:
    - Font family must be in the brand's allowed list.
    - Font size must meet min/max for the element's role.
    - Font weight must be within the brand font's allowed range.
    """
    if not brand.fonts:
        return []

    size_rules_by_role: dict[str, SizeRule] = {
        sr.role.lower(): sr for sr in brand.size_rules
    }
    allowed_names = [bf.family for bf in brand.fonts]

    runs = _collect_runs(slide)
    issues: list[Issue] = []

    for element_id, role, font, sample_text in runs:
        # --- Font family check ---
        matched_brand_font = _check_font_family(font, brand.fonts)
        if matched_brand_font is None and font.family is not None:
            suggestion = " or ".join(f"'{n}'" for n in allowed_names)
            issues.append(Issue(
                id=f"typo-family-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=element_id,
                evaluator="typography",
                severity=Severity.error,
                message=(
                    f"Font '{font.family}' is not approved. "
                    f"Use {suggestion} instead."
                ),
                details={
                    "check": "font_family",
                    "actual_family": font.family,
                    "allowed_families": allowed_names,
                    "sample_text": sample_text[:50],
                },
            ))

        # --- Font size check ---
        if font.size_pt is not None and role is not None:
            rule = size_rules_by_role.get(role.lower())
            if rule is not None:
                if font.size_pt < rule.min_pt:
                    issues.append(Issue(
                        id=f"typo-size-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                        slide_index=slide.index,
                        element_id=element_id,
                        evaluator="typography",
                        severity=Severity.warning,
                        message=(
                            f"Font size {font.size_pt}pt is below the minimum "
                            f"{rule.min_pt}pt for {role} text."
                        ),
                        details={
                            "check": "font_size",
                            "actual_size_pt": font.size_pt,
                            "min_pt": rule.min_pt,
                            "max_pt": rule.max_pt,
                            "role": role,
                            "sample_text": sample_text[:50],
                        },
                    ))
                elif font.size_pt > rule.max_pt:
                    issues.append(Issue(
                        id=f"typo-size-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                        slide_index=slide.index,
                        element_id=element_id,
                        evaluator="typography",
                        severity=Severity.warning,
                        message=(
                            f"Font size {font.size_pt}pt exceeds the maximum "
                            f"{rule.max_pt}pt for {role} text."
                        ),
                        details={
                            "check": "font_size",
                            "actual_size_pt": font.size_pt,
                            "min_pt": rule.min_pt,
                            "max_pt": rule.max_pt,
                            "role": role,
                            "sample_text": sample_text[:50],
                        },
                    ))

        # --- Font weight check ---
        if font.weight is not None and matched_brand_font is not None:
            if not (matched_brand_font.weight_min <= font.weight <= matched_brand_font.weight_max):
                issues.append(Issue(
                    id=f"typo-weight-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                    slide_index=slide.index,
                    element_id=element_id,
                    evaluator="typography",
                    severity=Severity.info,
                    message=(
                        f"Font weight {font.weight} is outside the approved range "
                        f"({matched_brand_font.weight_min}-{matched_brand_font.weight_max}) "
                        f"for '{matched_brand_font.family}'."
                    ),
                    details={
                        "check": "font_weight",
                        "actual_weight": font.weight,
                        "weight_min": matched_brand_font.weight_min,
                        "weight_max": matched_brand_font.weight_max,
                        "font_family": matched_brand_font.family,
                        "sample_text": sample_text[:50],
                    },
                ))

    return issues
