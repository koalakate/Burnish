"""Content evaluator — checks text density, bullet count, and empty placeholders."""

from __future__ import annotations

import uuid

from packages.csm.brand import BrandRuleset
from packages.csm.models import Paragraph, Slide
from services.rules.models import Issue, Severity

_DEFAULT_MAX_WORDS = 150
_DEFAULT_MAX_BULLETS = 7


def _count_words(paragraphs: list[Paragraph]) -> int:
    """Count total words across all runs in a list of paragraphs."""
    total = 0
    for para in paragraphs:
        for run in para.runs:
            total += len(run.text.split())
    return total


def _count_bullets(paragraphs: list[Paragraph]) -> int:
    """Count paragraphs that look like bullet items (level >= 1 or non-empty at level 0)."""
    return sum(
        1
        for p in paragraphs
        if p.level >= 1 and any(r.text.strip() for r in p.runs)
    )


def _has_text(paragraphs: list[Paragraph]) -> bool:
    """Return True if any run has non-whitespace text."""
    return any(r.text.strip() for p in paragraphs for r in p.runs)


def evaluate_content(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check content quality for a single slide.

    Checks:
    - Text density: too many words on one slide.
    - Bullet count: more than the allowed number of bullets in a single text element.
    - Empty text placeholders.
    """
    tolerances = brand.custom_tolerances
    max_words = tolerances.max_words_per_slide or _DEFAULT_MAX_WORDS
    max_bullets = tolerances.max_bullets_per_slide or _DEFAULT_MAX_BULLETS
    issues: list[Issue] = []

    # --- Text density (slide-level word count) ---
    total_words = 0
    for elem in slide.elements:
        if elem.type == "text":
            total_words += _count_words(elem.paragraphs)
        elif elem.type == "shape":
            total_words += _count_words(elem.paragraphs)
        elif elem.type == "table":
            for cell in elem.cells:
                total_words += _count_words(cell.paragraphs)

    if total_words > max_words:
        issues.append(Issue(
            id=f"content-density-{slide.index}-{uuid.uuid4().hex[:8]}",
            slide_index=slide.index,
            element_id="",
            evaluator="content",
            severity=Severity.warning,
            message=(
                f"Slide has {total_words} words, exceeding the recommended "
                f"maximum of {max_words}. Consider splitting content across slides."
            ),
            details={
                "check": "text_density",
                "actual_words": total_words,
                "max_words": max_words,
            },
        ))

    # --- Bullet count and empty placeholders (per-element) ---
    for elem in slide.elements:
        if elem.type == "text":
            paragraphs = elem.paragraphs
        elif elem.type == "shape":
            paragraphs = elem.paragraphs
        else:
            continue

        elem_id = elem.id or elem.name or "unknown"

        # Empty placeholder check
        if not _has_text(paragraphs) and elem.type == "text":
            issues.append(Issue(
                id=f"content-empty-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="content",
                severity=Severity.info,
                message=(
                    f"Text placeholder '{elem.name}' is empty. "
                    "Remove it or add content."
                ),
                details={
                    "check": "empty_placeholder",
                    "element_name": elem.name,
                },
                bbox=elem.bbox,
            ))

        # Bullet count check
        bullet_count = _count_bullets(paragraphs)
        if bullet_count > max_bullets:
            issues.append(Issue(
                id=f"content-bullets-{slide.index}-{elem_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=elem_id,
                evaluator="content",
                severity=Severity.warning,
                message=(
                    f"Element has {bullet_count} bullet points, exceeding the "
                    f"recommended maximum of {max_bullets}. Consider breaking "
                    "into multiple slides."
                ),
                details={
                    "check": "bullet_count",
                    "actual_bullets": bullet_count,
                    "max_bullets": max_bullets,
                },
                bbox=elem.bbox,
            ))

    return issues
