"""
services/providers/upstox_market_data.py — Upstox Official Market Data Provider.

Uses the official Upstox Developer API v2 to fetch:
  - Real-time OHLC candle data (no delays, direct from NSE)
  - Live quotes via the Market Quote API
  - Historical candles for technical analysis

This is the recommended provider for live NSE market data.
Prefers UPSTOX_ANALYTICS_TOKEN, with UPSTOX_ACCESS_TOKEN as a fallback.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

import httpx

# ── Upstox API v2 base URL ──────────────────────────────────────────────────
UPSTOX_BASE = "https://api.upstox.com/v2"
UPSTOX_V3_BASE = "https://api.upstox.com/v3"

# Official NSE_EQ instrument keys from Upstox's NSE instrument master (verified 200 OK).
INSTRUMENT_KEYS: Dict[str, str] = {
    "RELIANCE":   "NSE_EQ|INE002A01018",
    "SBIN":       "NSE_EQ|INE062A01020",
    "TCS":        "NSE_EQ|INE467B01029",
    "INFY":       "NSE_EQ|INE009A01021",
    "ZOMATO":     "NSE_EQ|INE758T01015",
    "ITC":        "NSE_EQ|INE154A01025",
    "ICICIBANK":  "NSE_EQ|INE090A01021",
    "WIPRO":      "NSE_EQ|INE075A01022",
    "HDFCBANK":   "NSE_EQ|INE040A01034",
    "BAJFINANCE": "NSE_EQ|INE296A01032",
    "LT":         "NSE_EQ|INE018A01030",
    "AXISBANK":   "NSE_EQ|INE238A01034",
    "KOTAKBANK":  "NSE_EQ|INE237A01036",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "SUNPHARMA":  "NSE_EQ|INE044A01036",
    "MARUTI":     "NSE_EQ|INE585B01010",
    "M&M":        "NSE_EQ|INE101A01026",
    "NTPC":       "NSE_EQ|INE733E01010",
    "POWERGRID":  "NSE_EQ|INE752E01010",
    "HCLTECH":    "NSE_EQ|INE860A01027",
    "TECHM":      "NSE_EQ|INE669C01036",
    "TITAN":      "NSE_EQ|INE280A01028",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "TATASTEEL":  "NSE_EQ|INE081A01020",
    "JSWSTEEL":   "NSE_EQ|INE019A01038",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "DRREDDY":    "NSE_EQ|INE089A01031",
    "CIPLA":      "NSE_EQ|INE059A01026",
    "COALINDIA":  "NSE_EQ|INE522F01014",
    "ONGC":       "NSE_EQ|INE213A01029",
    "GRASIM":     "NSE_EQ|INE047A01021",
    "NESTLEIND":  "NSE_EQ|INE239A01024",
    "BAJAJFINSV": "NSE_EQ|INE918I01026",
    "TRENT":      "NSE_EQ|INE849A01020",
    "BEL":        "NSE_EQ|INE263A01024",
    # ── Next-50 expansion (verified from Upstox NSE.json.gz 2026-11) ─────────
    "ETERNAL":    "NSE_EQ|INE758T01015",   # Renamed from ZOMATO on NSE; same ISIN
    "HAL":        "NSE_EQ|INE066F01020",
    "SIEMENS":    "NSE_EQ|INE003A01024",
    "ABB":        "NSE_EQ|INE117A01022",
    "BHEL":       "NSE_EQ|INE257A01026",
    "EICHERMOT":  "NSE_EQ|INE066A01021",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "TVSMOTOR":   "NSE_EQ|INE494B01023",
    "DIVISLAB":   "NSE_EQ|INE361B01024",
    "APOLLOHOSP": "NSE_EQ|INE437A01024",
    "TORNTPHARM": "NSE_EQ|INE685A01028",
    "LUPIN":      "NSE_EQ|INE326A01037",
    "PERSISTENT": "NSE_EQ|INE262H01021",
    "COFORGE":    "NSE_EQ|INE591G01025",
    "BRITANNIA":  "NSE_EQ|INE216A01030",
    "GODREJCP":   "NSE_EQ|INE102D01028",
    "DABUR":      "NSE_EQ|INE016A01026",
    "VBL":        "NSE_EQ|INE200M01039",
    "COLPAL":     "NSE_EQ|INE259A01022",
    "CHOLAFIN":   "NSE_EQ|INE121A01024",
    "SHRIRAMFIN": "NSE_EQ|INE721A01047",
    "BANKBARODA": "NSE_EQ|INE028A01039",
    "PNB":        "NSE_EQ|INE160A01022",
    "INDIGO":     "NSE_EQ|INE646L01027",
    "DLF":        "NSE_EQ|INE271C01023",
    "PIDILITIND": "NSE_EQ|INE318A01026",
    "HAVELLS":    "NSE_EQ|INE176B01034",
    "TATAPOWER":  "NSE_EQ|INE245A01021",
    "GAIL":       "NSE_EQ|INE129A01019",
}
MARKET_CONTEXT_INSTRUMENT_KEYS: Dict[str, str] = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
}

# Upstox candle interval mapping
INTERVAL_MAP = {
    "1m":  "1minute",
    "5m":  "5minute",
    "15m": "15minute",
    "30m": "30minute",
    "1h":  "60minute",
    "1D":  "day",
    "1W":  "week",
    "1M":  "month",
}


def get_market_data_token() -> str:
    return (
        os.environ.get("UPSTOX_ANALYTICS_TOKEN", "").strip()
        or os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
    )


def _get_headers() -> Dict[str, str]:
    token = get_market_data_token()
    if not token:
        raise ValueError(
            "No Upstox market-data token is configured. Set UPSTOX_ANALYTICS_TOKEN "
            "or UPSTOX_ACCESS_TOKEN."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def get_candles(
    symbol: str,
    interval: str = "5m",
    days_back: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV candles from Upstox for a given symbol.
    Returns a list of dicts with keys: timestamp, open, high, low, close, volume
    """
    instrument_key = INSTRUMENT_KEYS.get(symbol.upper())
    if not instrument_key:
        raise ValueError(f"Unknown symbol: {symbol}. Add it to INSTRUMENT_KEYS.")

    upstox_interval = INTERVAL_MAP.get(interval, "5minute")

    # Upstox intraday candle endpoint is date-based and expects a valid range.
    # Use the market timezone (Asia/Kolkata) to avoid off-by-one day issues.
    now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata"))
    to_date = now.strftime("%Y-%m-%d")

    days_back = max(1, int(days_back))
    if upstox_interval in {"1minute", "5minute", "15minute", "30minute", "60minute"}:
        days_back = min(days_back, 30)
    elif upstox_interval == "day":
        days_back = min(days_back, 365)

    from_date = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Guard against invalid ranges from timezone/day-boundary drift.
    if from_date > to_date:
        from_date = (datetime.strptime(to_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    url = f"{UPSTOX_BASE}/historical-candle/{instrument_key}/{upstox_interval}/{to_date}/{from_date}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=_get_headers())
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                # Upstox uses 400 for unavailable/unsupported candle windows.
                # Treat it as an empty result so one symbol cannot abort a scan.
                return []
            raise
        data = response.json()

    candles_raw = data.get("data", {}).get("candles", [])
    # Upstox format: [timestamp, open, high, low, close, volume, oi]
    candles = []
    for c in candles_raw:
        candles.append({
            "timestamp": c[0],
            "open":      float(c[1]),
            "high":      float(c[2]),
            "low":       float(c[3]),
            "close":     float(c[4]),
            "volume":    int(c[5]),
        })

    # Return in chronological order (oldest first)
    return list(reversed(candles))


async def get_daily_history_v3(
    symbol: str,
    days_back: int = 3650,
) -> List[Dict[str, Any]]:
    """Fetch daily history from Upstox V3, which supports up to a decade."""
    normalized_symbol = symbol.upper()
    instrument_key = (
        INSTRUMENT_KEYS.get(normalized_symbol)
        or MARKET_CONTEXT_INSTRUMENT_KEYS.get(normalized_symbol)
    )
    if not instrument_key:
        raise ValueError(f"Unknown symbol: {symbol}. Add it to INSTRUMENT_KEYS.")
    if not 1 <= days_back <= 3650:
        raise ValueError("days_back must be between 1 and 3650 for Upstox V3 daily candles.")

    now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata"))
    to_date = now.strftime("%Y-%m-%d")
    from_date = (now.date() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    encoded_key = quote(instrument_key, safe="")
    url = (
        f"{UPSTOX_V3_BASE}/historical-candle/{encoded_key}/days/1/"
        f"{to_date}/{from_date}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=_get_headers())
        response.raise_for_status()
        data = response.json()

    candles = [
        {
            "timestamp": candle[0],
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": int(candle[5]),
        }
        for candle in data.get("data", {}).get("candles", [])
    ]
    return sorted(candles, key=lambda candle: candle["timestamp"])


def _is_jwt_expired(token: str) -> bool:
    """Return True only when token is a JWT with an expired `exp` timestamp."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        return False
    try:
        import base64
        import json

        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8"))
        exp = payload.get("exp")
        if exp is None:
            return False
        return datetime.now(timezone.utc).timestamp() >= float(exp)
    except Exception:
        return False


async def get_live_quote(symbol: str) -> Dict[str, Any]:
    """
    Fetch the latest live market quote for a symbol via Upstox Market Quote API.
    Returns LTP, OHLC, volume, circuit limits.
    """
    instrument_key = INSTRUMENT_KEYS.get(symbol.upper())
    if not instrument_key:
        raise ValueError(f"Unknown symbol: {symbol}")

    url = f"{UPSTOX_BASE}/market-quote/quotes"
    params = {"instrument_key": instrument_key}
    live_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
    if live_token and not _is_jwt_expired(live_token):
        headers = {
            "Authorization": f"Bearer {live_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    else:
        headers = _get_headers()

    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 401 and os.environ.get("UPSTOX_ANALYTICS_TOKEN", "").strip():
            fallback_headers = _get_headers()
            if fallback_headers.get("Authorization") != headers.get("Authorization"):
                response = await client.get(url, headers=fallback_headers, params=params)
        response.raise_for_status()
        data = response.json()

    data_map = data.get("data", {}) or {}
    quote_data = (
        data_map.get(instrument_key)
        or data_map.get(f"NSE_EQ:{symbol.upper()}")
        or (next((v for v in data_map.values() if isinstance(v, dict)), {}))
    )
    ohlc = quote_data.get("ohlc", {}) or {}
    ltp_val = quote_data.get("last_price")
    if not ltp_val:
        ltp_val = ohlc.get("close", 0.0)

    return {
        "symbol":         symbol,
        "instrument_key": instrument_key,
        "ltp":            float(ltp_val or 0.0),
        "open":           ohlc.get("open", 0.0),
        "high":           ohlc.get("high", 0.0),
        "low":            ohlc.get("low", 0.0),
        "close":          ohlc.get("close", 0.0),
        "volume":         quote_data.get("volume", 0),
        "avg_price":      quote_data.get("average_price", 0.0),
        "upper_circuit":  quote_data.get("upper_circuit_limit", 0.0),
        "lower_circuit":  quote_data.get("lower_circuit_limit", 0.0),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "source":         "Upstox Official API (Real-time NSE)",
    }


def compute_frac_diff(close: Any, d: float = 0.5, window: int = 10) -> Any:
    """Compute fixed-width-window fractionally differentiated closing prices."""
    import numpy as np

    weights = [1.0]
    for k in range(1, window):
        weights.append(-weights[-1] / k * (d - k + 1))
    w_ffd = np.array(weights[::-1], dtype=float)
    return close.rolling(window).apply(lambda x: float(np.dot(x, w_ffd)), raw=True)


async def compute_features(symbol: str, interval: str = "5m") -> Dict[str, Any]:
    """
    Fetch live candles from Upstox and compute a full feature set for the AI.
    Features: RSI (14), SMA (20), EMA (9/21), ATR (14), Volume Ratio, Momentum, VWAP.
    """
    import pandas as pd
    import numpy as np

    candles = await get_candles(symbol, interval=interval, days_back=5)
    if not candles:
        raise ValueError(f"No candle data returned for {symbol}. Market may be closed or token expired.")
    if len(candles) < 20:
        raise ValueError(f"Not enough candle data for {symbol} ({len(candles)} candles)")

    df = pd.DataFrame(candles)
    idx = len(df) - 1
    
    # Basic series
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # 1. RSI (14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))

    # 2. Moving Averages
    sma20 = close.rolling(20).mean()
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    # 3. True Range and ATR (14)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()

    # 4. Volume Ratio (current volume / 20-period avg volume)
    avg_vol_20 = volume.rolling(20).mean()
    vol_ratio = volume / avg_vol_20

    # 5. Momentum (10-bar price rate of change)
    momentum_10 = (close - close.shift(10)) / close.shift(10) * 100
    volatility = atr14 / close * 100
    trend_strength = (ema9 - ema21) / close * 100
    range_pct = (high - low) / close * 100
    return_5 = close.pct_change(5) * 100
    return_20 = close.pct_change(20) * 100
    frac_diff = compute_frac_diff(close, d=0.5, window=10)

    # 6. VWAP (Intraday)
    # Convert timestamps to datetime to group by day
    df['dt'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['dt'].dt.date
    df['typical_price'] = (high + low + close) / 3
    df['vp'] = df['typical_price'] * volume
    
    # Cumulative sum grouped by day for VWAP (guard zero volume)
    df['cum_vp'] = df.groupby('date')['vp'].cumsum()
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['vwap'] = np.where(df['cum_vol'] > 0, df['cum_vp'] / df['cum_vol'], close)

    # Scale-invariant derived features matching MLQualityFilter
    rsi_val = float(rsi_series.iloc[idx]) if pd.notna(rsi_series.iloc[idx]) else 50.0
    prev_rsi_val = float(rsi_series.iloc[idx - 1]) if idx > 0 and pd.notna(rsi_series.iloc[idx - 1]) else rsi_val
    ltp_val = float(close.iloc[idx])
    ema9_val = float(ema9.iloc[idx])
    ema21_val = float(ema21.iloc[idx])
    vwap_val = float(df['vwap'].iloc[idx])
    frac_val = float(frac_diff.iloc[idx]) if pd.notna(frac_diff.iloc[idx]) else 0.0
    high_val = float(high.iloc[idx])
    low_val = float(low.iloc[idx])
    open_val = float(df['open'].iloc[idx])
    span_val = high_val - low_val
    dt_ist = pd.to_datetime(df['timestamp'].iloc[idx], utc=True, errors='coerce')
    if pd.notna(dt_ist):
        dt_ist = dt_ist.tz_convert("Asia/Kolkata")
        hour_ist_val = float(dt_ist.hour + dt_ist.minute / 60.0)
    else:
        hour_ist_val = 12.0
    atr_causal = atr14.expanding(min_periods=14).mean().bfill().fillna(0.0).to_numpy() * 2.0
    diffs = close.diff().fillna(0.0).to_numpy()
    pos_s, neg_s, cusum_last = 0.0, 0.0, 0.0
    for i in range(len(diffs)):
        cusum_last = 0.0
        pos_s = max(0.0, pos_s + diffs[i])
        neg_s = min(0.0, neg_s + diffs[i])
        thr = float(atr_causal[i]) if atr_causal[i] > 0 else float('inf')
        if pos_s > thr:
            pos_s = 0.0
            cusum_last = 1.0
        elif neg_s < -thr:
            neg_s = 0.0
            cusum_last = -1.0
    ret1_val = float(close.pct_change(1).iloc[idx] * 100.0) if pd.notna(close.pct_change(1).iloc[idx]) else 0.0

    # 7. Consecutive Candles Analysis
    is_green = df['close'] > df['open']
    is_red = df['close'] < df['open']
    
    # Check if the last 2 and last 3 confirmed candles are all green or all red
    # idx = -2 is the latest confirmed candle, idx = -3 is the one before, idx = -4 before that
    latest_3_green = is_green.iloc[-3] and is_green.iloc[-2] and is_green.iloc[-1]
    latest_3_red = is_red.iloc[-3] and is_red.iloc[-2] and is_red.iloc[-1]

    latest_2_green = is_green.iloc[-2] and is_green.iloc[-1]
    latest_2_red = is_red.iloc[-2] and is_red.iloc[-1]

    # last_valid_idx should be the newest confirmed candle; this is the index used for the output payload.
    idx = len(df) - 1

    return {
        "symbol":       symbol,
        "ltp":          float(close.iloc[idx]),
        # Canonical OHLC names consumed by the opportunity scorer.  Retain
        # candle_* aliases for callers that use the explicit names.
        "open":         float(df['open'].iloc[idx]),
        "close":        float(close.iloc[idx]),
        "candle_open":  float(df['open'].iloc[idx]),
        "candle_close": float(close.iloc[idx]),
        "latest_3_green": bool(latest_3_green),
        "latest_3_red":   bool(latest_3_red),
        "latest_2_green": bool(latest_2_green),
        "latest_2_red":   bool(latest_2_red),
        "rsi":          rsi_val,
        "prev_rsi":     prev_rsi_val,
        "rsi_delta":    rsi_val - prev_rsi_val,
        "sma20":        float(sma20.iloc[idx]),
        "ema9":         ema9_val,
        "ema21":        ema21_val,
        "ema9_dist_pct":  ((ltp_val - ema9_val) / ltp_val * 100.0) if ltp_val > 0 else 0.0,
        "ema21_dist_pct": ((ltp_val - ema21_val) / ltp_val * 100.0) if ltp_val > 0 else 0.0,
        "atr14":        float(atr14.iloc[idx]),
        "vol_ratio":    float(vol_ratio.iloc[idx]),
        "momentum":     float(momentum_10.iloc[idx]),
        "volatility":   float(volatility.iloc[idx]),
        "trend_strength": float(trend_strength.iloc[idx]),
        "range_pct":    float(range_pct.iloc[idx]),
        "return_1":     ret1_val,
        "return_5":     float(return_5.iloc[idx]),
        "return_20":    float(return_20.iloc[idx]),
        "frac_diff":    frac_val,
        "frac_diff_pct": (frac_val / ltp_val * 100.0) if ltp_val > 0 else 0.0,
        "vwap":         vwap_val,
        "vwap_dist_pct": ((ltp_val - vwap_val) / vwap_val * 100.0) if vwap_val > 0 else 0.0,
        "body_pct":     ((ltp_val - open_val) / span_val) if span_val > 0 else 0.0,
        "cusum_event":  cusum_last,
        "hour_ist":     hour_ist_val,
        "timestamp":    str(df['timestamp'].iloc[idx]),  # PIT compliance key
        "candle_count": len(candles),
        "source":       "Upstox Official API (Real-time NSE)",
        "interval":     interval,
    }
