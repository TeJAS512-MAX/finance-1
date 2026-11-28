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


@router.get("/readiness")
async def get_readiness():
    from intelligence.readiness import get_readiness_snapshot

    return get_readiness_snapshot()


@router.post("/swing/paper-scan")
async def run_swing_paper_scan(execute: bool = False, record: bool = False):
    """Score top-5 15d CNC delivery picks, optionally place paper orders, and optionally
    record the tranche into the persistent prospective paper ledger."""
    from core.config import get_settings
    from intelligence.swing_alpha import record_swing_paper_tranche, score_latest_swing_universe
    from trading.paper_broker import PaperBroker

    settings = get_settings()
    if engine.broker is None:
        engine.broker = PaperBroker(initial_capital=settings.paper_trading_initial_capital)

    if execute and not engine.broker.is_paper:
        return {
            "status": "blocked",
            "reason": "PAPER_ONLY_ENDPOINT",
            "orders": [],
        }

    acct = await engine.broker.get_account()
    equity = float(acct.get("total_equity") or settings.paper_trading_initial_capital)
    scored = score_latest_swing_universe(capital=equity)
    placed: list[dict] = []

    if execute and scored.get("status") == "ok":
        existing = {p["symbol"].upper() for p in await engine.broker.get_positions()}
        for rec in scored.get("recommendations", []):
            sym = rec["symbol"].upper()
            qty = int(rec.get("suggested_qty", 0))
            if qty <= 0 or sym in existing:
                continue
            res = await engine.broker.place_order(
                ticker=sym,
                direction="BUY",
                quantity=qty,
                order_type="MARKET",
                price=float(rec["last_close"]),
                tag="swing_15d_cnc",
            )
            placed.append({"symbol": sym, "qty": qty, "result": res})
            if res.get("status") == "FILLED":
                existing.add(sym)

    # Record prospective tranche into the paper ledger
    recorded_tranche = None
    if record and scored.get("status") == "ok" and scored.get("recommendations"):
        recorded_tranche = record_swing_paper_tranche(
            recommendations=scored["recommendations"],
            as_of=scored.get("as_of", ""),
            capital=equity,
        )

    return {
        **scored,
        "executed": execute,
        "orders": placed,
        "ledger_tranche": recorded_tranche,
    }


@router.get("/swing/ledger")
async def get_swing_ledger():
    """Return the full prospective 15-day CNC paper ledger with aggregate stats."""
    from intelligence.swing_alpha import get_swing_paper_ledger_stats

    return get_swing_paper_ledger_stats()


@router.post("/swing/ledger/{tranche_id}/resolve")
async def resolve_swing_ledger_tranche(tranche_id: str, exit_prices: dict):
    """
    Resolve a specific open tranche with actual exit prices.
    Body: {"SYMBOL1": 1234.50, "SYMBOL2": 2345.00, ...}
    """
    from intelligence.swing_alpha import resolve_swing_paper_tranche

    try:
        tranche = resolve_swing_paper_tranche(tranche_id, exit_prices)
        return {"status": "resolved", "tranche": tranche}
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))
