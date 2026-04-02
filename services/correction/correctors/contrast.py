"""Contrast corrector — adjusts colors to meet WCAG AA contrast ratio."""

from __future__ import annotations

from typing import Any

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Color, Paragraph
from services.rules.models import Issue


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Compute relative luminance per WCAG 2.x."""

    def linearize(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        return float(((c + 0.055) / 1.055) ** 2.4)

    rl = linearize(r / 255.0)
    gl = linearize(g / 255.0)
    bl = linearize(b / 255.0)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def _contrast_ratio(fg_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int]) -> float:
    """Compute WCAG contrast ratio."""
    l1 = _relative_luminance(*fg_rgb)
    l2 = _relative_luminance(*bg_rgb)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _adjust_text_color(
    text_rgb: tuple[int, int, int],
    bg_rgb: tuple[int, int, int],
    threshold: float,
) -> tuple[int, int, int]:
    """Darken or lighten the text color until the contrast ratio meets the threshold.

    Strategy: adjust lightness via proportional RGB scaling to preserve the
    original hue and saturation as much as possible.  When darkening, scale
    all channels toward 0 by a common factor; when lightening, scale toward
    255.  Falls back to the opposite direction if the target cannot be
    reached.
    """
    if _contrast_ratio(text_rgb, bg_rgb) >= threshold:
        return text_rgb

    text_lum = _relative_luminance(*text_rgb)
    bg_lum = _relative_luminance(*bg_rgb)

    # Decide direction: if text is darker than bg, make it darker; else lighter
    darken = text_lum <= bg_lum

    def _scale(rgb: tuple[int, int, int], *, toward_black: bool) -> tuple[int, int, int]:
        """Progressively scale rgb toward black (factor→0) or white (factor→1)."""
        r, g, b = rgb
        for step in range(1, 256):
            t = step / 255.0
            if toward_black:
                nr = _clamp(round(r * (1 - t)))
                ng = _clamp(round(g * (1 - t)))
                nb = _clamp(round(b * (1 - t)))
            else:
                nr = _clamp(round(r + (255 - r) * t))
                ng = _clamp(round(g + (255 - g) * t))
                nb = _clamp(round(b + (255 - b) * t))
            if _contrast_ratio((nr, ng, nb), bg_rgb) >= threshold:
                return nr, ng, nb
        return nr, ng, nb

    result = _scale(text_rgb, toward_black=darken)
    if _contrast_ratio(result, bg_rgb) >= threshold:
        return result

    # Opposite direction as fallback
    result = _scale(text_rgb, toward_black=not darken)
    return result


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def correct_contrast(csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
    """Adjust text colors to meet WCAG AA contrast ratio.

    For each contrast issue, darkens or lightens the text color (the less
    prominent color) until the required contrast ratio is met.
    """
    contrast_issues = [
        i for i in issues
        if i.evaluator == "accessibility"
        and i.details.get("check") == "wcag_aa_contrast"
    ]
    if not contrast_issues:
        return csm

    # Build lookup: (slide_index, element_id) -> list of (text_hex, bg_hex, threshold)
    fixes: dict[tuple[int, str], list[dict[str, object]]] = {}
    for issue in contrast_issues:
        key = (issue.slide_index, issue.element_id)
        fixes.setdefault(key, []).append(issue.details)

    for slide in csm.slides:
        for elem in slide.elements:
            fix_list = fixes.get((slide.index, elem.id))
            if not fix_list:
                continue

            # Build text_hex -> new Color mapping from all fixes for this element
            color_map: dict[str, Color] = {}
            for details in fix_list:
                text_hex = str(details.get("text_color", ""))
                bg_hex = str(details.get("bg_color", ""))
                raw_threshold: Any = details.get("threshold", 4.5)
                threshold = float(raw_threshold)

                if not text_hex or not bg_hex:
                    continue

                # Parse hex colors
                th = text_hex.lstrip("#")
                bh = bg_hex.lstrip("#")
                if len(th) != 6 or len(bh) != 6:
                    continue

                text_rgb = (int(th[0:2], 16), int(th[2:4], 16), int(th[4:6], 16))
                bg_rgb = (int(bh[0:2], 16), int(bh[2:4], 16), int(bh[4:6], 16))

                nr, ng, nb = _adjust_text_color(text_rgb, bg_rgb, threshold)
                color_map[text_hex] = Color(
                    hex=_rgb_to_hex(nr, ng, nb), r=nr, g=ng, b=nb,
                )

            # Apply color replacements to text runs
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
                        if run.color is not None and run.color.hex in color_map:
                            run.color = color_map[run.color.hex]

    return csm
