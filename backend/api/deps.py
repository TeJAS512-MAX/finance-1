"""
api/deps.py — Shared FastAPI dependencies for B2B authentication and RBAC.

When settings.api_auth_enabled is False (default for development/testing),
all routes are open — existing tests pass without any auth headers.

When api_auth_enabled is True (or app_env == "production"), routes require
EITHER a valid JWT Bearer token OR a valid X-API-Key header.
"""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings
from core.security import ROLES_PERMISSIONS, decode_token, has_permission

_bearer = HTTPBearer(auto_error=False)


def _parse_b2b_keys(raw: str) -> dict[str, str]:
    """Parse 'key1:role1,key2:role2' into {key: role}."""
    result: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if ":" in part:
            k, r = part.split(":", 1)
            if k and r:
                result[k.strip()] = r.strip()
    return result


def _verify_api_key(api_key: str, key_map: dict[str, str]) -> Optional[str]:
    """Constant-time comparison against all configured B2B API keys.
    Returns the matched role string or None."""
    matched_role: Optional[str] = None
    for configured_key, role in key_map.items():
        if hmac.compare_digest(api_key.encode(), configured_key.encode()):
            matched_role = role
    return matched_role


def require_api_access(permission: Optional[str] = None):
    """
    Returns a FastAPI dependency factory that:
    - In dev/test mode (api_auth_enabled=False, app_env != "production"): passes through.
    - In production or when explicitly enabled: validates JWT Bearer or X-API-Key.
    - Optionally enforces a specific RBAC permission.
    """

    async def _dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> dict:
        settings = get_settings()
        auth_required = settings.api_auth_enabled or settings.is_production

        if not auth_required:
            # Open access in development/test mode
            return {"sub": "anonymous", "role": "admin"}

        role: Optional[str] = None
        subject: str = "unknown"

        # 1. Try JWT Bearer token
        if credentials and credentials.credentials:
            try:
                payload = decode_token(credentials.credentials)
                subject = str(payload.get("sub", "unknown"))
                role = str(payload.get("role", "viewer"))
            except Exception:
                pass  # Fall through to X-API-Key

        # 2. Try X-API-Key header
        if role is None and x_api_key:
            key_map = _parse_b2b_keys(settings.b2b_api_keys)
            if key_map:
                role = _verify_api_key(x_api_key, key_map)
                if role:
                    subject = f"apikey:{x_api_key[:6]}..."

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide Authorization: Bearer <JWT> or X-API-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if permission and not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' lacks permission '{permission}'.",
            )

        return {"sub": subject, "role": role}

    return _dep
