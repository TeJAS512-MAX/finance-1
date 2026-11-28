"""
backtesting/historical_fetcher.py — Downloads historical Upstox data for the backtester.
"""
from __future__ import annotations
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
load_dotenv()

from services.providers.upstox_market_data import INSTRUMENT_KEYS, _get_headers, UPSTOX_BASE

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "historical_candles_90d.json"

async def fetch_historical_data(days_back: int = 90) -> Dict[str, List[Dict[str, Any]]]:
    """
    Downloads up to 90 days of 30-minute candles in broker-supported windows.
    Saves to a local JSON cache so we don't hammer the API during backtesting.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # If cache exists and is fresh (from today), just load it
    if CACHE_FILE.exists():
        stat = CACHE_FILE.stat()
        file_age = datetime.now().timestamp() - stat.st_mtime
        if file_age < 3600 * 12:  # 12 hours
            print("📦 Loading historical data from local cache...")
            with open(CACHE_FILE, "r") as f:
                return json.load(f)

    print(f"📥 Fetching {days_back} days of historical data from Upstox...")
    all_data = {}
    
    now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata"))

    async with httpx.AsyncClient(timeout=15.0) as client:
        for symbol, instrument_key in INSTRUMENT_KEYS.items():
            print(f"  Fetching {symbol}...")
            try:
                candles_by_timestamp = {}
                window_end = now
                earliest = now - timedelta(days=days_back)
                while window_end > earliest:
                    window_start = max(earliest, window_end - timedelta(days=29))
                    url = (
                        f"{UPSTOX_BASE}/historical-candle/{instrument_key}/30minute/"
                        f"{window_end.strftime('%Y-%m-%d')}/{window_start.strftime('%Y-%m-%d')}"
                    )
                    response = await client.get(url, headers=_get_headers())
                    response.raise_for_status()
                    candles_raw = response.json().get("data", {}).get("candles", [])
                    for c in candles_raw:
                        candles_by_timestamp[c[0]] = {
                            "timestamp": c[0],
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": int(c[5]),
                        }
                    window_end = window_start - timedelta(days=1)
                    await asyncio.sleep(0.5)

                all_data[symbol] = [
                    candles_by_timestamp[key]
                    for key in sorted(candles_by_timestamp)
                ]
            except Exception as e:
                print(f"  ❌ Failed to fetch {symbol}: {e}")

    with open(CACHE_FILE, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"✅ Saved historical data to {CACHE_FILE.name}")
    
    return all_data

if __name__ == "__main__":
    asyncio.run(fetch_historical_data())
