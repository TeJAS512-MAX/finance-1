"""Historical-only Yahoo Finance cache for multi-year model research."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from services.providers.upstox_market_data import INSTRUMENT_KEYS

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "historical_candles_yahoo_daily.json"


def fetch_yahoo_daily_data(
    years_back: int = 10,
    symbols: List[str] | None = None,
    *,
    fresh_only: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """Refresh split/dividend-adjusted daily NSE history for research and backtesting."""
    if years_back < 1:
        raise ValueError("years_back must be at least one")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=365 * years_back)
    requested_symbols = [symbol.upper() for symbol in (symbols or INSTRUMENT_KEYS)]
    unknown_symbols = set(requested_symbols) - set(INSTRUMENT_KEYS)
    if unknown_symbols:
        raise ValueError(f"Unknown Yahoo symbols: {', '.join(sorted(unknown_symbols))}")

    existing_data: Dict[str, List[Dict[str, Any]]] = {}
    if CACHE_FILE.is_file():
        existing_data = json.loads(CACHE_FILE.read_text())
    fresh_data: Dict[str, List[Dict[str, Any]]] = {}

    for symbol in requested_symbols:
        ticker = f"{symbol}.NS"
        print(f"  Fetching Yahoo daily history for {symbol}...")
        try:
            frame = yf.download(
                ticker,
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception as exc:
            print(f"  Yahoo refresh failed for {symbol}: {exc}")
            continue
        if frame.empty:
            print(f"  No fresh Yahoo history returned for {symbol}; retaining any cache only.")
            continue

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        if isinstance(frame.index, pd.DatetimeIndex) and frame.index.name is None:
            frame.index.name = "date"
        frame = frame.reset_index()
        frame = frame.rename(columns={str(column): str(column).lower() for column in frame.columns})
        date_column = next(
            (column for column in ("date", "datetime") if column in frame.columns), None
        )
        if date_column is None or not {"open", "high", "low", "close", "volume"}.issubset(frame.columns):
            print(f"  Yahoo returned an unsupported candle schema for {symbol}; skipping it.")
            continue
        candles = []
        for _, row in frame.iterrows():
            timestamp = pd.Timestamp(row[date_column])
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
            candle = {
                "timestamp": timestamp.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
            if (
                all(pd.notna(candle[key]) and candle[key] > 0 for key in ("open", "high", "low", "close"))
                and candle["high"] >= max(candle["open"], candle["low"], candle["close"])
                and candle["low"] <= min(candle["open"], candle["high"], candle["close"])
                and candle["volume"] >= 0
            ):
                candles.append(candle)
        if candles:
            fresh_data[symbol] = candles
        else:
            print(f"  Yahoo returned no valid OHLCV rows for {symbol}; skipping it.")

    if not fresh_data:
        raise RuntimeError("Yahoo returned no fresh valid daily candles; no cache was overwritten.")

    merged_data = {**existing_data, **fresh_data}
    temporary_cache = CACHE_FILE.with_suffix(CACHE_FILE.suffix + ".tmp")
    temporary_cache.write_text(json.dumps(merged_data, indent=2))
    temporary_cache.replace(CACHE_FILE)
    failed_symbols = sorted(set(requested_symbols) - set(fresh_data))
    if failed_symbols:
        print(
            "  No fresh data for: "
            + ", ".join(failed_symbols)
            + "; these cached rows were not used for this training run."
        )
    print(
        f"Refreshed {len(fresh_data)}/{len(requested_symbols)} symbols in "
        f"{CACHE_FILE.name} using Yahoo split/dividend-adjusted OHLC."
    )
    return fresh_data if fresh_only else merged_data


if __name__ == "__main__":
    data = fetch_yahoo_daily_data(
        years_back=int(os.environ.get("STOCK_DIRECTION_YEARS_BACK", "10"))
    )
    print(f"symbols={len(data)} rows={sum(len(rows) for rows in data.values())}")
