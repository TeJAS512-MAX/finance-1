"""api/routes/token.py — Daily Upstox access & analytics token management via dashboard UI."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from intelligence.readiness import _jwt_expiry_status

router = APIRouter()


class TokenPayload(BaseModel):
    access_token: Optional[str] = None
    analytics_token: Optional[str] = None


def _update_env_var(env_key: str, new_value: str) -> None:
    """Persist an environment key directly into root .env so it survives restarts."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return

    content = env_path.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(env_key)}=.*$"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, f"{env_key}={new_value}", content, flags=re.MULTILINE)
    else:
        sep = "" if content.endswith("\n") or not content else "\n"
        content += f"{sep}{env_key}={new_value}\n"
    env_path.write_text(content, encoding="utf-8")


@router.get("/status", summary="Check if valid Upstox access & analytics tokens are configured")
async def token_status():
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
    is_set = bool(token and len(token) > 50)
    access_status = _jwt_expiry_status(token) if is_set else {"present": False, "expired": True, "expires_at": None}
    token_valid = bool(is_set and not access_status["expired"])

    analytics_token = os.environ.get("UPSTOX_ANALYTICS_TOKEN", "").strip()
    analytics_token_set = len(analytics_token) > 50
    analytics_status = (
        _jwt_expiry_status(analytics_token)
        if analytics_token_set
        else {"present": False, "expired": True, "expires_at": None}
    )
    analytics_valid = bool(analytics_token_set and not analytics_status["expired"])

    masked = f"...{token[-8:]}" if is_set else None
    analytics_masked = f"...{analytics_token[-8:]}" if analytics_token_set else None

    return {
        "token_set": is_set,
        "token_valid": token_valid,
        "token_expired": bool(is_set and access_status["expired"]),
        "expires_at": access_status["expires_at"],
        "masked_token": masked,
        "analytics_token_set": analytics_token_set,
        "analytics_token_valid": analytics_valid,
        "analytics_expired": bool(analytics_token_set and analytics_status["expired"]),
        "analytics_expires_at": analytics_status["expires_at"],
        "analytics_masked_token": analytics_masked,
        "market_data_token_set": analytics_token_set or is_set,
        "market_data_token_valid": analytics_valid or token_valid,
        "updated_at": None,
        "instructions": (
            "Use UPSTOX_ANALYTICS_TOKEN for one-year read-only market data and training. "
            "UPSTOX_ACCESS_TOKEN is a daily token required for live trading."
        ),
    }


@router.post("/update", summary="Save new Upstox access and/or analytics tokens")
async def update_token(payload: TokenPayload):
    access_val = (payload.access_token or "").strip()
    analytics_val = (payload.analytics_token or "").strip()
    if not access_val and not analytics_val:
        return {"success": False, "error": "Provide access_token and/or analytics_token."}

    updated_fields: list[str] = []
    persisted = True
    notes: list[str] = []

    for env_key, tok_val, label in (
        ("UPSTOX_ACCESS_TOKEN", access_val, "Daily access token"),
        ("UPSTOX_ANALYTICS_TOKEN", analytics_val, "Analytics token"),
    ):
        if not tok_val:
            continue
        if len(tok_val) < 50:
            return {"success": False, "error": f"{label} looks too short. Paste the full Upstox JWT token."}
        exp_info = _jwt_expiry_status(tok_val)
        if exp_info["expired"]:
            return {
                "success": False,
                "error": f"{label} is already expired ({exp_info['expires_at']}). Generate a fresh token first.",
            }
        os.environ[env_key] = tok_val
        try:
            _update_env_var(env_key, tok_val)
        except Exception:
            persisted = False
        updated_fields.append(f"{env_key}=...{tok_val[-8:]}")
        notes.append(f"{label} saved (...{tok_val[-8:]})")

    if access_val:
        try:
            from trading.bot_engine import engine

            if engine.broker is not None:
                engine.broker = None
                engine.add_log("WARN", f"New Upstox access token applied at {datetime.now().strftime('%H:%M:%S')}. Broker reset.")
        except Exception:
            pass

    return {
        "success": True,
        "message": "✅ " + " | ".join(notes),
        "updated": updated_fields,
        "persisted_to_env": persisted,
        "note": "Updated token(s) are active immediately in memory and persisted to .env.",
    }
