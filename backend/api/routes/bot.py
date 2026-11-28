from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.deps import require_api_access
from trading.bot_engine import engine

router = APIRouter()


class StartRequest(BaseModel):
    market_mode: Literal["stocks", "crypto"] = "stocks"


class ManualPaperOrderRequest(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL"]
    quantity: int

@router.get("/status", dependencies=[Depends(require_api_access("read:signals"))])
async def get_status():
    return {
        "is_running": engine.is_running,
        "market_mode": engine.market_mode,
        "market_provider": "Upstox" if engine.market_mode == "stocks" else "CoinDCX",
        "crypto_ready": False,
        "logs": engine.logs
    }

@router.post("/start", dependencies=[Depends(require_api_access("paper_trade"))])
async def start_bot(request: StartRequest | None = None):
    market_mode = request.market_mode if request else "stocks"
    started = engine.start(market_mode=market_mode)
    return {
        "status": "started" if started else "unavailable",
        "market_mode": market_mode,
        "message": "CoinDCX adapter is not configured yet." if market_mode == "crypto" else None,
    }

@router.post("/stop", dependencies=[Depends(require_api_access("paper_trade"))])
async def stop_bot():
    engine.stop()
    return {"status": "stopped"}

@router.get("/journal", dependencies=[Depends(require_api_access("read:signals"))])
async def get_journal():
    return {
        "journal": engine.trade_journal
    }


@router.get("/readiness", dependencies=[Depends(require_api_access("read:signals"))])
async def get_readiness():
    from intelligence.readiness import get_readiness_snapshot

    return get_readiness_snapshot()


@router.post("/swing/paper-scan", dependencies=[Depends(require_api_access("paper_trade"))])
async def run_swing_paper_scan(execute: bool = False, record: bool = False):
    """Score top-5 15d CNC delivery picks, optionally place paper orders using live
    Upstox market prices, and optionally record the tranche into the persistent ledger."""
    from core.config import get_settings
    from intelligence.swing_alpha import record_swing_paper_tranche, score_latest_swing_universe
    from services.providers.upstox_market_data import get_live_quote
    from trading.paper_broker import PaperBroker, default_paper_state_path

    settings = get_settings()
    if engine.broker is None:
        engine.broker = PaperBroker(
            initial_capital=settings.paper_trading_initial_capital,
            state_path=default_paper_state_path(),
        )

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
        existing_positions = await engine.broker.get_positions()
        existing = {p["symbol"].upper() for p in existing_positions}
        for sym_held in list(existing):
            try:
                q_held = await get_live_quote(sym_held)
                if q_held.get("ltp", 0) > 0:
                    engine.broker.update_price(sym_held, float(q_held["ltp"]))
            except Exception:
                pass

        for rec in scored.get("recommendations", []):
            sym = rec["symbol"].upper()
            qty = int(rec.get("suggested_qty", 0))
            if qty <= 0 or sym in existing:
                continue
            exec_price = float(rec["last_close"])
            try:
                quote = await get_live_quote(sym)
                if quote.get("ltp", 0) > 0:
                    exec_price = float(quote["ltp"])
                    rec["live_quote_ltp"] = exec_price
                    rec["last_close"] = exec_price
            except Exception:
                pass
            res = await engine.broker.place_order(
                ticker=sym,
                direction="BUY",
                quantity=qty,
                order_type="MARKET",
                price=exec_price,
                tag="swing_15d_cnc",
            )
            placed.append({"symbol": sym, "qty": qty, "exec_price": exec_price, "result": res})
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


@router.post("/swing/mark-to-market", dependencies=[Depends(require_api_access("paper_trade"))])
async def mark_paper_positions_to_live():
    """Refresh all open paper positions using live Upstox market quotes."""
    from core.config import get_settings
    from services.providers.upstox_market_data import get_live_quote
    from trading.paper_broker import PaperBroker, default_paper_state_path

    if engine.broker is None:
        settings = get_settings()
        engine.broker = PaperBroker(
            initial_capital=settings.paper_trading_initial_capital,
            state_path=default_paper_state_path(),
        )
    if not engine.broker.is_paper:
        return {"status": "blocked", "reason": "PAPER_ONLY_ENDPOINT", "updated": []}

    updated: list[dict] = []
    for pos in await engine.broker.get_positions():
        sym = pos["symbol"].upper()
        ticker = pos["ticker"]
        try:
            q = await get_live_quote(sym)
            ltp = float(q.get("ltp", 0.0))
            if ltp > 0:
                engine.broker.update_price(ticker, ltp)
                updated.append({"symbol": sym, "ltp": ltp})
        except Exception:
            continue

    acct = await engine.broker.get_account()
    return {"status": "ok", "updated": updated, "account": acct}


@router.post("/paper-order", dependencies=[Depends(require_api_access("paper_trade"))])
async def place_manual_paper_order(payload: ManualPaperOrderRequest):
    """Execute a simulated BUY or SELL order in PaperBroker using live Upstox LTP."""
    from fastapi import HTTPException
    from core.config import get_settings
    from services.providers.upstox_market_data import INSTRUMENT_KEYS, get_live_quote
    from trading.paper_broker import PaperBroker, default_paper_state_path

    sym = payload.symbol.strip().upper()
    if sym not in INSTRUMENT_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown NSE symbol: {sym}")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")

    settings = get_settings()
    if engine.broker is None:
        engine.broker = PaperBroker(
            initial_capital=settings.paper_trading_initial_capital,
            state_path=default_paper_state_path(),
        )
    if not engine.broker.is_paper:
        return {"status": "blocked", "reason": "PAPER_ONLY_ENDPOINT"}

    quote = await get_live_quote(sym)
    px = float(quote.get("ltp") or quote.get("close") or 0.0)
    if px <= 0:
        raise HTTPException(status_code=502, detail=f"No valid Upstox price available for {sym}.")

    result = await engine.broker.place_order(
        ticker=sym,
        direction=payload.direction,
        quantity=payload.quantity,
        order_type="MARKET",
        price=px,
        tag="manual_desk_paper",
    )
    account = await engine.broker.get_account()
    return {"status": result.get("status"), "order": result, "account": account, "quote_ltp": px}


@router.get("/swing/ledger", dependencies=[Depends(require_api_access("read:signals"))])
async def get_swing_ledger():
    """Return the full prospective 15-day CNC paper ledger with aggregate stats."""
    from intelligence.swing_alpha import get_swing_paper_ledger_stats

    return get_swing_paper_ledger_stats()


@router.post("/swing/ledger/{tranche_id}/resolve", dependencies=[Depends(require_api_access("paper_trade"))])
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
