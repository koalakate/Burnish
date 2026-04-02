"""Correction worker — runs correction engine, generates corrected PPTX.

Job data:
    check_run_id: str  — UUID of the CheckRun row
    deck_id: str       — UUID of the Deck row
    org_id: str        — UUID of the owning organization
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

from packages.csm.brand import BrandRuleset as BrandRulesetSchema
from packages.csm.models import CSM
from services.correction.correctors.alignment import correct_alignment
from services.correction.correctors.color import correct_colors
from services.correction.correctors.contrast import correct_contrast
from services.correction.correctors.font import correct_fonts
from services.correction.correctors.font_size import correct_font_sizes
from services.correction.engine import CorrectionEngine
from services.correction.exporter import export_pptx
from services.db.engine import async_session
from services.db.models.brand import BrandRuleset as BrandRulesetModel
from services.db.models.check import CheckRun, CheckStatus, CorrectionStatus, SlideCheckResult
from services.db.models.deck import Deck
from services.rules.models import Issue as RuleIssue
from services.rules.models import Severity as RuleSeverity
from services.storage.r2 import R2Client

logger = logging.getLogger(__name__)


def _build_correction_engine() -> CorrectionEngine:
    """Create a correction engine with all standard correctors."""
    engine = CorrectionEngine()
    engine.register(correct_colors)
    engine.register(correct_fonts)
    engine.register(correct_contrast)
    engine.register(correct_font_sizes)
    engine.register(correct_alignment)
    return engine


def _db_issues_to_rule_issues(
    check_run: CheckRun,
) -> list[RuleIssue]:
    """Convert DB Issue models to rule engine Issue models for the correction engine."""
    rule_issues: list[RuleIssue] = []
    for sr in check_run.slide_results:
        for issue in sr.issues:
            if issue.correction_status == CorrectionStatus.rejected:
                continue
            # Reconstruct full details from stored rule_details,
            # falling back to original_value/expected_value
            details: dict[str, object] = dict(issue.rule_details) if issue.rule_details else {}
            if issue.original_value is not None:
                details.setdefault("original_value", issue.original_value)
            if issue.expected_value is not None:
                details["expected_value"] = issue.expected_value
            rule_issues.append(
                RuleIssue(
                    id=str(issue.id),
                    slide_index=sr.slide_index,
                    element_id=issue.element_id or "",
                    evaluator=issue.rule_type,
                    severity=RuleSeverity(issue.severity.value),
                    message=issue.message,
                    details=details,
                )
            )
    return rule_issues


async def process_correction_job(job: Any, _token: Any = None) -> dict[str, Any]:
    """Process a correction job: run corrections, export PPTX, upload to R2."""
    data = job.data if hasattr(job, "data") else job
    check_run_id = data["check_run_id"]
    deck_id = data["deck_id"]
    org_id = data["org_id"]
    logger.info(
        "Correction job started: check_run_id=%s deck_id=%s", check_run_id, deck_id
    )

    r2 = R2Client()
    correction_engine = _build_correction_engine()

    async with async_session() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Load check run with slide results and issues (org-scoped)
        q = (
            select(CheckRun)
            .options(
                selectinload(CheckRun.slide_results).selectinload(
                    SlideCheckResult.issues
                )
            )
            .where(
                CheckRun.id == uuid.UUID(check_run_id),
                CheckRun.org_id == uuid.UUID(org_id),
            )
        )
        check_run = (await db.execute(q)).scalar_one_or_none()
        if not check_run:
            raise ValueError(f"CheckRun {check_run_id} not found")

        try:
            # Load deck and CSM
            deck = await db.get(Deck, uuid.UUID(deck_id))
            if not deck or not deck.csm_ref:
                raise ValueError(f"Deck {deck_id} not found or has no CSM")

            csm_json = r2.download_file(deck.csm_ref)
            csm = CSM.model_validate_json(csm_json)

            # Load brand ruleset
            ruleset_model = await db.get(BrandRulesetModel, check_run.ruleset_id)
            if not ruleset_model:
                raise ValueError(f"BrandRuleset {check_run.ruleset_id} not found")
            brand = BrandRulesetSchema.model_validate(ruleset_model.rules)

            # Convert DB issues to rule issues (excluding rejected)
            rule_issues = _db_issues_to_rule_issues(check_run)

            # Run correction engine
            corrected_csm = correction_engine.run(csm, rule_issues, brand)

            # Store corrected CSM in R2
            corrected_csm_key = r2.org_key(
                org_id, f"checks/{check_run_id}/corrected_csm.json"
            )
            r2.upload_file(
                corrected_csm.model_dump_json().encode(),
                corrected_csm_key,
                content_type="application/json",
            )

            # Download original PPTX, apply corrections, export
            pptx_bytes = r2.download_file(deck.source_ref)
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp.write(pptx_bytes)
                tmp_path = Path(tmp.name)

            try:
                corrected_pptx_bytes = export_pptx(tmp_path, corrected_csm)
            finally:
                tmp_path.unlink(missing_ok=True)

            # Upload corrected PPTX to R2
            export_key = r2.org_key(
                org_id, f"checks/{check_run_id}/corrected.pptx"
            )
            r2.upload_file(
                corrected_pptx_bytes,
                export_key,
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

            # Update check run with export ref
            check_run.exported_pptx_ref = export_key
            await db.commit()

            logger.info(
                "Correction complete: check_run_id=%s export_key=%s",
                check_run_id,
                export_key,
            )
            return {
                "check_run_id": check_run_id,
                "exported_pptx_ref": export_key,
            }

        except Exception:
            logger.exception("Correction failed for check_run_id=%s", check_run_id)
            check_run.exported_pptx_ref = None
            check_run.status = CheckStatus.failed
            await db.commit()
            raise
