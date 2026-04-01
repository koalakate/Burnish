"""CorrectionEngine — orchestrates correctors to fix issues in a CSM."""

from __future__ import annotations

from collections.abc import Callable

from packages.csm.brand import BrandRuleset
from packages.csm.models import CSM
from services.rules.models import Issue

Corrector = Callable[[CSM, list[Issue], BrandRuleset], CSM]


class CorrectionEngine:
    """Applies a pipeline of corrector functions to a CSM.

    Each corrector receives the current CSM, the full issue list, and the
    brand ruleset.  It returns a new CSM with its category of issues fixed.
    Correctors are applied in registration order; each sees the output of
    the previous one.
    """

    def __init__(self, correctors: list[Corrector] | None = None) -> None:
        self._correctors: list[Corrector] = list(correctors) if correctors else []

    def register(self, corrector: Corrector) -> None:
        """Append a corrector to the pipeline."""
        self._correctors.append(corrector)

    def run(self, csm: CSM, issues: list[Issue], brand: BrandRuleset) -> CSM:
        """Run all correctors in order and return the corrected CSM."""
        result = csm.model_copy(deep=True)
        for corrector in self._correctors:
            result = corrector(result, issues, brand)
        return result
