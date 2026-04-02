from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.deps import get_current_user, get_db
from services.api.middleware.tenant import set_tenant_context
from services.api.schemas.deck_schemas import (
    DeckDetailResponse,
    DeckListResponse,
    DeckResponse,
)
from services.db.models.deck import Deck, DeckStatus, SourceType
from services.storage.r2 import R2Client
from services.workers.queue import enqueue_job

router = APIRouter(prefix="/api/decks", tags=["decks"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/octet-stream",
}
PPTX_EXTENSION = ".pptx"


def _get_r2() -> R2Client:
    return R2Client()


def _deck_to_response(deck: Deck) -> DeckResponse:
    return DeckResponse(
        id=str(deck.id),
        name=deck.name,
        status=deck.status.value,
        source_type=deck.source_type.value,
        slide_count=deck.slide_count,
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


@router.post("/upload", status_code=201)
async def upload_deck(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
    r2: R2Client = Depends(_get_r2),
) -> dict[str, str]:
    org_id = user["org_id"]
    user_id = user["user_id"]
    await set_tenant_context(db, org_id)

    if not file.filename or not file.filename.lower().endswith(PPTX_EXTENSION):
        raise HTTPException(status_code=400, detail="Only .pptx files are accepted")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail="Only .pptx files are accepted"
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    deck_id = uuid.uuid4()
    r2_key = r2.org_key(org_id, f"decks/{deck_id}/{file.filename}")
    r2.upload_file(
        data,
        r2_key,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        ),
    )

    deck = Deck(
        id=deck_id,
        org_id=uuid.UUID(org_id) if isinstance(org_id, str) else org_id,
        uploaded_by=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        name=file.filename,
        source_type=SourceType.pptx,
        source_ref=r2_key,
        status=DeckStatus.uploaded,
    )
    db.add(deck)
    await db.commit()

    await enqueue_job("ingestion", {"deck_id": str(deck_id), "org_id": org_id})

    return {"deck_id": str(deck_id)}


@router.get("")
async def list_decks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> DeckListResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id

    count_q = (
        select(func.count())
        .select_from(Deck)
        .where(Deck.org_id == org_uuid, Deck.deleted_at.is_(None))
    )
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    q = (
        select(Deck)
        .where(Deck.org_id == org_uuid, Deck.deleted_at.is_(None))
        .order_by(Deck.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    decks = list(result.scalars().all())

    return DeckListResponse(
        items=[_deck_to_response(d) for d in decks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{deck_id}")
async def get_deck(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> DeckDetailResponse:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
    q = select(Deck).where(
        Deck.id == deck_id,
        Deck.org_id == org_uuid,
        Deck.deleted_at.is_(None),
    )
    result = await db.execute(q)
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    return DeckDetailResponse(
        id=str(deck.id),
        name=deck.name,
        status=deck.status.value,
        source_type=deck.source_type.value,
        slide_count=deck.slide_count,
        source_ref=deck.source_ref,
        version_number=deck.version_number,
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


@router.delete("/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    org_id = user["org_id"]
    await set_tenant_context(db, org_id)

    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
    q = select(Deck).where(
        Deck.id == deck_id,
        Deck.org_id == org_uuid,
        Deck.deleted_at.is_(None),
    )
    result = await db.execute(q)
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck.deleted_at = func.now()
    await db.commit()
