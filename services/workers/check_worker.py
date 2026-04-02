"""Check worker — runs rule engine + vision scorer, calculates DQS, stores results.

Job data:
    check_run_id: str  — UUID of the CheckRun row
    deck_id: str       — UUID of the Deck row
    org_id: str        — UUID of the owning organization
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from packages.csm.brand import BrandRuleset as BrandRulesetSchema
from packages.csm.models import CSM
from services.db.engine import async_session
from services.db.models.brand import BrandRuleset as BrandRulesetModel
from services.db.models.check import (
    CheckRun,
    CheckStatus,
    CorrectionStatus,
    SlideCheckResult,
)
from services.db.models.check import (
    Issue as IssueModel,
)
from services.db.models.check import (
    Severity as DBSeverity,
)
from services.db.models.deck import Deck
from services.rules.dqs import calculate_dqs
from services.rules.engine import RuleEngine
from services.rules.evaluators.accessibility import evaluate_accessibility
from services.rules.evaluators.color import evaluate_colors
from services.rules.evaluators.content import evaluate_content
from services.rules.evaluators.image import evaluate_images
from services.rules.evaluators.layout import evaluate_layout
from services.rules.evaluators.typography import evaluate_typography
from services.rules.models import Issue as RuleIssue
from services.storage.r2 import R2Client
from services.vision.scorer import VisionScore

logger = logging.getLogger(__name__)


def _build_rule_engine() -> RuleEngine:
    """Create a rule engine with all standard evaluators."""
    engine = RuleEngine()
    engine.register(evaluate_colors)
    engine.register(evaluate_typography)
    engine.register(evaluate_content)
    engine.register(evaluate_layout)
    engine.register(evaluate_images)
    engine.register(evaluate_accessibility)
    return engine


def _severity_to_db(severity_str: str) -> DBSeverity:
    return DBSeverity(severity_str)


def _derive_expected_value(ri: RuleIssue) -> str | None:
    """Derive the expected correction value from evaluator-specific details."""
    d = ri.details
    if not d:
        return None

    evaluator = ri.evaluator
    check = d.get("check", "")

    if evaluator == "color":
        val = d.get("nearest_brand_hex")
        return str(val) if val else None
    if evaluator == "typography":
        if check == "font_family":
            families = d.get("allowed_families")
            if isinstance(families, list) and families:
                return str(families[0])
        if check == "font_size":
            min_pt = d.get("min_pt")
            actual = d.get("actual_size_pt")
            max_pt = d.get("max_pt")
            if (
                isinstance(actual, (int, float))
                and isinstance(min_pt, (int, float))
                and actual < min_pt
            ):
                return str(min_pt)
            if (
                isinstance(actual, (int, float))
                and isinstance(max_pt, (int, float))
                and actual > max_pt
            ):
                return str(max_pt)
    if evaluator == "accessibility" and check == "wcag_aa_contrast":
        return "auto"
    if evaluator == "layout" and check == "margin":
        val = d.get("required_inches")
        return str(val) if val is not None else None

    return None


def _derive_original_value(ri: RuleIssue) -> str | None:
    """Derive the original value from evaluator-specific details."""
    d = ri.details
    if not d:
        return None

    evaluator = ri.evaluator
    check = d.get("check", "")

    if evaluator == "color":
        val = d.get("actual_hex")
        return str(val) if val else None
    if evaluator == "typography":
        if check == "font_family":
            val = d.get("actual_family")
            return str(val) if val else None
        if check == "font_size":
            val = d.get("actual_size_pt")
            return str(val) if val is not None else None
    if evaluator == "accessibility" and check == "wcag_aa_contrast":
        val = d.get("contrast_ratio")
        return f"{val}:1" if val is not None else None
    if evaluator == "layout" and check == "margin":
        val = d.get("actual_inches")
        if isinstance(val, (int, float)):
            return str(round(val, 2))
        return None

    return None


async def process_check_job(job: Any, _token: Any = None) -> dict[str, Any]:
    """Process a check job: load CSM, run evaluators, calculate DQS, store results."""
    data = job.data if hasattr(job, "data") else job
    check_run_id = data["check_run_id"]
    deck_id = data["deck_id"]
    org_id = data["org_id"]
    logger.info("Check job started: check_run_id=%s deck_id=%s", check_run_id, deck_id)

    r2 = R2Client()
    engine = _build_rule_engine()

    async with async_session() as db:
        # Mark as running
        check_run = await db.get(CheckRun, uuid.UUID(check_run_id))
        if not check_run:
            raise ValueError(f"CheckRun {check_run_id} not found")
        if str(check_run.org_id) != org_id:
            raise ValueError(f"CheckRun {check_run_id} does not belong to org {org_id}")
        check_run.status = CheckStatus.running
        check_run.started_at = datetime.now(UTC)
        await db.commit()

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

            # Run rule engine
            rule_issues = engine.run(csm, brand)

            # Vision scoring is optional — skip if no API key configured
            vision_scores: list[VisionScore] = []

            # Separate accessibility issues for DQS
            accessibility_issues: list[RuleIssue] = []
            for slide_set in rule_issues:
                for issue in slide_set.issues:
                    if issue.evaluator == "accessibility":
                        accessibility_issues.append(issue)

            # Calculate DQS
            dqs_report = calculate_dqs(rule_issues, vision_scores, accessibility_issues)

            # Store results in DB
            error_count = 0
            warning_count = 0
            info_count = 0

            for slide_dqs in dqs_report.slides:
                slide_idx = slide_dqs.slide_index
                slide_rule_issues = (
                    rule_issues[slide_idx].issues if slide_idx < len(rule_issues) else []
                )

                # Thumbnail ref (if ingestion uploaded thumbnails)
                thumb_ref = r2.org_key(
                    org_id, f"decks/{deck_id}/thumbnails/slide_{slide_idx}.png"
                )

                slide_result = SlideCheckResult(
                    id=uuid.uuid4(),
                    check_run_id=uuid.UUID(check_run_id),
                    slide_index=slide_idx,
                    dqs_slide=slide_dqs.dqs,
                    vision_scores=(
                        vision_scores[slide_idx].model_dump()
                        if slide_idx < len(vision_scores)
                        else {}
                    ),
                    thumbnail_ref=thumb_ref,
                )
                db.add(slide_result)
                await db.flush()

                # Store individual issues
                for ri in slide_rule_issues:
                    sev = _severity_to_db(ri.severity.value)
                    if sev == DBSeverity.error:
                        error_count += 1
                    elif sev == DBSeverity.warning:
                        warning_count += 1
                    else:
                        info_count += 1

                    # Normalize bbox from EMU to pixel coordinates (960x540)
                    normalized_bbox = None
                    if ri.bbox and csm.width > 0 and csm.height > 0:
                        normalized_bbox = {
                            "x": ri.bbox.x / csm.width * 960,
                            "y": ri.bbox.y / csm.height * 540,
                            "width": ri.bbox.width / csm.width * 960,
                            "height": ri.bbox.height / csm.height * 540,
                        }

                    expected_val = _derive_expected_value(ri)
                    original_val = _derive_original_value(ri)

                    issue_model = IssueModel(
                        id=uuid.uuid4(),
                        slide_result_id=slide_result.id,
                        rule_type=ri.evaluator,
                        severity=sev,
                        message=ri.message,
                        element_id=ri.element_id or None,
                        element_bbox=normalized_bbox,
                        original_value=original_val,
                        expected_value=expected_val,
                        rule_details={
                            k: v3
                            for k, v3 in ri.details.items()
                            if isinstance(v3, (str, int, float, bool, list, dict, type(None)))
                        } if ri.details else None,
                        correction_applied=expected_val is not None,
                        correction_status=(
                            CorrectionStatus.pending
                            if expected_val is not None
                            else None
                        ),
                    )
                    db.add(issue_model)

            # Update check run
            check_run.status = CheckStatus.complete
            check_run.dqs_overall = dqs_report.overall_dqs
            check_run.issue_count_error = error_count
            check_run.issue_count_warning = warning_count
            check_run.issue_count_info = info_count
            check_run.completed_at = datetime.now(UTC)
            await db.commit()

            logger.info(
                "Check complete: check_run_id=%s dqs=%.1f issues=%d/%d/%d",
                check_run_id,
                dqs_report.overall_dqs,
                error_count,
                warning_count,
                info_count,
            )
            return {
                "check_run_id": check_run_id,
                "dqs_overall": dqs_report.overall_dqs,
                "issue_count": error_count + warning_count + info_count,
            }

        except Exception:
            logger.exception("Check failed for check_run_id=%s", check_run_id)
            check_run.status = CheckStatus.failed
            check_run.completed_at = datetime.now(UTC)
            await db.commit()
            raise
