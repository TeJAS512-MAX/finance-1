from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from trading.bot_engine import engine

router = APIRouter()


class StartRequest(BaseModel):
    market_mode: Literal["stocks", "crypto"] = "stocks"

@router.get("/status")
async def get_status():
    return {
        "is_running": engine.is_running,
        "market_mode": engine.market_mode,
        "market_provider": "Upstox" if engine.market_mode == "stocks" else "CoinDCX",
        "crypto_ready": False,
        "logs": engine.logs
    }

@router.post("/start")
async def start_bot(request: StartRequest | None = None):
    market_mode = request.market_mode if request else "stocks"
    started = engine.start(market_mode=market_mode)
    return {
        "status": "started" if started else "unavailable",
        "market_mode": market_mode,
        "message": "CoinDCX adapter is not configured yet." if market_mode == "crypto" else None,
    }

@router.post("/stop")
async def stop_bot():
    engine.stop()
    return {"status": "stopped"}

@router.get("/journal")
async def get_journal():
    return {
        "journal": engine.trade_journal
    }
