from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeckResponse(BaseModel):
    id: str
    name: str
    status: str
    source_type: str
    slide_count: int
    created_at: datetime
    updated_at: datetime


class DeckDetailResponse(DeckResponse):
    source_ref: str
    version_number: int
    thumbnail_urls: list[str] = []


class DeckListResponse(BaseModel):
    items: list[DeckResponse]
    total: int
    page: int
    page_size: int
