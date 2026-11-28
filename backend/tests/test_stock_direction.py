from __future__ import annotations

from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import pytest

from intelligence.stock_direction import (
    FEATURE_COLUMNS,
    MODEL_SCHEMA_VERSION,
    build_direction_dataset,
    chronological_split,
    get_candidate_status,
    predict_next_session,
    _simulate_long_only_paper_backtest,
)
from intelligence import stock_direction


def _candles(count: int = 80) -> list[dict[str, float | str]]:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    candles = []
    close = 100.0
    for index in range(count):
        close *= 1.003 if index % 3 else 0.998
        candles.append(
            {
                "timestamp": (start + timedelta(days=index)).isoformat(),
                "open": close * 0.999,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1000 + index,
            }
        )
    return candles


def test_dataset_uses_only_next_candle_for_target_and_drops_unusable_rows():
    candles = _candles()
    candles[40]["close"] = 0
    candles.append(candles[39].copy())

    dataset = build_direction_dataset(
        {"TEST": candles}, commission_pct=0.03, slippage_pct=0.05
    )

    assert set(FEATURE_COLUMNS).issubset(dataset.columns)
    assert dataset["timestamp"].is_monotonic_increasing
    assert dataset["symbol"].unique().tolist() == ["TEST"]
    assert (dataset["target_date"] > dataset["timestamp"]).all()
    assert dataset["target_net_return_pct"].notna().all()
    assert not dataset[FEATURE_COLUMNS].isin([float("inf"), float("-inf")]).any().any()


def test_daily_candles_with_different_times_share_one_market_session():
    candles = [
        {
            "timestamp": "2026-01-02T09:15:00+05:30",
            "open": 101.0,
            "high": 103.0,
            "low": 100.0,
            "close": 102.0,
            "volume": 2000,
        },
        {
            "timestamp": "2026-01-02T00:00:00+05:30",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000,
        },
        {
            "timestamp": "2026-01-05T00:00:00+05:30",
            "open": 102.0,
            "high": 104.0,
            "low": 101.0,
            "close": 103.0,
            "volume": 3000,
        },
    ]

    frame = stock_direction._validated_candles(candles)

    assert len(frame) == 2
    assert frame["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date.tolist() == [
        datetime(2026, 1, 2).date(),
        datetime(2026, 1, 5).date(),
    ]
    assert frame.iloc[0]["close"] == 102.0


def test_dataset_joins_nifty_context_without_training_it_as_a_stock():
    dataset = build_direction_dataset(
        {"TEST": _candles(90), "NIFTY50": _candles(90)},
        commission_pct=0.03,
        slippage_pct=0.05,
    )

    assert set(dataset["symbol"]) == {"TEST"}
    assert dataset["nifty_return_1"].notna().any()
    assert dataset["nifty_return_20"].notna().any()


def test_target_is_next_open_to_close_net_return_after_configured_costs():
    candles = _candles()
    candles[31]["open"] = 100.0
    candles[31]["close"] = 102.0
    candles[31]["high"] = 103.0
    candles[31]["low"] = 99.0
    candles[30]["open"] = 109.9
    candles[30]["close"] = 110.0
    candles[30]["high"] = 111.0
    candles[30]["low"] = 109.0

    dataset = build_direction_dataset(
        {"TEST": candles}, commission_pct=0.03, slippage_pct=0.05
    )
    prior_timestamp = (
        pd.Timestamp(candles[30]["timestamp"])
        .tz_convert("Asia/Kolkata")
        .normalize()
    )
    prior_row = dataset.loc[dataset["timestamp"] == prior_timestamp].iloc[0]
    entry_debit = 100.0 * 1.0005 * 1.0003
    exit_credit = 102.0 * 0.9995 * 0.9997
    expected_net_return_pct = (exit_credit / entry_debit - 1) * 100

    assert prior_row["target_net_return_pct"] == pytest.approx(expected_net_return_pct)
    assert prior_row["close"] > prior_row["next_close"]
    assert prior_row["target_net_return_pct"] > 0
    assert prior_row["next_net_return_pct"] == pytest.approx(expected_net_return_pct)
    assert prior_row["next_open"] == 100.0
    assert prior_row["next_close"] == 102.0


def test_chronological_split_purges_labels_that_cross_boundaries():
    dates = pd.date_range("2020-01-01", periods=100, freq="D", tz="UTC")
    dataset = pd.DataFrame(
        {
            "timestamp": dates[:-1],
            "target_date": dates[1:],
            "target": [index % 3 - 1 for index in range(99)],
        }
    )

    splits = chronological_split(dataset)

    assert splits["train"]["timestamp"].max() < splits["validation"]["timestamp"].min()
    assert splits["validation"]["timestamp"].max() < splits["test"]["timestamp"].min()
    assert splits["train"]["target_date"].max() < splits["validation"]["timestamp"].min()
    assert splits["validation"]["target_date"].max() < splits["test"]["timestamp"].min()


def test_recent_chronological_split_reserves_exact_test_sessions_and_purges_boundaries():
    candle_dates = pd.date_range("2020-01-01", periods=151, freq="D", tz="UTC")
    dataset = pd.DataFrame(
        {
            "timestamp": candle_dates[:-1],
            "target_date": candle_dates[1:],
            "target": [index % 3 - 1 for index in range(150)],
        }
    )
    expected_test_dates = set(dataset["timestamp"].unique()[-20:])

    splits = chronological_split(dataset, training_sessions=90, test_sessions=20)

    assert set(splits["test"]["timestamp"].unique()) == expected_test_dates
    assert splits["train"]["target_date"].max() < splits["validation"]["timestamp"].min()
    assert splits["validation"]["target_date"].max() < splits["test"]["timestamp"].min()
    assert splits["train"]["timestamp"].min() >= dataset["timestamp"].unique()[-110]


def test_chronological_split_uses_all_available_pre_test_dates_when_unspecified():
    dates = pd.date_range("2020-01-01", periods=220, freq="D", tz="UTC")
    dataset = pd.DataFrame(
        {
            "timestamp": dates[:-1],
            "target_date": dates[1:],
            "target_net_return_pct": np.zeros(len(dates) - 1),
        }
    )
    expected_test_dates = set(dataset["timestamp"].unique()[-40:])

    splits = chronological_split(dataset, test_sessions=40)

    assert set(splits["test"]["timestamp"].unique()) == expected_test_dates
    assert splits["train"]["timestamp"].min() == dataset["timestamp"].min()
    assert splits["train"]["timestamp"].nunique() > 90
    assert splits["train"]["target_date"].max() < splits["validation"]["timestamp"].min()


def test_paper_backtest_target_is_reached_only_after_net_costs():
    test = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC"),
            "symbol": ["TEST"] * 3,
            "next_open": [100.0] * 3,
            "next_close": [110.0] * 3,
        }
    )

    result = _simulate_long_only_paper_backtest(
        test,
        np.array([1, 1, 1]),
        initial_capital=50_000.0,
        profit_target=1_000.0,
        max_drawdown=1_000.0,
        max_position_pct=10.0,
        commission_pct=0.03,
        slippage_pct=0.05,
    )

    assert result["profit_target_reached"] is True
    assert result["net_profit"] >= 1_000.0
    assert result["total_costs"] > 0


def test_paper_backtest_stops_at_maximum_drawdown():
    test = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC"),
            "symbol": ["TEST"] * 3,
            "next_open": [100.0] * 3,
            "next_close": [70.0] * 3,
        }
    )

    result = _simulate_long_only_paper_backtest(
        test,
        np.array([1, 1, 1]),
        initial_capital=50_000.0,
        profit_target=1_000.0,
        max_drawdown=1_000.0,
        max_position_pct=10.0,
        commission_pct=0.03,
        slippage_pct=0.05,
    )

    assert result["max_drawdown_reached"] is True
    assert result["sessions_evaluated"] == 1
    assert result["trades"] == 1


def test_paper_backtest_does_not_trade_zero_or_negative_return_estimates():
    test = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="D", tz="UTC"),
            "symbol": ["TEST"] * 2,
            "next_open": [100.0] * 2,
            "next_close": [110.0] * 2,
        }
    )

    result = _simulate_long_only_paper_backtest(
        test,
        np.array([0.0, -0.01]),
        initial_capital=50_000.0,
        profit_target=1_000.0,
        max_drawdown=1_000.0,
        max_position_pct=10.0,
        commission_pct=0.03,
        slippage_pct=0.05,
    )

    assert result["trades"] == 0
    assert result["final_equity"] == 50_000.0


def test_zero_return_baseline_model_always_predicts_no_trade():
    model = stock_direction._make_model("zero_return_baseline")
    features = pd.DataFrame(np.zeros((3, len(FEATURE_COLUMNS))), columns=FEATURE_COLUMNS)

    model.fit(features, np.array([-0.5, 0.1, 0.3]))

    assert np.array_equal(model.predict(features), np.zeros(3))


def test_tree_voting_regression_produces_predictions_and_feature_importance():
    rng = np.random.default_rng(42)
    features = pd.DataFrame(
        rng.normal(size=(120, len(FEATURE_COLUMNS))),
        columns=FEATURE_COLUMNS,
    )
    target = (
        0.4 * features["return_1"]
        - 0.2 * features["momentum_10"]
        + rng.normal(scale=0.1, size=len(features))
    )
    model = stock_direction._make_model("tree_voting_regression")
    model.fit(features, target)

    predictions = model.predict(features)
    importance = stock_direction._feature_importance(model, FEATURE_COLUMNS)

    assert predictions.shape == (len(features),)
    assert np.isfinite(predictions).all()
    assert importance


class _FakeModel:
    def __init__(self, prediction: float = 0.7):
        self.prediction = prediction

    def predict(self, features):
        return np.full(len(features), self.prediction)


def test_prediction_returns_cost_aware_estimate_and_is_restricted_to_candidate_symbols(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from core import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
        ),
    )
    artifact = tmp_path / "candidate.joblib"
    joblib.dump(
        {
            "model": _FakeModel(),
            "metadata": {
                "schema_version": MODEL_SCHEMA_VERSION,
                "trained_symbols": ["TEST"],
                "model_type": "test",
                "eligible_for_live_display": True,
                "artifact_training": {"through": "2024-01-01T00:00:00+00:00"},
                "execution_costs": {
                    "commission_pct_per_side": 0.03,
                    "slippage_pct_per_side": 0.05,
                },
            },
        },
        artifact,
    )

    prediction = predict_next_session("TEST", _candles(), model_path=artifact)

    assert prediction["decision"] == "TRADE"
    assert prediction["expected_net_return_pct"] == 0.7
    assert prediction["return_estimate_is_calibrated"] is False
    assert prediction["trained_through"].startswith("2024-01-01")
    with pytest.raises(ValueError, match="No trained history"):
        predict_next_session("UNSEEN", _candles(), model_path=artifact)


def test_prediction_recommends_no_trade_when_estimated_net_return_is_not_positive(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from core import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
        ),
    )
    artifact = tmp_path / "candidate.joblib"
    joblib.dump(
        {
            "model": _FakeModel(prediction=0.0),
            "metadata": {
                "schema_version": MODEL_SCHEMA_VERSION,
                "trained_symbols": ["TEST"],
                "model_type": "test",
                "eligible_for_live_display": True,
                "artifact_training": {"through": "2024-01-01T00:00:00+00:00"},
                "execution_costs": {
                    "commission_pct_per_side": 0.03,
                    "slippage_pct_per_side": 0.05,
                },
            },
        },
        artifact,
    )

    prediction = predict_next_session("TEST", _candles(), model_path=artifact)

    assert prediction["decision"] == "NO_TRADE"
    assert prediction["expected_net_return_pct"] == 0.0


def test_prediction_requires_aligned_nifty_context_when_candidate_uses_it(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from core import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
        ),
    )
    artifact = tmp_path / "candidate.joblib"
    metadata = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "trained_symbols": ["TEST"],
        "model_type": "test",
        "eligible_for_live_display": True,
        "market_context_symbols": ["NIFTY50"],
        "features": stock_direction._model_feature_columns(
            ["TEST"], include_market_context=True
        ),
        "artifact_training": {"through": "2021-01-01T00:00:00+00:00"},
        "execution_costs": {
            "commission_pct_per_side": 0.03,
            "slippage_pct_per_side": 0.05,
        },
    }
    joblib.dump({"model": _FakeModel(), "metadata": metadata}, artifact)

    with pytest.raises(ValueError, match="NIFTY50 market context is required"):
        predict_next_session("TEST", _candles(), model_path=artifact)

    prediction = predict_next_session(
        "TEST",
        _candles(),
        model_path=artifact,
        market_candles=_candles(),
    )

    assert prediction["decision"] == "TRADE"


def test_return_training_writes_regression_report_and_candidate(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from core import config

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
    monkeypatch.setattr(stock_direction, "MODEL_NAMES", ("ridge_regression",))
    model_path = tmp_path / "candidate.joblib"
    metadata_path = tmp_path / "candidate.json"

    report = stock_direction.train_stock_direction_candidate(
        {"TEST": _candles(180)},
        model_path=model_path,
        metadata_path=metadata_path,
        data_source="synthetic_test",
        training_sessions=90,
        test_sessions=20,
        allow_historical_promotion=False,
    )

    assert report["schema_version"] == MODEL_SCHEMA_VERSION
    assert report["target"].startswith("next-session open-to-close return")
    assert "mae_pct" in report["test"]
    assert "zero_return_baseline" in report["test"]["baselines"]
    assert report["execution_costs"] == {
        "commission_pct_per_side": 0.03,
        "slippage_pct_per_side": 0.05,
    }
    assert report["eligible_for_live_display"] is False
    assert report["historical_promotion_enabled"] is False
    assert report["validation"]["paper_backtest"]["profit_target"] == 500.0
    assert report["validation"]["paper_backtest"]["max_drawdown_limit"] == 1_000.0
    assert report["promotion_checks"]["validation_paper_profit_target_reached"] is False
    assert model_path.is_file()
    assert metadata_path.is_file()


def test_candidate_status_reports_when_evaluation_withholds_forecasts(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from core import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
        ),
    )
    artifact = tmp_path / "candidate.joblib"
    joblib.dump(
        {
            "model": _FakeModel(),
            "metadata": {
                "schema_version": MODEL_SCHEMA_VERSION,
                "trained_symbols": ["TEST"],
                "model_type": "test",
                "eligible_for_live_display": False,
                "artifact_training": {"through": "2024-01-01T00:00:00+00:00"},
                "execution_costs": {
                    "commission_pct_per_side": 0.03,
                    "slippage_pct_per_side": 0.05,
                },
                "test": {
                    "mae_pct": 0.9,
                    "best_baseline": "zero_return_baseline",
                    "baselines": {"zero_return_baseline": {"mae_pct": 1.0}},
                    "mae_improvement_vs_zero_return_baseline_95pct_ci": [-0.01, 0.02],
                },
                "paper_backtest": {"net_profit": -100.0},
            },
        },
        artifact,
    )

    status = get_candidate_status(artifact)

    assert status["state"] == "withheld"
    assert status["baseline_mae_pct"] == 1.0
    assert status["paper_net_profit"] == -100.0


def test_candidate_status_rejects_artifacts_from_old_training_schema(tmp_path):
    artifact = tmp_path / "candidate.joblib"
    joblib.dump({"model": _FakeModel(), "metadata": {"trained_symbols": ["TEST"]}}, artifact)

    assert get_candidate_status(artifact) == {"state": "needs_retraining"}


def test_prediction_is_withheld_for_unqualified_or_stale_candidates(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from core import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            backtest_default_commission_pct=0.03,
            backtest_default_slippage_pct=0.05,
        ),
    )
    artifact = tmp_path / "candidate.joblib"
    metadata = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "trained_symbols": ["TEST"],
        "model_type": "test",
        "eligible_for_live_display": False,
        "artifact_training": {"through": "2024-01-01T00:00:00+00:00"},
        "execution_costs": {
            "commission_pct_per_side": 0.03,
            "slippage_pct_per_side": 0.05,
        },
    }
    joblib.dump({"model": _FakeModel(), "metadata": metadata}, artifact)

    with pytest.raises(ValueError, match="did not beat"):
        predict_next_session("TEST", _candles(), model_path=artifact)

    metadata["eligible_for_live_display"] = True
    metadata["artifact_training"]["through"] = "2019-01-01T00:00:00+00:00"
    stale_artifact = tmp_path / "stale_candidate.joblib"
    joblib.dump({"model": _FakeModel(), "metadata": metadata}, stale_artifact)

    with pytest.raises(ValueError, match="stale"):
        predict_next_session("TEST", _candles(), model_path=stale_artifact)


def test_train_stock_direction_updates_stale_model_without_overwriting_qualified(
    tmp_path, monkeypatch
):
    from backtesting import train_stock_direction as runner

    model_path = tmp_path / "stock_direction_candidate.joblib"
    metadata_path = tmp_path / "stock_direction_candidate_meta.json"
    shadow_path = tmp_path / "stock_direction_shadow_candidate.joblib"
    report_path = tmp_path / "stock_direction_last_training_report.json"

    joblib.dump({"model": _FakeModel(), "metadata": {"schema_version": 3}}, model_path)
    metadata_path.write_text('{"schema_version": 3}', encoding="utf-8")

    async def fake_fetch(*args, **kwargs):
        return {"TEST": _candles(60)}, {"provider": "fake", "fetched_symbols": ["TEST"], "failed_symbols": {}}

    def fake_train(*args, **kwargs):
        joblib.dump(
            {
                "model": _FakeModel(0.0),
                "metadata": {
                    "schema_version": MODEL_SCHEMA_VERSION,
                    "eligible_for_live_display": False,
                    "model_type": "zero_return_baseline",
                    "test": {
                        "mae_pct": 1.0,
                        "best_baseline": "zero_return_baseline",
                        "baselines": {"zero_return_baseline": {"mae_pct": 1.0}},
                        "mae_improvement_vs_zero_return_baseline_95pct_ci": [0.0, 0.0],
                    },
                    "artifact_training": {"through": "2026-11-27T00:00:00+05:30"},
                    "execution_costs": {"commission_pct_per_side": 0.03, "slippage_pct_per_side": 0.05},
                    "paper_backtest": {"net_profit": 0.0},
                },
            },
            kwargs["model_path"],
        )
        kwargs["metadata_path"].write_text('{"schema_version": 10}', encoding="utf-8")
        return {
            "schema_version": MODEL_SCHEMA_VERSION,
            "eligible_for_live_display": False,
            "historical_promotion_enabled": False,
        }

    monkeypatch.setattr(runner, "MODEL_PATH", model_path)
    monkeypatch.setattr(runner, "METADATA_PATH", metadata_path)
    monkeypatch.setattr(runner, "SHADOW_MODEL_PATH", shadow_path)
    monkeypatch.setattr(runner, "TRAINING_REPORT_PATH", report_path)
    monkeypatch.setattr(runner, "fetch_upstox_daily_data", fake_fetch)
    monkeypatch.setattr(runner, "train_stock_direction_candidate", fake_train)

    runner.main()
    assert get_candidate_status(model_path)["state"] == "withheld"

    # Qualified current-schema model must be preserved on later withheld runs
    qualified_bundle = joblib.load(model_path)
    qualified_bundle["metadata"]["eligible_for_live_display"] = True
    qualified_bundle["metadata"]["model_type"] = "qualified_model"
    joblib.dump(qualified_bundle, model_path)

    runner.main()
    assert get_candidate_status(model_path)["state"] == "qualified_research"
    assert get_candidate_status(model_path)["model"] == "qualified_model"


def test_conviction_threshold_estimator_and_enriched_features():
    wrapper = stock_direction._ConvictionThresholdEstimator(
        _FakeModel(prediction=0.12), min_signal_pct=0.15
    )
    assert np.array_equal(wrapper.predict(np.zeros((2, 3))), np.zeros(2))
    high = stock_direction._ConvictionThresholdEstimator(
        _FakeModel(prediction=0.20), min_signal_pct=0.15
    )
    assert np.allclose(high.predict(np.zeros((2, 3))), np.array([0.20, 0.20]))

    ds = stock_direction.build_direction_dataset(
        {"TEST": _candles(80), "NIFTY50": _candles(80)},
        commission_pct=0.03,
        slippage_pct=0.05,
    )
    cols = stock_direction._model_feature_columns(["TEST"], include_market_context=True)
    x = stock_direction._model_input(ds, cols)
    assert "excess_return_1" in x.columns
    assert "close_in_range" in x.columns
    assert not x.isin([float("inf"), float("-inf")]).any().any()
