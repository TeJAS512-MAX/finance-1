from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import joblib
import numpy as np

from backtesting.stock_direction_cross_sectional_shadow import (
    record_cross_sectional_shadow_predictions,
)
from core import config
from intelligence.stock_direction import (
    MARKET_CONTEXT_SYMBOL,
    _model_feature_columns,
)
from intelligence.stock_direction_cross_sectional import REGIME_FEATURES


class _FakeRankModel:
    def predict(self, features):
        return np.arange(len(features), dtype=float)


class _FakeReturnModel:
    def predict(self, features):
        return np.full(len(features), 0.25)


def _candles(count: int = 82) -> list[dict[str, float | str]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    previous_close = 100.0
    for index in range(count):
        open_price = previous_close * (1 + (0.001 if index % 2 else -0.001))
        close = open_price * (1.004 if index % 3 else 0.998)
        candles.append(
            {
                "timestamp": (start + timedelta(days=index)).isoformat(),
                "open": open_price,
                "high": max(open_price, close) * 1.01,
                "low": min(open_price, close) * 0.99,
                "close": close,
                "volume": 1000 + index,
            }
        )
        previous_close = close
    return candles


def test_cross_sectional_shadow_starts_after_training_and_resolves_forward_returns(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
            paper_trading_initial_capital=50_000.0,
            max_position_size_pct=10.0,
        ),
    )
    candles = _candles()
    model_path = tmp_path / "cross_sectional.joblib"
    log_path = tmp_path / "cross_sectional_shadow.json"
    trained_through = candles[75]["timestamp"]
    symbols = ["ALPHA", "BETA"]
    joblib.dump(
        {
            "rank_model": _FakeRankModel(),
            "return_model": _FakeReturnModel(),
            "metadata": {
                "schema_version": 1,
                "architecture": "regime_aware_cross_sectional_ranker",
                "eligible_for_live_display": False,
                "live_trading_enabled": False,
                "trained_symbols": symbols,
                "features": [
                    *_model_feature_columns(symbols, include_market_context=True),
                    *REGIME_FEATURES,
                ],
                "regime_volatility_threshold": 1.0,
                "execution_costs": {
                    "commission_pct_per_side": 0.03,
                    "slippage_pct_per_side": 0.05,
                },
                "artifact_training": {
                    "through": trained_through,
                    "generated_at": "cross-sectional-v1",
                },
            },
        },
        model_path,
    )
    before_forward = record_cross_sectional_shadow_predictions(
        {
            "ALPHA": candles[:76],
            "BETA": candles[:76],
            MARKET_CONTEXT_SYMBOL: candles[:76],
        },
        model_path=model_path,
        log_path=log_path,
    )
    first_forecast = record_cross_sectional_shadow_predictions(
        {
            "ALPHA": candles,
            "BETA": candles,
            MARKET_CONTEXT_SYMBOL: candles,
        },
        model_path=model_path,
        log_path=log_path,
    )
    resolved_forecast = record_cross_sectional_shadow_predictions(
        {
            "ALPHA": _candles(83),
            "BETA": _candles(83),
            MARKET_CONTEXT_SYMBOL: _candles(83),
        },
        model_path=model_path,
        log_path=log_path,
    )

    assert before_forward["new_predictions"] == 0
    assert first_forecast["new_predictions"] == 2
    assert first_forecast["evaluation_sessions_started"] == 1
    assert resolved_forecast["newly_resolved_predictions"] == 2
    assert resolved_forecast["trade_predictions"] == 1
    assert resolved_forecast["pending_predictions"] == 2
    assert log_path.is_file()
