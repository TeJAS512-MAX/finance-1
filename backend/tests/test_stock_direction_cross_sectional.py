from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd

from core import config
from intelligence.stock_direction_cross_sectional import (
    _top_one_signals,
    _volatility_threshold,
    train_cross_sectional_candidate,
)


def _candles(count: int, offset: float = 0.0) -> list[dict[str, float | str]]:
    start = datetime(2021, 1, 4, tzinfo=timezone.utc)
    candles = []
    previous_close = 100.0 + offset
    for index in range(count):
        open_price = previous_close * (1 + 0.0005 * np.cos(index / 7 + offset))
        daily_return = (
            0.0015 * np.sin(index / 5 + offset)
            + 0.0008 * np.cos(index / 13)
            + offset * 0.00001
        )
        close = open_price * (1 + daily_return)
        candles.append(
            {
                "timestamp": (start + timedelta(days=index)).isoformat(),
                "open": open_price,
                "high": max(open_price, close) * 1.01,
                "low": min(open_price, close) * 0.99,
                "close": close,
                "volume": 1000 + (index % 31) * 17 + int(offset),
            }
        )
        previous_close = close
    return candles


def test_volatility_regime_threshold_uses_training_session_quantile():
    training = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, tz="UTC"),
            "nifty_realized_volatility_20": [0.1, 0.2, 0.3, 0.4],
        }
    )

    assert _volatility_threshold(training) == 0.325


def test_top_one_signals_take_only_positive_top_rank_per_session():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
                utc=True,
            ),
        }
    )

    signals = _top_one_signals(
        frame,
        rank_predictions=np.array([0.2, 0.8, 0.7, 0.1]),
        return_predictions=np.array([0.4, -0.1, 0.3, 0.2]),
    )

    assert np.array_equal(signals, np.array([0.0, 0.0, 0.3, 0.0]))


def test_cross_sectional_candidate_is_separate_and_never_promoted(
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
    historical_data = {
        "ALPHA": _candles(260, 1.0),
        "BETA": _candles(260, 2.0),
        "GAMMA": _candles(260, 3.0),
        "NIFTY50": _candles(260, 0.0),
    }
    model_path = tmp_path / "separate_cross_sectional_candidate.joblib"
    report_path = tmp_path / "separate_cross_sectional_report.json"

    report = train_cross_sectional_candidate(
        historical_data,
        data_source="synthetic_test",
        model_path=model_path,
        report_path=report_path,
        test_sessions=90,
    )
    bundle = joblib.load(model_path)

    assert report["architecture"] == "regime_aware_cross_sectional_ranker"
    assert report["schema_version"] == 1
    assert report["base_feature_schema_version"] == 10
    assert pd.Timestamp(report["artifact_training"]["through"]) == pd.Timestamp(
        report["date_ranges"]["test"]["end"]
    ) + pd.Timedelta(days=1)
    assert report["eligible_for_live_display"] is False
    assert report["historical_test_is_descriptive_only"] is True
    assert report["risk_limits"]["paper_profit_target"] == 500.0
    assert report["risk_limits"]["paper_max_drawdown"] == 1_000.0
    assert report["validation"]["ranking"]["sessions_ranked"] > 0
    assert report["historical_test"]["sessions"] == 90
    assert set(bundle) == {"rank_model", "return_model", "metadata"}
    assert bundle["metadata"]["eligible_for_live_display"] is False
    assert model_path.is_file()
    assert report_path.is_file()
