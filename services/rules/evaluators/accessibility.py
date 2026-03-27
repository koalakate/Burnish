"""Accessibility evaluator — WCAG AA contrast ratio checks."""

from __future__ import annotations

import uuid

from packages.csm.brand import BrandRuleset
from packages.csm.models import Color, Slide
from services.rules.models import Issue, Severity

# ---------------------------------------------------------------------------
# Relative luminance & contrast ratio (WCAG 2.x)
# ---------------------------------------------------------------------------

def _linearize(c: float) -> float:
    """Convert an sRGB channel (0-1) to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(color: Color) -> float:
    """Compute relative luminance per WCAG 2.x definition.

    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    r = _linearize(color.r / 255.0)
    g = _linearize(color.g / 255.0)
    b = _linearize(color.b / 255.0)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: Color, bg: Color) -> float:
    """Compute WCAG contrast ratio between two colors.

    Returns a value between 1.0 and 21.0.
    https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
    """
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_BG = Color(hex="#FFFFFF", r=255, g=255, b=255)


def _is_large_text(size_pt: float | None, weight: int | None) -> bool:
    """Determine if text qualifies as 'large' under WCAG AA.

    Large text: >= 18pt, or >= 14pt and bold (weight >= 700).
    """
    if size_pt is None:
        return False
    if size_pt >= 18.0:
        return True
    if size_pt >= 14.0 and weight is not None and weight >= 700:
        return True
    return False


def _get_slide_bg(slide: Slide) -> Color:
    """Get the effective slide background color.

    Falls back to white if no background is set.
    """
    if slide.background is not None:
        if slide.background.solid_color is not None:
            return slide.background.solid_color
        if slide.background.gradient_colors:
            # Use the first gradient stop as a reasonable approximation
            return slide.background.gradient_colors[0]
    return _DEFAULT_BG


def _get_effective_bg(slide: Slide, shape_fill: Color | None) -> Color:
    """Get the effective background for a text element.

    If the text is inside a shape with a fill color, use that.
    Otherwise fall back to the slide background.
    """
    if shape_fill is not None:
        return shape_fill
    return _get_slide_bg(slide)


# ---------------------------------------------------------------------------
# Text element collection
# ---------------------------------------------------------------------------

def _collect_text_items(
    slide: Slide,
) -> list[tuple[str, str, Color, float | None, int | None, Color]]:
    """Collect text items with their colors and background context.

    Returns: list of (element_id, sample_text, text_color, size_pt, weight, bg_color)
    """
    items: list[tuple[str, str, Color, float | None, int | None, Color]] = []
    slide_bg = _get_slide_bg(slide)

    for elem in slide.elements:
        if elem.type == "text":
            bg = slide_bg
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.color is not None and run.text.strip():
                        items.append((
                            elem.id,
                            run.text[:30],
                            run.color,
                            run.font.size_pt,
                            run.font.weight,
                            bg,
                        ))
        elif elem.type == "shape":
            bg = _get_effective_bg(slide, elem.fill_color)
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.color is not None and run.text.strip():
                        items.append((
                            elem.id,
                            run.text[:30],
                            run.color,
                            run.font.size_pt,
                            run.font.weight,
                            bg,
                        ))
        elif elem.type == "table":
            for cell in elem.cells:
                bg = _get_effective_bg(slide, cell.fill_color)
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.color is not None and run.text.strip():
                            items.append((
                                elem.id,
                                run.text[:30],
                                run.color,
                                run.font.size_pt,
                                run.font.weight,
                                bg,
                            ))
    return items


# ---------------------------------------------------------------------------
# Public evaluator
# ---------------------------------------------------------------------------

def evaluate_accessibility(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check WCAG AA contrast ratios for all text elements on a slide.

    For each text run, computes the contrast ratio between text color and
    background color (shape fill or slide background). Thresholds:
    - Normal text: 4.5:1
    - Large text (>= 18pt, or >= 14pt bold): 3.0:1
    """
    text_items = _collect_text_items(slide)
    issues: list[Issue] = []

    for element_id, sample_text, text_color, size_pt, weight, bg_color in text_items:
        ratio = contrast_ratio(text_color, bg_color)
        large = _is_large_text(size_pt, weight)
        threshold = 3.0 if large else 4.5

        if ratio < threshold:
            issues.append(Issue(
                id=f"accessibility-contrast-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=element_id,
                evaluator="accessibility",
                severity=Severity.error,
                message=(
                    f"Low contrast ({ratio:.1f}:1) \u2014 text on this background "
                    f"needs at least {threshold:.1f}:1 for readability."
                ),
                details={
                    "check": "wcag_aa_contrast",
                    "contrast_ratio": round(ratio, 2),
                    "threshold": threshold,
                    "text_color": text_color.hex,
                    "bg_color": bg_color.hex,
                    "is_large_text": large,
                    "size_pt": size_pt,
                    "weight": weight,
                    "sample_text": sample_text,
                },
            ))

    return issues
