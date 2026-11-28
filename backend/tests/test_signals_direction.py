from __future__ import annotations

from pathlib import Path

import pytest

from api.routes import signals
from intelligence import decision_engine, stock_direction
from services.providers import upstox_market_data


@pytest.mark.asyncio
async def test_live_signal_keeps_intraday_decision_and_adds_research_forecast(
    monkeypatch, tmp_path: Path
):
    async def compute_features(symbol: str, interval: str):
        return {"rsi": 55.0, "ltp": 100.0, "sma20": 99.0}

    async def get_candles(symbol: str, interval: str, days_back: int):
        return []

    monkeypatch.setattr(upstox_market_data, "compute_features", compute_features)
    monkeypatch.setattr(upstox_market_data, "get_candles", get_candles)
    monkeypatch.setattr(
        decision_engine,
        "analyze_setup",
        lambda features: {
            "candidate_direction": "LONG",
            "decision": "TRADE",
            "ml_probability": 0.7,
            "reason": "test decision",
            "technical_score": 0.8,
            "score_breakdown": {},
        },
    )
    model_path = tmp_path / "candidate.joblib"
    model_path.touch()
    monkeypatch.setattr(stock_direction, "MODEL_PATH", model_path)
    monkeypatch.setattr(stock_direction, "candidate_supports_symbol", lambda symbol: True)
    monkeypatch.setattr(
        stock_direction,
        "predict_next_session",
        lambda symbol, candles, market_candles=None: {
            "decision": "TRADE",
            "expected_net_return_pct": 0.12,
            "return_estimate_is_calibrated": False,
            "as_of": "2024-01-01T00:00:00+00:00",
            "trained_through": "2024-01-02T00:00:00+00:00",
            "model": "test",
            "mode": "research_only",
        },
    )

    result = await signals._analyze_symbol("RELIANCE")

    assert result is not None
    assert result["direction"] == "LONG"
    assert result["nextSessionPrediction"]["decision"] == "TRADE"
    assert result["nextSessionPrediction"]["expected_net_return_pct"] == 0.12
    assert result["nextSessionPrediction"]["mode"] == "research_only"
    assert result["nextSessionPredictionStatus"] == "available"


@pytest.mark.asyncio
async def test_model_status_failure_does_not_discard_live_signals(monkeypatch):
    async def analyze_symbol(symbol: str):
        return {"symbol": symbol, "confidence": 80}

    def fail_model_status():
        raise OSError("candidate artifact unavailable")

    monkeypatch.setattr(signals, "_analyze_symbol", analyze_symbol)
    monkeypatch.setattr(signals, "get_candidate_status", fail_model_status)

    response = await signals.list_signals()

    assert response["signals"] == [
        {"symbol": symbol, "confidence": 80} for symbol in signals.WATCHLIST
    ]
    assert response["direction_model"] == {"state": "unavailable"}
