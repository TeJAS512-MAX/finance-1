"""
core/security.py — Authentication, JWT, password hashing, RBAC.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

settings = get_settings()


# ── Password hashing ─────────────────────────────────────────

def _prehash(password: str) -> bytes:
    """SHA-256 pre-hash encoded as base64 so bcrypt handles any password length."""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=settings.bcrypt_rounds))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            if bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8")):
                return True
        except ValueError:
            pass
        try:
            return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
        except ValueError:
            return False
    return False


# ── JWT tokens ───────────────────────────────────────────────

def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )


# ── Roles ─────────────────────────────────────────────────────

ROLES_PERMISSIONS: Dict[str, list[str]] = {
    "viewer":    ["read:portfolio", "read:signals", "read:journal"],
    "analyst":   ["read:*", "write:watchlist"],
    "trader":    ["read:*", "write:*", "paper_trade"],
    "admin":     ["read:*", "write:*", "paper_trade", "admin"],
}


def has_permission(role: str, permission: str) -> bool:
    perms = ROLES_PERMISSIONS.get(role, [])
    return permission in perms or "admin" in perms or "read:*" in perms
