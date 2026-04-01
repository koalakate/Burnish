from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


async def verify_clerk_token(request: Request) -> dict[str, Any]:
    """Placeholder for Clerk JWT verification. Will be replaced with real Clerk SDK."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    # TODO: Verify with Clerk SDK
    return {"user_id": "dev-user", "org_id": "dev-org", "role": "owner"}
