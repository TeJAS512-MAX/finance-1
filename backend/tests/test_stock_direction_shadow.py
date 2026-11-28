from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import joblib
import numpy as np

from backtesting.stock_direction_shadow import (
    SHADOW_EVALUATION_SESSION_LIMIT,
    _evaluation_progress,
    record_shadow_predictions,
)
from core import config
from intelligence.stock_direction import MODEL_SCHEMA_VERSION


class _FakeRegressor:
    def __init__(self, prediction: float = 0.25):
        self.prediction = prediction

    def predict(self, features):
        return np.full(len(features), self.prediction)


def test_shadow_evaluation_completes_only_after_90_resolved_sessions():
    candidate_id = "candidate:baseline"
    entries = [
        {
            "candidate_id": candidate_id,
            "as_of": (
                datetime(2026, 1, 1, tzinfo=timezone.utc)
                + timedelta(days=index)
            ).isoformat(),
            "actual_net_return_pct": None,
        }
        for index in range(SHADOW_EVALUATION_SESSION_LIMIT)
    ]

    pending_progress = _evaluation_progress(entries, candidate_id)
    assert pending_progress == {
        "sessions_started": 90,
        "sessions_resolved": 0,
        "complete": False,
    }

    for entry in entries:
        entry["actual_net_return_pct"] = 0.0
    resolved_progress = _evaluation_progress(entries, candidate_id)

    assert resolved_progress == {
        "sessions_started": 90,
        "sessions_resolved": 90,
        "complete": True,
    }


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


def test_shadow_log_waits_for_forward_data_then_resolves_prior_forecast(
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
    model_path = tmp_path / "shadow.joblib"
    log_path = tmp_path / "shadow_predictions.json"
    training_date = candles[75]["timestamp"]
    selected_model = _FakeRegressor()
    joblib.dump(
        {
            "model": selected_model,
            "shadow_models": {
                "test_regressor": selected_model,
                "challenger_regressor": _FakeRegressor(-0.25),
            },
            "metadata": {
                "schema_version": MODEL_SCHEMA_VERSION,
                "eligible_for_live_display": False,
                "model_type": "test_regressor",
                "trained_symbols": ["TEST"],
                "execution_costs": {
                    "commission_pct_per_side": 0.03,
                    "slippage_pct_per_side": 0.05,
                },
                "artifact_training": {
                    "through": training_date,
                    "generated_at": "test-candidate-v1",
                },
            },
        },
        model_path,
    )

    before_forward_data = record_shadow_predictions(
        {"TEST": candles[:76]}, model_path=model_path, log_path=log_path
    )
    first_forecast = record_shadow_predictions(
        {"TEST": candles[:-1]}, model_path=model_path, log_path=log_path
    )
    resolved_forecast = record_shadow_predictions(
        {"TEST": candles}, model_path=model_path, log_path=log_path
    )
    entries = json.loads(log_path.read_text(encoding="utf-8"))

    assert before_forward_data["new_predictions"] == 0
    assert first_forecast["new_predictions"] == 2
    assert first_forecast["resolved_predictions"] == 0
    assert resolved_forecast["newly_resolved_predictions"] == 2
    assert resolved_forecast["resolved_predictions"] == 1
    assert resolved_forecast["pending_predictions"] == 1
    assert {entry["model"] for entry in entries} == {
        "test_regressor",
        "challenger_regressor",
    }
    assert sum(entry["actual_net_return_pct"] is not None for entry in entries) == 2
    assert sum(entry["actual_net_return_pct"] is None for entry in entries) == 2
    assert resolved_forecast["challenger_metrics"]["test_regressor"]["paper_backtest"][
        "trades"
    ] == 1
    assert resolved_forecast["challenger_metrics"]["challenger_regressor"][
        "paper_backtest"
    ]["trades"] == 0
    assert resolved_forecast["paper_backtest"]["trades"] == 1
