from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from backtesting import upstox_stock_history as history
from services.providers import upstox_market_data


def _candles(count: int = 30) -> list[dict[str, float | str]]:
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    return [
        {
            "timestamp": (start + timedelta(days=index)).isoformat(),
            "open": 100.0 + index,
            "high": 102.0 + index,
            "low": 99.0 + index,
            "close": 101.0 + index,
            "volume": 1000 + index,
        }
        for index in range(count)
    ]


@pytest.mark.asyncio
async def test_training_history_uses_fresh_upstox_candles_only(monkeypatch, tmp_path):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")
    cache_file = tmp_path / "historical_candles_upstox_daily.json"
    monkeypatch.setattr(history, "CACHE_FILE", cache_file)
    monkeypatch.setattr(history, "INSTRUMENT_KEYS", {"TEST": "NSE_EQ|TEST"})
    monkeypatch.setattr(history, "MARKET_CONTEXT_INSTRUMENT_KEYS", {})

    async def get_daily_history_v3(symbol: str, days_back: int):
        assert symbol == "TEST"
        assert days_back == 3650
        return _candles()

    monkeypatch.setattr(history, "get_daily_history_v3", get_daily_history_v3)

    candles, report = await history.fetch_upstox_daily_data(symbols=["TEST"])

    assert candles["TEST"] == _candles()
    assert report["provider"] == "Upstox Official API v3"
    assert report["fetched_symbols"] == ["TEST"]
    assert json.loads(cache_file.read_text()) == candles


@pytest.mark.asyncio
async def test_training_history_fetches_market_context_separately(monkeypatch, tmp_path):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")
    cache_file = tmp_path / "historical_candles_upstox_daily.json"
    monkeypatch.setattr(history, "CACHE_FILE", cache_file)
    monkeypatch.setattr(history, "INSTRUMENT_KEYS", {"TEST": "NSE_EQ|TEST"})
    monkeypatch.setattr(
        history,
        "MARKET_CONTEXT_INSTRUMENT_KEYS",
        {"NIFTY50": "NSE_INDEX|Nifty 50"},
    )

    async def get_daily_history_v3(symbol: str, days_back: int):
        assert symbol in {"TEST", "NIFTY50"}
        return _candles()

    monkeypatch.setattr(history, "get_daily_history_v3", get_daily_history_v3)

    candles, report = await history.fetch_upstox_daily_data(symbols=["TEST"])

    assert set(candles) == {"TEST", "NIFTY50"}
    assert report["fetched_symbols"] == ["TEST"]
    assert report["fetched_market_context"] == ["NIFTY50"]
    assert report["market_context_data_ranges"]["NIFTY50"]["start"]


@pytest.mark.asyncio
async def test_shadow_history_does_not_replace_long_training_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")
    cache_file = tmp_path / "historical_candles_upstox_daily.json"
    cached_training_history = {"TRAINING": _candles()}
    cache_file.write_text(json.dumps(cached_training_history))
    monkeypatch.setattr(history, "CACHE_FILE", cache_file)
    monkeypatch.setattr(history, "INSTRUMENT_KEYS", {"TEST": "NSE_EQ|TEST"})
    monkeypatch.setattr(history, "MARKET_CONTEXT_INSTRUMENT_KEYS", {})

    async def get_daily_history_v3(symbol: str, days_back: int):
        assert symbol == "TEST"
        assert days_back == 45
        return _candles()

    monkeypatch.setattr(history, "get_daily_history_v3", get_daily_history_v3)

    await history.fetch_upstox_daily_data(
        days_back=45,
        symbols=["TEST"],
        persist_cache=False,
    )

    assert json.loads(cache_file.read_text()) == cached_training_history


@pytest.mark.asyncio
async def test_training_fails_without_upstox_token(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("UPSTOX_ANALYTICS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="No Upstox market-data token is configured"):
        await history.fetch_upstox_daily_data(symbols=["TEST"])


@pytest.mark.asyncio
async def test_training_rejects_history_beyond_upstox_v3_daily_limit(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")

    with pytest.raises(ValueError, match="between 1 and 3650"):
        await history.fetch_upstox_daily_data(days_back=3651, symbols=["RELIANCE"])


@pytest.mark.asyncio
async def test_upstox_v3_daily_fetch_encodes_key_and_sorts_candles(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")
    monkeypatch.setattr(
        upstox_market_data,
        "INSTRUMENT_KEYS",
        {"TEST": "NSE_EQ|TEST"},
    )
    requests = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "candles": [
                        ["2026-10-02T00:00:00+05:30", 2, 3, 1, 2.5, 200, 0],
                        ["2026-10-01T00:00:00+05:30", 1, 2, 0.5, 1.5, 100, 0],
                    ]
                }
            }

    class Client:
        def __init__(self, timeout):
            assert timeout == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url, headers):
            requests.append((url, headers))
            return Response()

    monkeypatch.setattr(
        upstox_market_data.httpx,
        "AsyncClient",
        Client,
    )

    candles = await upstox_market_data.get_daily_history_v3("TEST", days_back=3650)
    market_candles = await upstox_market_data.get_daily_history_v3(
        "NIFTY50", days_back=3650
    )

    assert len(requests) == 2
    assert "/historical-candle/NSE_EQ%7CTEST/days/1/" in requests[0][0]
    assert "/historical-candle/NSE_INDEX%7CNifty%2050/days/1/" in requests[1][0]
    assert requests[0][1]["Authorization"] == "Bearer test-analytics-token"
    assert [candle["timestamp"] for candle in candles] == [
        "2026-10-01T00:00:00+05:30",
        "2026-10-02T00:00:00+05:30",
    ]
    assert candles[0]["volume"] == 100
    assert len(market_candles) == 2


@pytest.mark.asyncio
async def test_partial_upstox_failures_do_not_reuse_old_symbol_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "test-analytics-token")
    cache_file = tmp_path / "historical_candles_upstox_daily.json"
    cache_file.write_text(json.dumps({"FAILED": _candles()}))
    monkeypatch.setattr(history, "CACHE_FILE", cache_file)
    monkeypatch.setattr(history, "MARKET_CONTEXT_INSTRUMENT_KEYS", {})
    monkeypatch.setattr(
        history,
        "INSTRUMENT_KEYS",
        {"GOOD": "NSE_EQ|GOOD", "FAILED": "NSE_EQ|FAILED"},
    )

    async def get_daily_history_v3(symbol: str, days_back: int):
        if symbol == "FAILED":
            raise RuntimeError("Upstox temporarily unavailable")
        assert days_back == 3650
        return _candles()

    monkeypatch.setattr(history, "get_daily_history_v3", get_daily_history_v3)

    candles, report = await history.fetch_upstox_daily_data(
        symbols=["GOOD", "FAILED"]
    )

    assert set(candles) == {"GOOD"}
    assert "FAILED" not in json.loads(cache_file.read_text())
    assert "FAILED" in report["failed_symbols"]
