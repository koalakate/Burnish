from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from services.db.engine import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_current_user(request: Request) -> dict[str, Any]:
    """Placeholder auth dep — will integrate Clerk JWT later."""
    return {"user_id": "dev-user", "org_id": "dev-org", "role": "owner"}
