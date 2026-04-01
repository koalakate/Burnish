"""Image evaluator — checks DPI, aspect ratio distortion, and missing alt text."""

from __future__ import annotations

import uuid

from packages.csm.brand import BrandRuleset
from packages.csm.models import Slide
from services.rules.models import Issue, Severity

_DEFAULT_MIN_DPI = 150.0
_DEFAULT_ASPECT_RATIO_TOLERANCE = 0.05  # 5%


def evaluate_images(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check image quality for a single slide.

    Checks:
    - Image DPI below minimum (print quality).
    - Aspect ratio distortion (stretched or squished beyond tolerance).
    - Missing alt text (accessibility).
    """
    tolerances = brand.custom_tolerances
    min_dpi = _DEFAULT_MIN_DPI if tolerances.image_min_dpi is None else tolerances.image_min_dpi
    ar_tolerance = _DEFAULT_ASPECT_RATIO_TOLERANCE if tolerances.aspect_ratio_tolerance is None else tolerances.aspect_ratio_tolerance
    issues: list[Issue] = []

    for elem in slide.elements:
        if elem.type != "image":
            continue

        elem_id = elem.id or elem.name or "unknown"

        # --- DPI check ---
        if elem.dpi is not None and elem.dpi < min_dpi:
            issues.append(Issue(
                id=f"image-dpi-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="image",
                severity=Severity.warning,
                message=(
                    f"Image '{elem.name}' has {elem.dpi:.0f} DPI, below the "
                    f"minimum of {min_dpi:.0f} DPI for print quality."
                ),
                details={
                    "check": "image_dpi",
                    "actual_dpi": elem.dpi,
                    "min_dpi": min_dpi,
                },
                bbox=elem.bbox,
            ))

        # --- Aspect ratio distortion check ---
        if (
            elem.original_width is not None
            and elem.original_height is not None
            and elem.original_width > 0
            and elem.original_height > 0
            and elem.bbox.width > 0
            and elem.bbox.height > 0
        ):
            original_ar = elem.original_width / elem.original_height
            displayed_ar = elem.bbox.width / elem.bbox.height
            distortion = abs(displayed_ar - original_ar) / original_ar

            if distortion > ar_tolerance:
                issues.append(Issue(
                    id=f"image-aspect-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                    slide_index=slide.index,
                    element_id=elem_id,
                    evaluator="image",
                    severity=Severity.warning,
                    message=(
                        f"Image '{elem.name}' appears distorted "
                        f"({distortion:.0%} aspect ratio change). "
                        "Original proportions may have been altered."
                    ),
                    details={
                        "check": "aspect_ratio",
                        "original_aspect_ratio": round(original_ar, 4),
                        "displayed_aspect_ratio": round(displayed_ar, 4),
                        "distortion_pct": round(distortion * 100, 2),
                        "tolerance_pct": round(ar_tolerance * 100, 2),
                    },
                    bbox=elem.bbox,
                ))

        # --- Missing alt text check ---
        if not elem.alt_text or not elem.alt_text.strip():
            issues.append(Issue(
                id=f"image-alt-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="image",
                severity=Severity.error,
                message=(
                    f"Image '{elem.name}' is missing alt text. "
                    "Add a description for accessibility."
                ),
                details={
                    "check": "alt_text",
                    "element_name": elem.name,
                },
                bbox=elem.bbox,
            ))

    return issues
