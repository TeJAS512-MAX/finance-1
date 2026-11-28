"""
api/routes/auth.py — B2B API key → JWT token exchange endpoint.

POST /api/v1/auth/token
  Body: {"api_key": "<b2b_key>"}
  Returns: {"access_token": "...", "token_type": "bearer", "role": "..."}

This allows B2B client companies to exchange their API key for a short-lived
JWT they can then use on the signals/bot/portfolio/orders routes.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.config import get_settings
from core.security import ROLES_PERMISSIONS, create_access_token

router = APIRouter()


class APIKeyRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_minutes: int


def _lookup_key(api_key: str, raw_keys: str) -> str | None:
    """Constant-time key lookup; returns role or None."""
    matched: str | None = None
    for part in raw_keys.split(","):
        part = part.strip()
        if ":" not in part:
            continue
        k, r = part.split(":", 1)
        if hmac.compare_digest(api_key.encode(), k.strip().encode()):
            matched = r.strip()
    return matched


@router.post("/token", response_model=TokenResponse, summary="Exchange B2B API key for JWT")
async def exchange_api_key(body: APIKeyRequest) -> TokenResponse:
    """
    B2B clients send their API key; receive a scoped short-lived JWT.
    Safe to call without authentication — this is the token issuance endpoint.
    """
    settings = get_settings()
    raw_keys = settings.b2b_api_keys

    if not raw_keys.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="B2B API key authentication is not configured on this server.",
        )

    role = _lookup_key(body.api_key, raw_keys)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if role not in ROLES_PERMISSIONS:
        role = "viewer"  # Defensive default for unknown roles

    token = create_access_token(
        subject=f"b2b:{body.api_key[:6]}...",
        extra_claims={"role": role, "source": "api_key"},
    )

    return TokenResponse(
        access_token=token,
        role=role,
        expires_in_minutes=settings.jwt_access_token_expire_minutes,
    )
