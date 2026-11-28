"""api/routes/signals.py — Real-time trade signals from Upstox Official NSE data."""
import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
import httpx

from api.deps import require_api_access
from core.logging_config import get_logger
from intelligence.stock_direction import get_candidate_status

router = APIRouter()
logger = get_logger("signals")

# Instruments the AI watches — must match upstox_market_data.INSTRUMENT_KEYS
WATCHLIST = ['RELIANCE', 'INFY', 'TCS', 'SBIN', 'ZOMATO', 'ITC', 'ICICIBANK', 'WIPRO']


async def _analyze_symbol(
    symbol: str,
    market_candles: list[dict] | None = None,
) -> dict | None:
    """Run the shared technical, ML, and AI-arbiter pipeline."""
    try:
        from services.providers.upstox_market_data import compute_features, get_candles
        from intelligence.decision_engine import analyze_setup
        from intelligence.stock_direction import (
            MODEL_PATH,
            candidate_supports_symbol,
            predict_next_session,
        )

        features = await compute_features(symbol, interval="30m")
        decision = analyze_setup(features)
        rsi = features["rsi"]
        next_session_prediction = None
        prediction_status = "model_not_trained"
        if MODEL_PATH.is_file():
            prediction_status = "symbol_not_qualified"
            try:
                if candidate_supports_symbol(symbol):
                    prediction_status = "unavailable"
                    daily_candles = await get_candles(symbol, interval="1D", days_back=90)
                    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
                    if (
                        daily_candles
                        and datetime.fromisoformat(daily_candles[-1]["timestamp"]).date() == now_ist.date()
                        and now_ist.time() < time(15, 30)
                    ):
                        daily_candles = daily_candles[:-1]
                    next_session_prediction = predict_next_session(
                        symbol,
                        daily_candles,
                        market_candles=market_candles,
                    )
                    prediction_status = "available"
            except (ValueError, httpx.HTTPError, OSError, KeyError):
                logger.exception("Next-session prediction unavailable for %s", symbol)
            except Exception:
                logger.exception("Unexpected next-session prediction failure for %s", symbol)

        return {
            "id": f"sig_{symbol}",
            "symbol": symbol,
            "direction": (
                decision["candidate_direction"]
                if decision["decision"] == "TRADE"
                else "NO_TRADE"
            ),
            "candidateDirection": decision["candidate_direction"],
            "decision": decision["decision"],
            "confidence": round((decision["ml_probability"] or 0.0) * 100),
            "timeHorizon": "INTRADAY",
            "eventType": decision["reason"],
            "verificationStatus": "AI FILTERED",
            "informationType": "LIVE DATA + ML",
            "technicalScore": decision["technical_score"],
            "mlProbability": decision["ml_probability"],
            "scoreBreakdown": decision["score_breakdown"],
            "nextSessionPrediction": next_session_prediction,
            "nextSessionPredictionStatus": prediction_status,
            "ltp": round(features["ltp"], 2),
            "rsi": round(rsi, 1),
            "sma20": round(features["sma20"], 2),
            "generatedAt": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception:
        logger.exception("Live signal analysis failed for %s", symbol)
        return None


@router.get("", summary="List live AI trade signals based on RSI/SMA analysis", dependencies=[Depends(require_api_access("read:signals"))])
async def list_signals():
    """Fetches real candles for all watchlist stocks and returns live signals."""
    try:
        try:
            direction_model = get_candidate_status()
        except Exception:
            logger.exception("Failed to load next-session model evaluation status")
            direction_model = {"state": "unavailable"}

        market_candles = None
        if (
            direction_model.get("state") == "qualified_research"
            and direction_model.get("requires_market_context", False)
        ):
            try:
                from services.providers.upstox_market_data import get_daily_history_v3

                market_candles = await get_daily_history_v3("NIFTY50", days_back=90)
            except Exception:
                logger.exception("NIFTY50 market context is unavailable for predictions")

        tasks = [
            _analyze_symbol(sym, market_candles)
            if market_candles is not None
            else _analyze_symbol(sym)
            for sym in WATCHLIST
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals = [r for r in results if isinstance(r, dict)]
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        try:
            from intelligence.swing_alpha import get_swing_status

            swing_model = get_swing_status()
        except Exception:
            swing_model = {"state": "unavailable", "swing_oos_ready": False}

        return {
            "signals": signals,
            "direction_model": direction_model,
            "swing_model": swing_model,
            "scanned_at": datetime.now().isoformat(),
            "source": "Upstox Official API (Real-time NSE)"
        }
    except Exception:
        logger.exception("Failed to build live signal response")
        return {
            "signals": [],
            "direction_model": {"state": "unavailable"},
            "swing_model": {"state": "unavailable", "swing_oos_ready": False},
            "scanned_at": datetime.now().isoformat(),
            "source": "Upstox Official API (Real-time NSE)"
        }


@router.get("/swing", summary="Top 15-day CNC delivery swing alpha picks", dependencies=[Depends(require_api_access("read:signals"))])
async def list_swing_signals():
    """Return latest ranked 15-trading-day CNC delivery opportunities and OOS readiness status."""
    from core.config import get_settings
    from intelligence.swing_alpha import get_swing_status, score_latest_swing_universe
    from services.providers.upstox_market_data import INSTRUMENT_KEYS

    capital = get_settings().paper_trading_initial_capital
    scored = score_latest_swing_universe(capital=capital)
    return {
        **scored,
        "universe_symbols": sorted(INSTRUMENT_KEYS.keys()),
        "swing_model": get_swing_status(),
    }


@router.get("/quote/{symbol}", summary="Fetch live Upstox quote and metadata for any registered NSE symbol", dependencies=[Depends(require_api_access("read:signals"))])
async def get_symbol_live_quote(symbol: str):
    """Return live/last-session Upstox market quote, sector, and instrument key for a symbol."""
    from fastapi import HTTPException
    from services.providers.upstox_market_data import INSTRUMENT_KEYS, get_live_quote
    from trading.bot_engine import SYMBOL_SECTORS

    sym = symbol.strip().upper()
    if sym not in INSTRUMENT_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown NSE symbol: {sym}")

    try:
        quote = await get_live_quote(sym)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstox quote unavailable for {sym}: {exc}")

    return {
        **quote,
        "sector": SYMBOL_SECTORS.get(sym, "OTHER"),
    }


@router.get("/{thesis_id}", summary="Get trade thesis detail", dependencies=[Depends(require_api_access("read:signals"))])
async def get_thesis(thesis_id: str):
    return {"thesis_id": thesis_id, "status": "not_yet_implemented"}
