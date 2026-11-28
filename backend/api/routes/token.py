"""api/routes/token.py — Daily Upstox access token management via the dashboard UI."""
from fastapi import APIRouter
from pydantic import BaseModel
import os
import re
from pathlib import Path
from datetime import datetime

router = APIRouter()

class TokenPayload(BaseModel):
    access_token: str

def _update_env_file(new_token: str) -> None:
    """Write the new token directly into the .env file so it persists on restart."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return
    
    content = env_path.read_text(encoding="utf-8")
    # Replace the token line if it exists
    if "UPSTOX_ACCESS_TOKEN=" in content:
        content = re.sub(
            r"UPSTOX_ACCESS_TOKEN=.*",
            f"UPSTOX_ACCESS_TOKEN={new_token}",
            content
        )
    else:
        content += f"\nUPSTOX_ACCESS_TOKEN={new_token}\n"
    
    env_path.write_text(content, encoding="utf-8")

@router.get("/status", summary="Check if a valid access token is set")
async def token_status():
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    is_set = bool(token and len(token) > 50)
    analytics_token = os.environ.get("UPSTOX_ANALYTICS_TOKEN", "").strip()
    analytics_token_set = len(analytics_token) > 50
    
    # Mask the token for display — show only last 8 chars
    masked = f"...{token[-8:]}" if is_set else None
    
    return {
        "token_set": is_set,
        "masked_token": masked,
        "analytics_token_set": analytics_token_set,
        "market_data_token_set": analytics_token_set or is_set,
        "updated_at": None,  # Could store this in memory if needed
        "instructions": (
            "Use UPSTOX_ANALYTICS_TOKEN for one-year read-only market data and training. "
            "UPSTOX_ACCESS_TOKEN is a daily token required for live trading."
        ),
    }

@router.post("/update", summary="Save a new Upstox access token")
async def update_token(payload: TokenPayload):
    token = payload.access_token.strip()
    
    if len(token) < 50:
        return {"success": False, "error": "Token looks too short. Please paste the full JWT token from Upstox."}
    
    # 1. Update in-memory environment (takes effect immediately for this process)
    os.environ["UPSTOX_ACCESS_TOKEN"] = token
    
    # 2. Persist to .env file so it survives a server restart
    try:
        _update_env_file(token)
        persisted = True
    except Exception as e:
        persisted = False
    
    # 3. Reset the bot engine's broker so next run picks up the new token
    try:
        from trading.bot_engine import engine
        if engine.broker is not None:
            engine.broker = None
            engine.add_log("WARN", f"🔑 New Upstox token applied at {datetime.now().strftime('%H:%M:%S')}. Broker reset.")
    except Exception:
        pass
    
    masked = f"...{token[-8:]}"
    
    return {
        "success": True,
        "message": f"✅ Token saved! Masked: {masked}",
        "persisted_to_env": persisted,
        "note": "The new token is active immediately. Start the Trading Engine to begin trading."
    }
