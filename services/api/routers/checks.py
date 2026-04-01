from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.api.deps import get_current_user, get_db
from services.api.middleware.tenant import set_tenant_context
from services.api.schemas.check_schemas import (
    CheckRunDetailResponse,
    CheckTriggerResponse,
    IssueResponse,
    SlideDetailResponse,
    SlideResultSummary,
)
from services.db.models.brand import BrandRuleset as BrandRulesetModel
from services.db.models.check import CheckRun, CheckStatus, SlideCheckResult, TriggerType
from services.db.models.deck import Deck

router = APIRouter(prefix="/api", tags=["checks"])


@router.post("/decks/{deck_id}/check", status_code=201)
async def trigger_check(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckTriggerResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)
    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id

    deck_q = select(Deck).where(
        Deck.id == deck_id,
        Deck.org_id == org_uuid,
        Deck.deleted_at.is_(None),
    )
    deck = (await db.execute(deck_q)).scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    ruleset_q = select(BrandRulesetModel).where(
        BrandRulesetModel.org_id == org_uuid,
        BrandRulesetModel.is_active.is_(True),
    )
    ruleset = (await db.execute(ruleset_q)).scalar_one_or_none()
    if not ruleset:
        raise HTTPException(
            status_code=400,
            detail="No active brand ruleset found for this organization",
        )

    check_run = CheckRun(
        id=uuid.uuid4(),
        deck_id=deck_id,
        ruleset_id=ruleset.id,
        org_id=org_uuid,
        triggered_by=TriggerType.manual,
        status=CheckStatus.queued,
    )
    db.add(check_run)
    await db.commit()

    # TODO: enqueue BullMQ job here (Task 5)

    return CheckTriggerResponse(
        check_run_id=str(check_run.id),
        status=check_run.status.value,
    )


@router.get("/checks/{check_run_id}")
async def get_check_run(
    check_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckRunDetailResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)
    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id

    q = (
        select(CheckRun)
        .options(selectinload(CheckRun.slide_results))
        .where(CheckRun.id == check_run_id, CheckRun.org_id == org_uuid)
    )
    check_run = (await db.execute(q)).scalar_one_or_none()
    if not check_run:
        raise HTTPException(status_code=404, detail="Check run not found")

    slides = [
        SlideResultSummary(
            slide_index=sr.slide_index,
            dqs_slide=sr.dqs_slide,
            thumbnail_url=sr.thumbnail_ref or None,
        )
        for sr in sorted(check_run.slide_results, key=lambda s: s.slide_index)
    ]

    return CheckRunDetailResponse(
        id=str(check_run.id),
        deck_id=str(check_run.deck_id),
        status=check_run.status.value,
        dqs_overall=check_run.dqs_overall,
        issue_count_error=check_run.issue_count_error,
        issue_count_warning=check_run.issue_count_warning,
        issue_count_info=check_run.issue_count_info,
        started_at=check_run.started_at,
        completed_at=check_run.completed_at,
        created_at=check_run.created_at,
        slides=slides,
    )


@router.get("/checks/{check_run_id}/slides/{slide_index}")
async def get_slide_issues(
    check_run_id: uuid.UUID,
    slide_index: int,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> SlideDetailResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)
    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id

    check_q = select(CheckRun).where(
        CheckRun.id == check_run_id, CheckRun.org_id == org_uuid
    )
    check_run = (await db.execute(check_q)).scalar_one_or_none()
    if not check_run:
        raise HTTPException(status_code=404, detail="Check run not found")

    slide_q = (
        select(SlideCheckResult)
        .options(selectinload(SlideCheckResult.issues))
        .where(
            SlideCheckResult.check_run_id == check_run_id,
            SlideCheckResult.slide_index == slide_index,
        )
    )
    slide_result = (await db.execute(slide_q)).scalar_one_or_none()
    if not slide_result:
        raise HTTPException(status_code=404, detail="Slide result not found")

    issues = [
        IssueResponse(
            id=str(issue.id),
            rule_type=issue.rule_type,
            severity=issue.severity.value,
            message=issue.message,
            element_id=issue.element_id,
            element_bbox=issue.element_bbox,
            original_value=issue.original_value,
            expected_value=issue.expected_value,
            correction_status=(
                issue.correction_status.value if issue.correction_status else None
            ),
        )
        for issue in slide_result.issues
    ]

    return SlideDetailResponse(
        slide_index=slide_result.slide_index,
        dqs_slide=slide_result.dqs_slide,
        thumbnail_url=slide_result.thumbnail_ref or None,
        issues=issues,
    )
