from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, org_id: str) -> None:
    """Set PostgreSQL RLS context for multi-tenant isolation."""
    await session.execute(text("SET app.current_org_id = :org_id"), {"org_id": org_id})
