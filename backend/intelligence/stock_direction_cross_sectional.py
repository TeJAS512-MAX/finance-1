"""Research-only regime-aware, cross-sectional stock return challenger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline

from core.config import get_settings
from intelligence.stock_direction import (
    DATA_DIR,
    MARKET_CONTEXT_SYMBOL,
    MARKET_FEATURE_COLUMNS,
    MODEL_SCHEMA_VERSION,
    PAPER_MAX_DRAWDOWN,
    PAPER_PROFIT_TARGET,
    _model_feature_columns,
    _model_input,
    _simulate_long_only_paper_backtest,
    build_direction_dataset,
    chronological_split,
)

CROSS_SECTIONAL_MODEL_PATH = DATA_DIR / "stock_direction_cross_sectional_candidate.joblib"
CROSS_SECTIONAL_REPORT_PATH = DATA_DIR / "stock_direction_cross_sectional_report.json"
CROSS_SECTIONAL_SCHEMA_VERSION = 1
REGIME_FEATURES = (
    "market_uptrend_regime",
    "market_high_volatility_regime",
)
BOOTSTRAP_ITERATIONS = 2_000


def _volatility_threshold(training: pd.DataFrame) -> float:
    if "nifty_realized_volatility_20" not in training:
        raise ValueError("The cross-sectional challenger requires NIFTY50 market context")
    market_volatility = (
        training[["timestamp", "nifty_realized_volatility_20"]]
        .drop_duplicates("timestamp")["nifty_realized_volatility_20"]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    if market_volatility.empty:
        raise ValueError("Training data has no usable NIFTY50 volatility observations")
    return float(market_volatility.quantile(0.75))


def _with_regime_features(
    frame: pd.DataFrame,
    volatility_threshold: float,
) -> pd.DataFrame:
    if not set(MARKET_FEATURE_COLUMNS).issubset(frame.columns):
        raise ValueError("The cross-sectional challenger requires complete NIFTY50 features")
    result = frame.copy()
    market_trend = pd.to_numeric(result["nifty_return_20"], errors="coerce")
    market_volatility = pd.to_numeric(
        result["nifty_realized_volatility_20"], errors="coerce"
    )
    result["market_uptrend_regime"] = np.where(
        market_trend.notna(),
        (market_trend > 0).astype(float),
        np.nan,
    )
    result["market_high_volatility_regime"] = np.where(
        market_volatility.notna(),
        (market_volatility > volatility_threshold).astype(float),
        np.nan,
    )
    return result


def _feature_input(
    frame: pd.DataFrame,
    feature_columns: list[str],
    volatility_threshold: float,
) -> pd.DataFrame:
    augmented = _with_regime_features(frame, volatility_threshold)
    base = _model_input(augmented, feature_columns)
    for column in REGIME_FEATURES:
        base[column] = augmented[column]
    return base.reindex(columns=[*feature_columns, *REGIME_FEATURES])


def _make_rank_model() -> Pipeline:
    return Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="median", keep_empty_features=True),
            ),
            (
                "regressor",
                HistGradientBoostingRegressor(
                    max_iter=120,
                    learning_rate=0.05,
                    max_leaf_nodes=7,
                    min_samples_leaf=40,
                    l2_regularization=2.0,
                    early_stopping=False,
                    random_state=42,
                ),
            ),
        ]
    )


def _top_one_signals(
    frame: pd.DataFrame,
    rank_predictions: np.ndarray,
    return_predictions: np.ndarray,
) -> np.ndarray:
    ordered = frame[["timestamp"]].reset_index(drop=True).copy()
    ordered["rank_prediction"] = rank_predictions
    signals = np.zeros(len(ordered), dtype=float)
    for _, session in ordered.groupby("timestamp", sort=True):
        if len(session) < 2:
            continue
        selected = int(session["rank_prediction"].idxmax())
        if return_predictions[selected] > 0:
            signals[selected] = return_predictions[selected]
    return signals


def _top_one_session_returns(
    frame: pd.DataFrame,
    rank_scores: np.ndarray,
    gate_scores: np.ndarray,
) -> dict[pd.Timestamp, float]:
    working = frame[["timestamp", "target_net_return_pct"]].reset_index(drop=True)
    working["rank_score"] = rank_scores
    working["gate_score"] = gate_scores
    returns: dict[pd.Timestamp, float] = {}
    for timestamp, session in working.groupby("timestamp", sort=True):
        if len(session) < 2:
            continue
        selected = int(session["rank_score"].idxmax())
        returns[pd.Timestamp(timestamp)] = (
            float(working.loc[selected, "target_net_return_pct"])
            if working.loc[selected, "gate_score"] > 0
            else 0.0
        )
    return returns


def _bootstrap_mean_difference_ci(
    first: np.ndarray,
    second: np.ndarray,
) -> list[float] | None:
    if len(first) != len(second) or len(first) < 2:
        return None
    differences = first - second
    rng = np.random.default_rng(42)
    sampled_means = np.empty(BOOTSTRAP_ITERATIONS, dtype=float)
    for index in range(BOOTSTRAP_ITERATIONS):
        sampled = rng.choice(differences, size=len(differences), replace=True)
        sampled_means[index] = sampled.mean()
    low, high = np.percentile(sampled_means, [2.5, 97.5])
    return [round(float(low), 4), round(float(high), 4)]


def _ranking_metrics(
    frame: pd.DataFrame,
    rank_predictions: np.ndarray,
    return_predictions: np.ndarray,
) -> dict[str, Any]:
    working = frame[["timestamp", "target_net_return_pct"]].reset_index(drop=True)
    working["rank_prediction"] = rank_predictions
    working["return_prediction"] = return_predictions
    correlations: list[float] = []
    for _, session in working.groupby("timestamp", sort=True):
        if len(session) < 2:
            continue
        correlation = session["rank_prediction"].rank().corr(
            session["target_net_return_pct"].rank()
        )
        if pd.notna(correlation):
            correlations.append(float(correlation))

    rank_returns = _top_one_session_returns(
        frame,
        rank_predictions,
        return_predictions,
    )
    momentum = _top_one_session_returns(
        frame,
        frame["return_5"].to_numpy(dtype=float),
        frame["return_5"].to_numpy(dtype=float),
    )
    common_dates = sorted(set(rank_returns) & set(momentum))
    rank_values = np.array([rank_returns[date] for date in common_dates], dtype=float)
    momentum_values = np.array([momentum[date] for date in common_dates], dtype=float)
    return {
        "sessions_ranked": len(rank_returns),
        "mean_session_spearman_correlation": round(float(np.mean(correlations)), 4)
        if correlations
        else None,
        "top_one_mean_net_return_pct": round(float(rank_values.mean()), 4)
        if len(rank_values)
        else None,
        "top_one_positive_return_fraction": round(
            float(np.mean(rank_values > 0)), 4
        )
        if len(rank_values)
        else None,
        "top_one_vs_no_trade_mean_return_difference_95pct_ci_pct": (
            _bootstrap_mean_difference_ci(rank_values, np.zeros(len(rank_values)))
            if len(rank_values)
            else None
        ),
        "top_one_vs_5day_momentum_mean_return_difference_95pct_ci_pct": (
            _bootstrap_mean_difference_ci(rank_values, momentum_values)
            if len(rank_values)
            else None
        ),
    }


def _fit_heads(
    frame: pd.DataFrame,
    feature_columns: list[str],
    volatility_threshold: float,
) -> tuple[Pipeline, Pipeline]:
    features = _feature_input(frame, feature_columns, volatility_threshold)
    absolute_target = frame["target_net_return_pct"].to_numpy(dtype=float)
    relative_target = (
        frame["target_net_return_pct"]
        - frame.groupby("timestamp")["target_net_return_pct"].transform("mean")
    ).to_numpy(dtype=float)
    rank_model = _make_rank_model()
    return_model = _make_rank_model()
    rank_model.fit(features, relative_target)
    return_model.fit(features, absolute_target)
    return rank_model, return_model


def _evaluate_partition(
    frame: pd.DataFrame,
    rank_model: Pipeline,
    return_model: Pipeline,
    feature_columns: list[str],
    volatility_threshold: float,
) -> dict[str, Any]:
    features = _feature_input(frame, feature_columns, volatility_threshold)
    rank_predictions = rank_model.predict(features)
    return_predictions = return_model.predict(features)
    signals = _top_one_signals(frame, rank_predictions, return_predictions)
    momentum_signals = _top_one_signals(
        frame,
        frame["return_5"].to_numpy(dtype=float),
        frame["return_5"].to_numpy(dtype=float),
    )
    settings = get_settings()

    def simulate(predictions: np.ndarray) -> dict[str, Any]:
        return _simulate_long_only_paper_backtest(
            frame,
            predictions,
            initial_capital=settings.paper_trading_initial_capital,
            profit_target=PAPER_PROFIT_TARGET,
            max_drawdown=PAPER_MAX_DRAWDOWN,
            max_position_pct=settings.max_position_size_pct,
            commission_pct=settings.backtest_default_commission_pct,
            slippage_pct=settings.backtest_default_slippage_pct,
        )

    actual = frame["target_net_return_pct"].to_numpy(dtype=float)
    return {
        "samples": int(len(frame)),
        "sessions": int(frame["timestamp"].nunique()),
        "absolute_return_mae_pct": round(
            float(mean_absolute_error(actual, return_predictions)), 4
        ),
        "zero_return_baseline_mae_pct": round(
            float(mean_absolute_error(actual, np.zeros(len(actual)))), 4
        ),
        "ranking": _ranking_metrics(frame, rank_predictions, return_predictions),
        "top_one_paper_backtest": simulate(signals),
        "five_day_momentum_baseline_paper_backtest": simulate(momentum_signals),
        "no_trade_baseline_paper_backtest": simulate(np.zeros(len(frame))),
    }


def train_cross_sectional_candidate(
    historical_data: dict[str, list[dict[str, Any]]],
    data_source: str = "unspecified",
    data_report: dict[str, Any] | None = None,
    model_path: Path = CROSS_SECTIONAL_MODEL_PATH,
    report_path: Path = CROSS_SECTIONAL_REPORT_PATH,
    test_sessions: int = 90,
) -> dict[str, Any]:
    """Train a separate research challenger; never promote or modify the active model."""
    settings = get_settings()
    dataset = build_direction_dataset(
        historical_data,
        commission_pct=settings.backtest_default_commission_pct,
        slippage_pct=settings.backtest_default_slippage_pct,
    )
    if "nifty_realized_volatility_20" not in dataset:
        raise ValueError("Cross-sectional challenger requires NIFTY50 market history")
    splits = chronological_split(dataset, test_sessions=test_sessions)
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    symbols = sorted(dataset["symbol"].unique().tolist())
    feature_columns = _model_feature_columns(symbols, include_market_context=True)

    validation_threshold = _volatility_threshold(train)
    validation_rank_model, validation_return_model = _fit_heads(
        train,
        feature_columns,
        validation_threshold,
    )
    validation_report = _evaluate_partition(
        validation,
        validation_rank_model,
        validation_return_model,
        feature_columns,
        validation_threshold,
    )

    development = pd.concat([train, validation], ignore_index=True).sort_values(
        ["timestamp", "symbol"]
    )
    test_threshold = _volatility_threshold(development)
    test_rank_model, test_return_model = _fit_heads(
        development,
        feature_columns,
        test_threshold,
    )
    test_report = _evaluate_partition(
        test,
        test_rank_model,
        test_return_model,
        feature_columns,
        test_threshold,
    )

    final_threshold = _volatility_threshold(dataset)
    final_rank_model, final_return_model = _fit_heads(
        dataset,
        feature_columns,
        final_threshold,
    )
    metadata = {
        "architecture": "regime_aware_cross_sectional_ranker",
        "schema_version": CROSS_SECTIONAL_SCHEMA_VERSION,
        "base_feature_schema_version": MODEL_SCHEMA_VERSION,
        "mode": "research_only",
        "eligible_for_live_display": False,
        "live_trading_enabled": False,
        "historical_test_is_descriptive_only": True,
        "market_context_symbols": [MARKET_CONTEXT_SYMBOL],
        "trained_symbols": symbols,
        "features": [*feature_columns, *REGIME_FEATURES],
        "regime_volatility_threshold": final_threshold,
        "execution_costs": {
            "commission_pct_per_side": settings.backtest_default_commission_pct,
            "slippage_pct_per_side": settings.backtest_default_slippage_pct,
        },
        "artifact_training": {
            "samples": int(len(dataset)),
            "through": dataset["target_date"].max().isoformat(),
            "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        },
    }
    bundle = {
        "rank_model": final_rank_model,
        "return_model": final_return_model,
        "metadata": metadata,
    }
    report = {
        **metadata,
        "data_source": data_source,
        "data_report": data_report or {},
        "objective": (
            "Rank symbols by predicted next-session cross-sectional excess return; "
            "trade only the top-ranked symbol when predicted after-cost absolute return is positive."
        ),
        "risk_limits": {
            "paper_profit_target": PAPER_PROFIT_TARGET,
            "paper_max_drawdown": PAPER_MAX_DRAWDOWN,
            "max_position_size_pct": settings.max_position_size_pct,
        },
        "date_ranges": {
            name: {
                "start": part["timestamp"].min().isoformat(),
                "end": part["timestamp"].max().isoformat(),
                "samples": int(len(part)),
                "sessions": int(part["timestamp"].nunique()),
            }
            for name, part in splits.items()
        },
        "validation": validation_report,
        "historical_test": test_report,
        "promotion": "None; require an independent prospective shadow evaluation.",
        "backtest_exclusions": (
            "Taxes and exchange/regulatory fees are not modeled; historical test results "
            "are descriptive only and cannot authorize promotion."
        ),
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_model_path = model_path.with_suffix(model_path.suffix + ".tmp")
    joblib.dump(bundle, temporary_model_path)
    temporary_model_path.replace(model_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_report_path = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary_report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary_report_path.replace(report_path)
    return report
