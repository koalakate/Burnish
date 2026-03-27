"""Rule engine — orchestrates evaluators against a CSM and brand ruleset."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM, Slide
from services.rules.models import Issue, SlideIssueSet

# An evaluator is any callable with this signature:
#   (slide: Slide, brand: BrandRuleset) -> list[Issue]
Evaluator = Callable[[Slide, BrandRuleset], list[Issue]]


class AsyncEvaluator(Protocol):
    """Protocol for async evaluators."""

    async def __call__(self, slide: Slide, brand: BrandRuleset) -> list[Issue]: ...


class RuleEngine:
    """Runs a set of evaluators against every slide in a CSM."""

    def __init__(self, evaluators: list[Evaluator] | None = None) -> None:
        self._evaluators: list[Evaluator] = list(evaluators or [])

    def register(self, evaluator: Evaluator) -> None:
        """Add an evaluator to the engine."""
        self._evaluators.append(evaluator)

    def run(self, csm: CSM, brand: BrandRuleset) -> list[SlideIssueSet]:
        """Run all evaluators against every slide, returning per-slide issue sets."""
        result: list[SlideIssueSet] = []
        for slide in csm.slides:
            issues = self._run_slide(slide, brand)
            result.append(SlideIssueSet(slide_index=slide.index, issues=issues))
        return result

    async def run_async(self, csm: CSM, brand: BrandRuleset) -> list[SlideIssueSet]:
        """Run all evaluators against every slide in parallel."""
        tasks = [
            asyncio.to_thread(self._run_slide, slide, brand) for slide in csm.slides
        ]
        slide_issues = await asyncio.gather(*tasks)
        return [
            SlideIssueSet(slide_index=slide.index, issues=issues)
            for slide, issues in zip(csm.slides, slide_issues)
        ]

    def _run_slide(self, slide: Slide, brand: BrandRuleset) -> list[Issue]:
        """Run all evaluators on a single slide and deduplicate issues."""
        all_issues: list[Issue] = []
        seen_ids: set[str] = set()
        for evaluator in self._evaluators:
            for issue in evaluator(slide, brand):
                if issue.id not in seen_ids:
                    seen_ids.add(issue.id)
                    all_issues.append(issue)
        return all_issues
