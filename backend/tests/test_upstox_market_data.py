from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

from api.routes.token import token_status
from services.providers import upstox_market_data as mod


@pytest.mark.asyncio
async def test_token_status_keeps_analytics_and_trading_credentials_separate(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "a" * 60)
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)

    status = await token_status()

    assert status["analytics_token_set"] is True
    assert status["market_data_token_set"] is True
    assert status["token_set"] is False


def test_market_data_headers_prefer_analytics_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "analytics-token")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "daily-token")

    assert mod._get_headers()["Authorization"] == "Bearer analytics-token"


def test_market_data_headers_fall_back_to_daily_token(monkeypatch):
    monkeypatch.delenv("UPSTOX_ANALYTICS_TOKEN", raising=False)
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "daily-token")

    assert mod._get_headers()["Authorization"] == "Bearer daily-token"


@pytest.mark.asyncio
async def test_compute_features_uses_latest_candle(monkeypatch):
    """Regression test: compute_features must always use the latest candle index."""
    candles = []
    base = 100.0
    for i in range(25):
        candles.append(
            {
                "timestamp": f"2026-09-26T09:{i:02d}:00+00:00",
                "open": base + i,
                "high": base + i + 3,
                "low": base + i - 2,
                "close": base + i + 1,
                "volume": 1000 + i * 10,
            }
        )

    async def fake_get_candles(symbol: str, interval: str = "5m", days_back: int = 5):
        assert symbol == "RELIANCE"
        assert interval == "5m"
        assert days_back == 5
        return candles

    monkeypatch.setattr(mod, "get_candles", fake_get_candles)

    result = await mod.compute_features("RELIANCE", interval="5m")

    assert result["symbol"] == "RELIANCE"
    assert result["candle_count"] == 25
    assert result["timestamp"] == candles[-1]["timestamp"]
    assert "ltp" in result
    assert "rsi" in result


@pytest.mark.asyncio
async def test_daily_candle_requests_respect_upstox_one_year_limit(monkeypatch):
    requested_urls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"candles": []}}

    class Client:
        async def get(self, url, headers):
            assert headers == {}
            requested_urls.append(url)
            return Response()

    @asynccontextmanager
    async def client_factory(timeout):
        assert timeout == 10.0
        yield Client()

    monkeypatch.setattr(mod, "_get_headers", lambda: {})
    monkeypatch.setattr(mod.httpx, "AsyncClient", client_factory)

    await mod.get_candles("RELIANCE", interval="1D", days_back=3000)

    parts = requested_urls[0].split("/")
    to_date = datetime.strptime(parts[-2], "%Y-%m-%d").date()
    from_date = datetime.strptime(parts[-1], "%Y-%m-%d").date()
    assert to_date - from_date == timedelta(days=365)
