"""Authentication dependencies (X-Server-Token check)."""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.settings import settings


async def token_required(x_server_token: str = Header(..., alias="X-Server-Token")) -> None:
    """Validate the shared token presented by frontend / OC client."""

    if x_server_token != settings.server_token:
        raise HTTPException(status_code=403, detail="Unauthorized, invalid token")
