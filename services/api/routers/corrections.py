from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.api.deps import get_current_user, get_db
from services.api.middleware.tenant import set_tenant_context
from services.api.schemas.correction_schemas import (
    CorrectionActionResponse,
    CorrectionItem,
    CorrectionsListResponse,
    EditCorrectionRequest,
    ExportResponse,
    FixAllResponse,
    SlideCorrectionGroup,
)
from services.db.models.check import (
    CheckRun,
    CheckStatus,
    CorrectionStatus,
    Issue,
    SlideCheckResult,
)
from services.storage.r2 import R2Client
from services.workers.queue import enqueue_job

router = APIRouter(prefix="/api", tags=["corrections"])


def _get_r2() -> R2Client:
    return R2Client()


async def _get_check_run_for_org(
    check_run_id: uuid.UUID,
    org_id: str,
    db: AsyncSession,
) -> CheckRun:
    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
    q = (
        select(CheckRun)
        .options(
            selectinload(CheckRun.slide_results).selectinload(
                SlideCheckResult.issues
            )
        )
        .where(CheckRun.id == check_run_id, CheckRun.org_id == org_uuid)
    )
    check_run = (await db.execute(q)).scalar_one_or_none()
    if not check_run:
        raise HTTPException(status_code=404, detail="Check run not found")
    return check_run


def _issue_to_correction(issue: Issue) -> CorrectionItem:
    return CorrectionItem(
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


@router.get("/checks/{check_run_id}/corrections")
async def list_corrections(
    check_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CorrectionsListResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    check_run = await _get_check_run_for_org(check_run_id, org_id, db)

    groups: dict[int, list[CorrectionItem]] = defaultdict(list)
    total = 0
    for sr in sorted(check_run.slide_results, key=lambda s: s.slide_index):
        for issue in sr.issues:
            if issue.correction_applied or issue.expected_value is not None:
                groups[sr.slide_index].append(_issue_to_correction(issue))
                total += 1

    slides = [
        SlideCorrectionGroup(slide_index=idx, corrections=corrections)
        for idx, corrections in sorted(groups.items())
    ]

    return CorrectionsListResponse(
        check_run_id=str(check_run_id),
        slides=slides,
        total=total,
    )


@router.post("/checks/{check_run_id}/corrections/{correction_id}/accept")
async def accept_correction(
    check_run_id: uuid.UUID,
    correction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CorrectionActionResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    check_run = await _get_check_run_for_org(check_run_id, org_id, db)

    for sr in check_run.slide_results:
        for issue in sr.issues:
            if issue.id == correction_id:
                issue.correction_status = CorrectionStatus.accepted
                await db.commit()
                return CorrectionActionResponse(
                    id=str(correction_id),
                    correction_status=CorrectionStatus.accepted.value,
                )

    raise HTTPException(status_code=404, detail="Correction not found")


@router.post("/checks/{check_run_id}/corrections/{correction_id}/edit")
async def edit_correction(
    check_run_id: uuid.UUID,
    correction_id: uuid.UUID,
    body: EditCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CorrectionActionResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    check_run = await _get_check_run_for_org(check_run_id, org_id, db)

    for sr in check_run.slide_results:
        for issue in sr.issues:
            if issue.id == correction_id:
                issue.correction_status = CorrectionStatus.edited
                issue.expected_value = body.value
                await db.commit()
                return CorrectionActionResponse(
                    id=str(correction_id),
                    correction_status=CorrectionStatus.edited.value,
                )

    raise HTTPException(status_code=404, detail="Correction not found")


@router.post("/checks/{check_run_id}/corrections/{correction_id}/dismiss")
async def dismiss_correction(
    check_run_id: uuid.UUID,
    correction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> CorrectionActionResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    check_run = await _get_check_run_for_org(check_run_id, org_id, db)

    for sr in check_run.slide_results:
        for issue in sr.issues:
            if issue.id == correction_id:
                issue.correction_status = CorrectionStatus.rejected
                await db.commit()
                return CorrectionActionResponse(
                    id=str(correction_id),
                    correction_status=CorrectionStatus.rejected.value,
                )

    raise HTTPException(status_code=404, detail="Correction not found")


@router.post("/checks/{check_run_id}/fix-all")
async def fix_all(
    check_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> FixAllResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    check_run = await _get_check_run_for_org(check_run_id, org_id, db)

    if check_run.status != CheckStatus.complete:
        raise HTTPException(
            status_code=400, detail="Check run is not complete"
        )

    accepted_count = 0
    for sr in check_run.slide_results:
        for issue in sr.issues:
            if issue.correction_status not in (
                CorrectionStatus.rejected,
                CorrectionStatus.edited,
            ):
                if issue.correction_applied or issue.expected_value is not None:
                    issue.correction_status = CorrectionStatus.accepted
                    accepted_count += 1

    await db.commit()

    if accepted_count > 0:
        await enqueue_job(
            "correction",
            {
                "check_run_id": str(check_run_id),
                "deck_id": str(check_run.deck_id),
                "org_id": str(check_run.org_id),
            },
        )

    return FixAllResponse(
        check_run_id=str(check_run_id),
        accepted_count=accepted_count,
        status="accepted" if accepted_count > 0 else "no_corrections",
    )


@router.get("/checks/{check_run_id}/export")
async def get_export(
    check_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
    r2: R2Client = Depends(_get_r2),
) -> ExportResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
    q = select(CheckRun).where(
        CheckRun.id == check_run_id, CheckRun.org_id == org_uuid
    )
    check_run = (await db.execute(q)).scalar_one_or_none()
    if not check_run:
        raise HTTPException(status_code=404, detail="Check run not found")

    if not check_run.exported_pptx_ref:
        raise HTTPException(
            status_code=404, detail="Export not available yet"
        )

    download_url = r2.get_signed_url(check_run.exported_pptx_ref)

    return ExportResponse(
        check_run_id=str(check_run_id),
        download_url=download_url,
        dqs_after=check_run.dqs_overall,
    )
