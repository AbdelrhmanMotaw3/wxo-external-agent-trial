"""Shared bearer / API-key authentication for Orchestrate callbacks."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app import config


async def require_agent_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected = config.AGENT_AUTH_TOKEN
    if not expected:
        return

    bearer_ok = False
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        bearer_ok = token == expected

    api_key_ok = bool(x_api_key and x_api_key == expected)
    if bearer_ok or api_key_ok:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
    )


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None
