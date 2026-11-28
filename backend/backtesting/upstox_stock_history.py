"""Fresh daily stock history from the Upstox API for net-return model training."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from services.providers.upstox_market_data import (
    INSTRUMENT_KEYS,
    MARKET_CONTEXT_INSTRUMENT_KEYS,
    get_daily_history_v3,
    get_market_data_token,
)

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "historical_candles_upstox_daily.json"
MAX_DAILY_HISTORY_DAYS = 3650
MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
DAILY_CANDLE_CUTOFF = time(15, 45)


async def fetch_upstox_daily_data(
    days_back: int = MAX_DAILY_HISTORY_DAYS,
    symbols: list[str] | None = None,
    persist_cache: bool = True,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Fetch fresh broker candles, optionally preserving them as the training cache."""
    if not get_market_data_token():
        raise ValueError(
            "No Upstox market-data token is configured; set UPSTOX_ANALYTICS_TOKEN "
            "or UPSTOX_ACCESS_TOKEN before training."
        )
    if not 1 <= days_back <= MAX_DAILY_HISTORY_DAYS:
        raise ValueError(f"days_back must be between 1 and {MAX_DAILY_HISTORY_DAYS} for Upstox daily candles.")

    requested_symbols = [symbol.upper() for symbol in (symbols or INSTRUMENT_KEYS)]
    unknown_symbols = set(requested_symbols) - set(INSTRUMENT_KEYS)
    if unknown_symbols:
        raise ValueError(f"Unknown Upstox symbols: {', '.join(sorted(unknown_symbols))}")

    requested_market_context = sorted(MARKET_CONTEXT_INSTRUMENT_KEYS)
    symbols_to_fetch = [*requested_symbols, *requested_market_context]
    semaphore = asyncio.Semaphore(2)
    now_ist = datetime.now(MARKET_TIMEZONE)

    async def fetch_symbol(symbol: str) -> tuple[str, list[dict[str, Any]], str | None]:
        try:
            async with semaphore:
                candles = await get_daily_history_v3(symbol, days_back=days_back)
            normalized = {}
            for candle in candles:
                timestamp = datetime.fromisoformat(str(candle["timestamp"]))
                if now_ist.time() < DAILY_CANDLE_CUTOFF and timestamp.astimezone(
                    MARKET_TIMEZONE
                ).date() >= now_ist.date():
                    continue
                normalized[timestamp.isoformat()] = candle
            ordered = [normalized[key] for key in sorted(normalized)]
            if len(ordered) < 22:
                return symbol, [], f"Only {len(ordered)} completed daily candles were returned."
            return symbol, ordered, None
        except Exception as exc:
            return symbol, [], f"{type(exc).__name__}: {exc}"

    results = await asyncio.gather(*(fetch_symbol(symbol) for symbol in symbols_to_fetch))
    historical_data = {
        symbol: candles for symbol, candles, error in results if candles and error is None
    }
    failures: dict[str, str] = {}
    market_context_failures: dict[str, str] = {}
    for result in results:
        symbol, error = result[0], result[2]
        if error is not None:
            if symbol in requested_market_context:
                market_context_failures[symbol] = error
            else:
                failures[symbol] = error
    fetched_symbols = sorted(set(requested_symbols) & set(historical_data))
    fetched_market_context = sorted(
        set(requested_market_context) & set(historical_data)
    )
    if not fetched_symbols:
        detail = "; ".join(f"{symbol}: {error}" for symbol, error in failures.items())
        raise RuntimeError(f"Upstox returned no usable daily history. {detail}")

    report = {
        "provider": "Upstox Official API v3",
        "requested_days": days_back,
        "requested_symbols": requested_symbols,
        "fetched_symbols": fetched_symbols,
        "failed_symbols": failures,
        "data_start_by_symbol": {
            symbol: historical_data[symbol][0]["timestamp"]
            for symbol in fetched_symbols
        },
        "data_end_by_symbol": {
            symbol: historical_data[symbol][-1]["timestamp"]
            for symbol in fetched_symbols
        },
        "requested_market_context": requested_market_context,
        "fetched_market_context": fetched_market_context,
        "failed_market_context": market_context_failures,
        "market_context_data_ranges": {
            symbol: {
                "start": historical_data[symbol][0]["timestamp"],
                "end": historical_data[symbol][-1]["timestamp"],
            }
            for symbol in fetched_market_context
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    if persist_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary_cache = CACHE_FILE.with_suffix(CACHE_FILE.suffix + ".tmp")
        temporary_cache.write_text(json.dumps(historical_data, indent=2))
        temporary_cache.replace(CACHE_FILE)
    if failures or market_context_failures:
        print(
            "Upstox history unavailable for "
            + ", ".join(sorted([*failures, *market_context_failures]))
            + "; no cached or alternate-provider data was used for those instruments."
        )
    return historical_data, report
