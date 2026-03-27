from __future__ import annotations

from fastapi import Request

from services.db.engine import async_session


async def get_db():
    async with async_session() as session:
        yield session


async def get_current_user(request: Request) -> dict:
    """Placeholder auth dep — will integrate Clerk JWT later."""
    return {"user_id": "dev-user", "org_id": "dev-org", "role": "owner"}
