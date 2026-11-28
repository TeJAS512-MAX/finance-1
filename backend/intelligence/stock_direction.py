"""Research-only next-session net-return model and evaluation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
    VotingRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_PATH = DATA_DIR / "stock_direction_candidate.joblib"
METADATA_PATH = DATA_DIR / "stock_direction_candidate_meta.json"
SHADOW_MODEL_PATH = DATA_DIR / "stock_direction_shadow_candidate.joblib"
MODEL_SCHEMA_VERSION = 10
MARKET_CONTEXT_SYMBOL = "NIFTY50"
PAPER_PROFIT_TARGET = 500.0
PAPER_MAX_DRAWDOWN = 1_000.0
MODEL_NAMES = (
    "ridge_regression",
    "random_forest_regression",
    "extra_trees_regression",
    "hist_gradient_boosting_regression",
    "tree_voting_regression",
)
FEATURE_COLUMNS = [
    "rsi",
    "trend_strength",
    "return_1",
    "momentum_10",
    "volatility_pct",
    "range_pct",
    "return_5",
    "return_20",
    "volume_ratio",
    "candle_body_pct",
    "overnight_gap_pct",
    "realized_volatility_20",
]
MARKET_FEATURE_COLUMNS = [
    "nifty_return_1",
    "nifty_return_5",
    "nifty_return_20",
    "nifty_realized_volatility_20",
]
CANDLE_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


@lru_cache(maxsize=4)
def _cached_bundle(model_path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    return joblib.load(model_path)


def _load_bundle(model_path: Path) -> dict[str, Any]:
    stat = model_path.stat()
    return _cached_bundle(str(model_path), stat.st_mtime_ns)


def _execution_costs_match(metadata: dict[str, Any]) -> bool:
    from core.config import get_settings

    settings = get_settings()
    execution_costs = metadata.get("execution_costs", {})
    return (
        np.isclose(
            execution_costs.get("commission_pct_per_side", float("nan")),
            settings.backtest_default_commission_pct,
        )
        and np.isclose(
            execution_costs.get("slippage_pct_per_side", float("nan")),
            settings.backtest_default_slippage_pct,
        )
    )


def candidate_supports_symbol(symbol: str, model_path: Path = MODEL_PATH) -> bool:
    """Return whether evaluation qualified this symbol for research display."""
    bundle = _load_bundle(model_path)
    metadata = bundle["metadata"]
    return (
        metadata.get("schema_version") == MODEL_SCHEMA_VERSION
        and metadata.get("eligible_for_live_display", False)
        and symbol.upper() in metadata["trained_symbols"]
        and _execution_costs_match(metadata)
    )


def get_candidate_status(model_path: Path = MODEL_PATH) -> dict[str, Any]:
    """Expose the evaluation gate and test baseline so consumers can explain withheld forecasts."""
    if not model_path.is_file():
        return {"state": "not_trained"}

    metadata = _load_bundle(model_path)["metadata"]
    if metadata.get("schema_version") != MODEL_SCHEMA_VERSION:
        return {"state": "needs_retraining"}
    if not _execution_costs_match(metadata):
        return {"state": "needs_retraining"}
    if (
        "eligible_for_live_display" not in metadata
        or not metadata.get("test")
        or not metadata.get("artifact_training")
    ):
        return {"state": "needs_retraining"}
    test_metrics = metadata["test"]
    baseline_name = test_metrics["best_baseline"]
    return {
        "state": "qualified_research" if metadata["eligible_for_live_display"] else "withheld",
        "model": metadata["model_type"],
        "data_source": metadata.get("data_source"),
        "trained_through": metadata["artifact_training"]["through"],
        "target": metadata.get("target"),
        "requires_market_context": bool(metadata.get("market_context_symbols")),
        "test_mae_pct": test_metrics["mae_pct"],
        "baseline_mae_pct": test_metrics["baselines"][baseline_name]["mae_pct"],
        "mae_improvement_95pct_ci": test_metrics[
            "mae_improvement_vs_zero_return_baseline_95pct_ci"
        ],
        "paper_net_profit": metadata["paper_backtest"]["net_profit"],
    }


def _validated_candles(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(candles)
    if not set(CANDLE_COLUMNS).issubset(frame.columns):
        return pd.DataFrame(columns=CANDLE_COLUMNS)

    frame = frame[list(CANDLE_COLUMNS)].copy()
    frame["_source_timestamp"] = pd.to_datetime(
        frame["timestamp"], utc=True, errors="coerce"
    )
    frame["timestamp"] = (
        frame["_source_timestamp"].dt.tz_convert("Asia/Kolkata").dt.normalize()
    )
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    valid_ohlc = (
        (frame[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (frame["volume"] >= 0)
        & (frame["high"] >= frame[["open", "low", "close"]].max(axis=1))
        & (frame["low"] <= frame[["open", "high", "close"]].min(axis=1))
    )
    frame = (
        frame.loc[valid_ohlc]
        .sort_values("_source_timestamp")
        .drop_duplicates("timestamp", keep="last")
        .sort_values("timestamp")
        .drop(columns="_source_timestamp")
        .reset_index(drop=True)
    )
    return frame


def _feature_frame(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = _validated_candles(candles)
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "close", *FEATURE_COLUMNS])
    close = frame["close"]
    previous_close = close.shift(1)
    returns = close.pct_change(fill_method=None) * 100
    change = close.diff()
    average_gain = change.clip(lower=0).rolling(14, min_periods=14).mean()
    average_loss = (-change.clip(upper=0)).rolling(14, min_periods=14).mean()
    relative_strength = average_gain / average_loss
    rsi = 100 - 100 / (1 + relative_strength)
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_gain == 0) & (average_loss > 0), 0)
    rsi = rsi.mask((average_gain == 0) & (average_loss == 0), 50)

    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    average_volume = frame["volume"].rolling(20, min_periods=5).mean()
    features = pd.DataFrame(
        {
            "timestamp": frame["timestamp"],
            "close": close,
            "rsi": rsi,
            "trend_strength": (close.ewm(span=9, adjust=False).mean() - close.ewm(span=21, adjust=False).mean())
            / close
            * 100,
            "return_1": returns,
            "momentum_10": close.pct_change(10, fill_method=None) * 100,
            "volatility_pct": true_range.rolling(14, min_periods=14).mean() / close * 100,
            "range_pct": (frame["high"] - frame["low"]) / close * 100,
            "return_5": close.pct_change(5, fill_method=None) * 100,
            "return_20": close.pct_change(20, fill_method=None) * 100,
            "volume_ratio": frame["volume"] / average_volume,
            "candle_body_pct": (close - frame["open"]) / frame["open"] * 100,
            "overnight_gap_pct": (frame["open"] - previous_close) / previous_close * 100,
            "realized_volatility_20": returns.rolling(20, min_periods=20).std(ddof=0),
        }
    )
    features[FEATURE_COLUMNS] = features[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    return features


def _market_feature_frame(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = _validated_candles(candles)
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", *MARKET_FEATURE_COLUMNS])

    returns = frame["close"].pct_change(fill_method=None) * 100
    features = pd.DataFrame(
        {
            "timestamp": frame["timestamp"],
            "nifty_return_1": returns,
            "nifty_return_5": frame["close"].pct_change(5, fill_method=None) * 100,
            "nifty_return_20": frame["close"].pct_change(20, fill_method=None) * 100,
            "nifty_realized_volatility_20": returns.rolling(20, min_periods=20).std(
                ddof=0
            ),
        }
    )
    features[MARKET_FEATURE_COLUMNS] = features[MARKET_FEATURE_COLUMNS].replace(
        [np.inf, -np.inf], np.nan
    )
    return features


def _model_feature_columns(
    symbols: list[str],
    include_market_context: bool = False,
) -> list[str]:
    return [
        *FEATURE_COLUMNS,
        *(MARKET_FEATURE_COLUMNS if include_market_context else []),
        *(f"symbol__{symbol.upper()}" for symbol in sorted(set(symbols))),
    ]


def _model_input(frame: pd.DataFrame, model_feature_columns: list[str]) -> pd.DataFrame:
    numeric_features = [
        column
        for column in (*FEATURE_COLUMNS, *MARKET_FEATURE_COLUMNS)
        if column in model_feature_columns
    ]
    model_input = frame.reindex(columns=numeric_features).copy()
    if "symbol" in frame:
        normalized_symbols = frame["symbol"].astype(str).str.upper()
        for column in model_feature_columns:
            if column.startswith("symbol__"):
                model_input[column] = (
                    normalized_symbols == column.removeprefix("symbol__")
                ).astype(float)
    return model_input.reindex(columns=model_feature_columns, fill_value=0.0)


def _after_cost_long_return_pct(
    open_price: float | pd.Series,
    close_price: float | pd.Series,
    commission_pct: float,
    slippage_pct: float,
) -> float | pd.Series:
    entry_fill = open_price * (1 + slippage_pct / 100)
    exit_fill = close_price * (1 - slippage_pct / 100)
    entry_debit = entry_fill * (1 + commission_pct / 100)
    exit_credit = exit_fill * (1 - commission_pct / 100)
    return (exit_credit / entry_debit - 1) * 100


def build_direction_dataset(
    historical_data: dict[str, list[dict[str, Any]]],
    commission_pct: float | None = None,
    slippage_pct: float | None = None,
) -> pd.DataFrame:
    """Build after-cost open-to-close return targets from each completed candle."""
    if commission_pct is None or slippage_pct is None:
        from core.config import get_settings

        settings = get_settings()
        commission_pct = (
            settings.backtest_default_commission_pct
            if commission_pct is None
            else commission_pct
        )
        slippage_pct = (
            settings.backtest_default_slippage_pct
            if slippage_pct is None
            else slippage_pct
        )
    if not 0 <= commission_pct < 100 or not 0 <= slippage_pct < 100:
        raise ValueError("Commission and slippage must be between 0 and 100 percent")

    market_candles = historical_data.get(MARKET_CONTEXT_SYMBOL, [])
    market_features = _market_feature_frame(market_candles)
    rows = []
    for symbol, candles in historical_data.items():
        if symbol.upper() == MARKET_CONTEXT_SYMBOL:
            continue
        clean_candles = _validated_candles(candles)
        if clean_candles.empty:
            continue
        features = _feature_frame(clean_candles.to_dict("records"))
        if len(features) < 22:
            continue
        next_open = clean_candles["open"].shift(-1)
        next_close = clean_candles["close"].shift(-1)
        target_net_return_pct = _after_cost_long_return_pct(
            next_open,
            next_close,
            commission_pct,
            slippage_pct,
        )
        next_timestamp = features["timestamp"].shift(-1)
        sample = features.copy()
        sample["target_net_return_pct"] = target_net_return_pct
        sample["target_date"] = next_timestamp
        sample["symbol"] = symbol.upper()
        sample["next_net_return_pct"] = target_net_return_pct
        sample["next_open"] = next_open
        sample["next_close"] = next_close
        if not market_features.empty:
            sample = sample.merge(
                market_features,
                on="timestamp",
                how="left",
                validate="one_to_one",
            )
        rows.append(
            sample.dropna(
                subset=[
                    "target_net_return_pct",
                    "target_date",
                    "next_open",
                    "next_close",
                ]
            )
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                *FEATURE_COLUMNS,
                "timestamp",
                "target_date",
                "symbol",
                "target_net_return_pct",
                "next_net_return_pct",
                "next_open",
                "next_close",
            ]
        )
    dataset = pd.concat(rows, ignore_index=True)
    return dataset.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def chronological_split(
    dataset: pd.DataFrame,
    training_sessions: int | None = None,
    test_sessions: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Split by unique session dates and purge labels crossing each boundary."""
    dates = np.array(sorted(dataset["timestamp"].dropna().unique()))
    if len(dates) < 30:
        raise ValueError("At least 30 unique session dates are required for chronological evaluation")
    if training_sessions is None and test_sessions is None:
        validation_start = dates[int(len(dates) * 0.60)]
        test_start = dates[int(len(dates) * 0.80)]
        train_mask = (dataset["timestamp"] < validation_start) & (
            dataset["target_date"] < validation_start
        )
        validation_mask = (
            (dataset["timestamp"] >= validation_start)
            & (dataset["timestamp"] < test_start)
            & (dataset["target_date"] < test_start)
        )
        test_mask = dataset["timestamp"] >= test_start
    elif training_sessions is None:
        if test_sessions is None or test_sessions < 1:
            raise ValueError("test_sessions must be at least 1")
        pre_test_sessions = len(dates) - test_sessions
        if pre_test_sessions < 30:
            raise ValueError(
                "At least 30 pre-test session dates are required when training_sessions is omitted"
            )
        validation_sessions = max(1, round(pre_test_sessions * 0.30))
        validation_start = dates[-test_sessions - validation_sessions]
        test_start = dates[-test_sessions]
        train_mask = (dataset["timestamp"] < validation_start) & (
            dataset["target_date"] < validation_start
        )
        validation_mask = (
            (dataset["timestamp"] >= validation_start)
            & (dataset["timestamp"] < test_start)
            & (dataset["target_date"] < test_start)
        )
        test_mask = dataset["timestamp"] >= test_start
    else:
        if test_sessions is None:
            raise ValueError("training_sessions and test_sessions must be provided together")
        if training_sessions < 30 or test_sessions < 1:
            raise ValueError("training_sessions must be at least 30 and test_sessions at least 1")
        required_sessions = training_sessions + test_sessions
        if len(dates) < required_sessions:
            raise ValueError(
                f"At least {required_sessions} unique session dates are required for "
                f"{training_sessions} training and {test_sessions} test sessions"
            )
        training_start = dates[-required_sessions]
        validation_sessions = max(1, round(training_sessions * 0.30))
        validation_start = dates[-test_sessions - validation_sessions]
        test_start = dates[-test_sessions]
        train_mask = (
            (dataset["timestamp"] >= training_start)
            & (dataset["timestamp"] < validation_start)
            & (dataset["target_date"] < validation_start)
        )
        validation_mask = (
            (dataset["timestamp"] >= validation_start)
            & (dataset["timestamp"] < test_start)
            & (dataset["target_date"] < test_start)
        )
        test_mask = dataset["timestamp"] >= test_start

    splits = {
        "train": dataset.loc[train_mask].copy(),
        "validation": dataset.loc[validation_mask].copy(),
        "test": dataset.loc[test_mask].copy(),
    }
    if any(part.empty for part in splits.values()):
        raise ValueError("Chronological split produced an empty partition")
    return splits


def _make_regressor(name: str) -> Any:
    if name == "tree_voting_regression":
        return VotingRegressor(
            estimators=[
                ("random_forest", _make_regressor("random_forest_regression")),
                ("extra_trees", _make_regressor("extra_trees_regression")),
                (
                    "hist_gradient_boosting",
                    _make_regressor("hist_gradient_boosting_regression"),
                ),
            ]
        )

    regressor = {
        "random_forest_regression": RandomForestRegressor(
            n_estimators=240,
            max_depth=8,
            min_samples_leaf=25,
            n_jobs=-1,
            random_state=42,
        ),
        "extra_trees_regression": ExtraTreesRegressor(
            n_estimators=240,
            max_depth=8,
            min_samples_leaf=25,
            n_jobs=-1,
            random_state=42,
        ),
        "hist_gradient_boosting_regression": HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=42,
        ),
    }.get(name)
    if name == "zero_return_baseline":
        return DummyRegressor(strategy="constant", constant=0.0)
    if name == "ridge_regression":
        return Ridge(alpha=10.0)
    if regressor is None:
        raise ValueError(f"Unknown model: {name}")
    return regressor


def _make_model(name: str) -> Pipeline:
    regressor = _make_regressor(name)
    steps = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if name == "ridge_regression":
        steps.append(("scaler", StandardScaler()))
    steps.append(("regressor", regressor))
    return Pipeline(steps)


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    return {
        "mae_pct": round(float(mean_absolute_error(actual, predicted)), 4),
        "rmse_pct": round(float(np.sqrt(mean_squared_error(actual, predicted))), 4),
        "r2": round(float(r2_score(actual, predicted)), 4),
        "trade_signals": int(np.count_nonzero(predicted > 0)),
        "mean_predicted_net_return_pct": round(float(np.mean(predicted)), 4),
    }


def _simulate_long_only_paper_backtest(
    test: pd.DataFrame,
    predictions: np.ndarray,
    initial_capital: float,
    profit_target: float,
    max_drawdown: float,
    max_position_pct: float,
    commission_pct: float,
    slippage_pct: float,
) -> dict[str, Any]:
    """Simulate one-session long trades after each signal, including configured costs."""
    if len(test) != len(predictions):
        raise ValueError("Prediction count must match the holdout rows")

    rows = test.assign(_prediction=predictions).sort_values(["timestamp", "symbol"])
    equity = initial_capital
    peak_equity = initial_capital
    maximum_drawdown = 0.0
    total_costs = 0.0
    trade_count = 0
    winning_trades = 0
    sessions_evaluated = 0
    max_position_fraction = max_position_pct / 100
    commission_fraction = commission_pct / 100
    slippage_fraction = slippage_pct / 100
    stop_reason = "holdout_complete"

    for _, session in rows.groupby("timestamp", sort=True):
        if equity >= initial_capital + profit_target:
            stop_reason = "profit_target_reached"
            break
        if peak_equity - equity >= max_drawdown:
            stop_reason = "max_drawdown_reached"
            break

        sessions_evaluated += 1
        signals = session.loc[session["_prediction"] > 0]
        position_budget = min(
            equity * max_position_fraction,
            equity / len(signals) if not signals.empty else 0,
        )
        session_pnl = 0.0
        for row in signals.itertuples():
            entry_price = float(row.next_open)
            exit_price = float(row.next_close)
            entry_fill = entry_price * (1 + slippage_fraction)
            exit_fill = exit_price * (1 - slippage_fraction)
            quantity = int(
                position_budget / (entry_fill * (1 + commission_fraction))
            )
            if quantity <= 0:
                continue

            entry_notional = quantity * entry_fill
            exit_notional = quantity * exit_fill
            entry_commission = entry_notional * commission_fraction
            exit_commission = exit_notional * commission_fraction
            trade_pnl = (
                exit_notional
                - exit_commission
                - entry_notional
                - entry_commission
            )
            session_pnl += trade_pnl
            total_costs += (
                quantity * (entry_price + exit_price) * slippage_fraction
                + entry_commission
                + exit_commission
            )
            trade_count += 1
            winning_trades += int(trade_pnl > 0)

        equity += session_pnl
        peak_equity = max(peak_equity, equity)
        maximum_drawdown = max(maximum_drawdown, peak_equity - equity)
        if equity >= initial_capital + profit_target:
            stop_reason = "profit_target_reached"
        elif maximum_drawdown >= max_drawdown:
            stop_reason = "max_drawdown_reached"
        else:
            continue
        break

    return {
        "strategy": "Long-only; enter at next session open and exit at its close",
        "initial_capital": round(initial_capital, 2),
        "profit_target": round(profit_target, 2),
        "target_equity": round(initial_capital + profit_target, 2),
        "max_drawdown_limit": round(max_drawdown, 2),
        "max_position_pct": round(max_position_pct, 2),
        "commission_pct_per_side": round(commission_pct, 4),
        "slippage_pct_per_side": round(slippage_pct, 4),
        "sessions_in_holdout": int(test["timestamp"].nunique()),
        "sessions_evaluated": sessions_evaluated,
        "trades": trade_count,
        "win_rate": round(winning_trades / trade_count, 4) if trade_count else 0.0,
        "total_costs": round(total_costs, 2),
        "final_equity": round(equity, 2),
        "net_profit": round(equity - initial_capital, 2),
        "max_drawdown": round(maximum_drawdown, 2),
        "profit_target_reached": stop_reason == "profit_target_reached",
        "max_drawdown_reached": stop_reason == "max_drawdown_reached",
        "stop_reason": stop_reason,
        "exclusions": "Taxes and exchange/regulatory fees are not modeled.",
    }


def _date_bootstrap_mae_improvement(
    test: pd.DataFrame,
    actual: np.ndarray,
    predicted: np.ndarray,
    iterations: int = 2000,
) -> list[float]:
    date_values = test["timestamp"].drop_duplicates().to_numpy()
    row_indices = {
        timestamp: np.flatnonzero(test["timestamp"].to_numpy() == timestamp)
        for timestamp in date_values
    }
    rng = np.random.default_rng(42)
    scores = []
    for _ in range(iterations):
        sampled_dates = rng.choice(date_values, size=len(date_values), replace=True)
        indices = np.concatenate([row_indices[date] for date in sampled_dates])
        scores.append(
            mean_absolute_error(actual[indices], np.zeros(len(indices)))
            - mean_absolute_error(actual[indices], predicted[indices])
        )
    low, high = np.percentile(scores, [2.5, 97.5])
    return [round(float(low), 4), round(float(high), 4)]


def _feature_importance(
    model: Pipeline,
    model_feature_columns: list[str],
) -> dict[str, float]:
    regressor = model.named_steps["regressor"]
    if hasattr(regressor, "feature_importances_"):
        values = regressor.feature_importances_
    elif hasattr(regressor, "coef_"):
        values = np.abs(regressor.coef_)
        if values.ndim > 1:
            values = values.mean(axis=0)
    elif hasattr(regressor, "estimators_"):
        member_importances = [
            estimator.feature_importances_
            for estimator in regressor.estimators_
            if hasattr(estimator, "feature_importances_")
        ]
        if not member_importances:
            return {}
        values = np.mean(member_importances, axis=0)
    else:
        return {}
    return {
        name: round(float(value), 6)
        for name, value in sorted(
            zip(model_feature_columns, values), key=lambda item: item[1], reverse=True
        )
    }


def train_stock_direction_candidate(
    historical_data: dict[str, list[dict[str, Any]]],
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
    data_source: str = "unspecified",
    data_report: dict[str, Any] | None = None,
    training_sessions: int | None = None,
    test_sessions: int = 20,
    allow_historical_promotion: bool = False,
) -> dict[str, Any]:
    """Evaluate after-cost return models against a zero-return baseline."""
    from core.config import get_settings

    settings = get_settings()
    commission_pct = settings.backtest_default_commission_pct
    slippage_pct = settings.backtest_default_slippage_pct
    all_samples = build_direction_dataset(
        historical_data,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
    )
    splits = chronological_split(
        all_samples,
        training_sessions=training_sessions,
        test_sessions=test_sessions,
    )
    dataset = (
        pd.concat(splits.values(), ignore_index=True)
        .sort_values(["timestamp", "symbol"])
        .reset_index(drop=True)
    )
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    include_market_context = not _market_feature_frame(
        historical_data.get(MARKET_CONTEXT_SYMBOL, [])
    ).empty
    model_feature_columns = _model_feature_columns(
        sorted(dataset["symbol"].unique().tolist()),
        include_market_context=include_market_context,
    )

    unique_train_dates = np.array(sorted(train["timestamp"].unique()))
    fold_results: dict[str, list[float]] = {
        name: [] for name in (*MODEL_NAMES, "zero_return_baseline")
    }
    fold_profit_per_session: dict[str, list[float]] = {
        name: [] for name in (*MODEL_NAMES, "zero_return_baseline")
    }
    for _, validation_indices in TimeSeriesSplit(n_splits=3).split(unique_train_dates):
        fold_validation_start = unique_train_dates[validation_indices[0]]
        fold_dates = unique_train_dates[validation_indices]
        fold_train = train.loc[
            (train["timestamp"] < fold_validation_start)
            & (train["target_date"] < fold_validation_start)
        ]
        fold_validation = train.loc[train["timestamp"].isin(fold_dates)]
        if fold_train.empty or fold_validation.empty:
            continue
        actual = fold_validation["target_net_return_pct"].to_numpy(dtype=float)
        fold_results["zero_return_baseline"].append(
            float(mean_absolute_error(actual, np.zeros(len(actual))))
        )
        fold_profit_per_session["zero_return_baseline"].append(0.0)
        for name in MODEL_NAMES:
            model = _make_model(name)
            model.fit(
                _model_input(fold_train, model_feature_columns),
                fold_train["target_net_return_pct"],
            )
            prediction = model.predict(_model_input(fold_validation, model_feature_columns))
            fold_results[name].append(float(mean_absolute_error(actual, prediction)))
            fold_backtest = _simulate_long_only_paper_backtest(
                fold_validation,
                prediction,
                initial_capital=settings.paper_trading_initial_capital,
                profit_target=PAPER_PROFIT_TARGET,
                max_drawdown=PAPER_MAX_DRAWDOWN,
                max_position_pct=settings.max_position_size_pct,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
            )
            fold_profit_per_session[name].append(
                fold_backtest["net_profit"] / max(fold_backtest["sessions_evaluated"], 1)
            )
    if not all(fold_results.values()):
        raise ValueError("Not enough time-ordered samples to complete walk-forward validation")

    model_names = [*MODEL_NAMES, "zero_return_baseline"]
    selected_name = max(
        model_names,
        key=lambda name: (
            float(np.mean(fold_profit_per_session[name])),
            -float(np.mean(fold_results[name])),
        ),
    )
    best_baseline_name = "zero_return_baseline"

    model = _make_model(selected_name)
    model.fit(
        _model_input(train, model_feature_columns),
        train["target_net_return_pct"],
    )
    validation_prediction = model.predict(
        _model_input(validation, model_feature_columns)
    )
    validation_actual = validation["target_net_return_pct"].to_numpy(dtype=float)
    validation_baselines = {
        "zero_return_baseline": np.zeros(len(validation)),
    }
    validation_backtest = _simulate_long_only_paper_backtest(
        validation,
        validation_prediction,
        initial_capital=settings.paper_trading_initial_capital,
        profit_target=PAPER_PROFIT_TARGET,
        max_drawdown=PAPER_MAX_DRAWDOWN,
        max_position_pct=settings.max_position_size_pct,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
    )
    validation_beats_zero_return_baseline = (
        mean_absolute_error(validation_actual, validation_prediction)
        < mean_absolute_error(validation_actual, np.zeros(len(validation_actual)))
    )
    final_training = pd.concat([train, validation], ignore_index=True)
    final_model = _make_model(selected_name)
    final_model.fit(
        _model_input(final_training, model_feature_columns),
        final_training["target_net_return_pct"],
    )
    test_actual = test["target_net_return_pct"].to_numpy(dtype=float)
    test_prediction = final_model.predict(_model_input(test, model_feature_columns))
    paper_backtest = _simulate_long_only_paper_backtest(
        test,
        test_prediction,
        initial_capital=settings.paper_trading_initial_capital,
        profit_target=PAPER_PROFIT_TARGET,
        max_drawdown=PAPER_MAX_DRAWDOWN,
        max_position_pct=settings.max_position_size_pct,
        commission_pct=settings.backtest_default_commission_pct,
        slippage_pct=settings.backtest_default_slippage_pct,
    )
    test_baselines = {"zero_return_baseline": np.zeros(len(test))}
    best_test_baseline_name = "zero_return_baseline"
    best_test_baseline = test_baselines[best_test_baseline_name]
    bootstrap_delta_ci = _date_bootstrap_mae_improvement(test, test_actual, test_prediction)
    per_symbol_test = {}
    for symbol, symbol_test in test.assign(prediction=test_prediction).groupby("symbol"):
        symbol_actual = symbol_test["target_net_return_pct"].to_numpy(dtype=float)
        symbol_prediction = symbol_test["prediction"].to_numpy(dtype=float)
        per_symbol_test[symbol] = {
            "samples": int(len(symbol_test)),
            **_regression_metrics(symbol_actual, symbol_prediction),
        }
    walk_forward_beats_baselines = (
        float(np.mean(fold_results[selected_name]))
        < float(np.mean(fold_results[best_baseline_name]))
    )
    walk_forward_trading_beats_no_trade = (
        float(np.mean(fold_profit_per_session[selected_name])) > 0
    )
    validation_paper_profit_target_reached = validation_backtest[
        "profit_target_reached"
    ]
    validation_drawdown_within_limit = not validation_backtest[
        "max_drawdown_reached"
    ]
    out_of_sample_beats_baseline = bootstrap_delta_ci[0] > 0
    historical_gates_passed = (
        walk_forward_beats_baselines
        and validation_beats_zero_return_baseline
        and validation_paper_profit_target_reached
        and validation_drawdown_within_limit
        and walk_forward_trading_beats_no_trade
        and out_of_sample_beats_baseline
        and paper_backtest["profit_target_reached"]
    )
    eligible_for_live_display = historical_gates_passed and allow_historical_promotion
    promotion_checks = {
        "walk_forward_mae_beats_zero_return_baseline": walk_forward_beats_baselines,
        "validation_mae_beats_zero_return_baseline": validation_beats_zero_return_baseline,
        "validation_paper_profit_target_reached": validation_paper_profit_target_reached,
        "validation_drawdown_within_limit": validation_drawdown_within_limit,
        "walk_forward_paper_profit_per_session_positive": walk_forward_trading_beats_no_trade,
        "holdout_mae_improvement_interval_excludes_zero": out_of_sample_beats_baseline,
        "holdout_paper_profit_target_reached": paper_backtest["profit_target_reached"],
        "historical_promotion_enabled": allow_historical_promotion,
    }
    shadow_models = {}
    for model_name in (*MODEL_NAMES, "zero_return_baseline"):
        challenger = _make_model(model_name)
        challenger.fit(
            _model_input(dataset, model_feature_columns),
            dataset["target_net_return_pct"],
        )
        shadow_models[model_name] = challenger
    final_model = shadow_models[selected_name]

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_type": selected_name,
        "schema_version": MODEL_SCHEMA_VERSION,
        "mode": "research_only",
        "data_source": data_source,
        "data_report": data_report or {},
        "eligible_for_live_display": eligible_for_live_display,
        "historical_gates_passed": historical_gates_passed,
        "historical_promotion_enabled": allow_historical_promotion,
        "promotion_checks": promotion_checks,
        "paper_backtest": paper_backtest,
        "execution_costs": {
            "commission_pct_per_side": commission_pct,
            "slippage_pct_per_side": slippage_pct,
        },
        "evaluation_design": {
            "pre_test_training_sessions": int(
                all_samples["timestamp"].nunique() - test_sessions
            ),
            "holdout_test_sessions": test_sessions,
            "validation_fraction_of_training_window": 0.30,
            "paper_profit_target": PAPER_PROFIT_TARGET,
            "paper_max_drawdown": PAPER_MAX_DRAWDOWN,
        },
        "target": (
            "next-session open-to-close return after configured commission and slippage; "
            "trade only when predicted net return is positive"
        ),
        "features": model_feature_columns,
        "shadow_challenger_models": sorted(shadow_models),
        "market_context_symbols": (
            [MARKET_CONTEXT_SYMBOL] if include_market_context else []
        ),
        "trained_symbols": sorted(dataset["symbol"].unique().tolist()),
        "date_ranges": {
            name: {
                "start": part["timestamp"].min().isoformat(),
                "end": part["timestamp"].max().isoformat(),
                "samples": int(len(part)),
                "unique_dates": int(part["timestamp"].nunique()),
            }
            for name, part in splits.items()
        },
        "artifact_training": {
            "samples": int(len(dataset)),
            "through": dataset["target_date"].max().isoformat(),
            "symbols": int(dataset["symbol"].nunique()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "target_summary_pct": {
            "mean": round(float(dataset["target_net_return_pct"].mean()), 4),
            "median": round(float(dataset["target_net_return_pct"].median()), 4),
            "positive_fraction": round(
                float((dataset["target_net_return_pct"] > 0).mean()), 4
            ),
        },
        "walk_forward_mae_pct": {
            name: [round(score, 4) for score in scores]
            for name, scores in fold_results.items()
        },
        "walk_forward_paper_profit_per_session": {
            name: [round(score, 4) for score in scores]
            for name, scores in fold_profit_per_session.items()
        },
        "selected_model": selected_name,
        "selected_model_beats_walk_forward_zero_return_baseline_by_mae": walk_forward_beats_baselines,
        "selected_model_beats_validation_zero_return_baseline_by_mae": validation_beats_zero_return_baseline,
        "selected_model_positive_walk_forward_paper_profit": walk_forward_trading_beats_no_trade,
        "best_walk_forward_baseline": best_baseline_name,
        "validation": {
            **_regression_metrics(validation_actual, validation_prediction),
            "beats_zero_return_baseline_by_mae": validation_beats_zero_return_baseline,
            "paper_backtest": validation_backtest,
            "baselines": {
                name: _regression_metrics(validation_actual, prediction)
                for name, prediction in validation_baselines.items()
            },
        },
        "test": {
            **_regression_metrics(test_actual, test_prediction),
            "by_symbol": per_symbol_test,
            "baselines": {
                name: _regression_metrics(test_actual, prediction)
                for name, prediction in test_baselines.items()
            },
            "best_baseline": best_test_baseline_name,
            "mae_improvement_vs_zero_return_baseline_95pct_ci": bootstrap_delta_ci,
            "out_of_sample_beats_zero_return_baseline_with_95pct_confidence": out_of_sample_beats_baseline,
        },
        "top_feature_importance": _feature_importance(
            final_model,
            model_feature_columns,
        ),
    }

    temporary_model_path = model_path.with_suffix(model_path.suffix + ".tmp")
    temporary_metadata_path = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
    joblib.dump(
        {
            "model": final_model,
            "metadata": metadata,
            "shadow_models": shadow_models,
        },
        temporary_model_path,
    )
    temporary_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    temporary_model_path.replace(model_path)
    temporary_metadata_path.replace(metadata_path)
    return metadata


def predict_next_session(
    symbol: str,
    candles: list[dict[str, Any]],
    model_path: Path = MODEL_PATH,
    shadow_mode: bool = False,
    market_candles: list[dict[str, Any]] | None = None,
    model_override: Any | None = None,
    model_name_override: str | None = None,
) -> dict[str, Any]:
    """Estimate next-session net executable return for a trained symbol."""
    bundle = _load_bundle(model_path)
    metadata = bundle["metadata"]
    normalized_symbol = symbol.upper()
    if metadata.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ValueError("Candidate artifact uses an older schema and must be retrained")
    if not shadow_mode and not metadata.get("eligible_for_live_display", False):
        raise ValueError("Candidate did not beat the walk-forward and out-of-sample baseline gate")
    if model_override is not None and not shadow_mode:
        raise ValueError("Challenger model overrides are allowed only in shadow mode")
    if normalized_symbol not in metadata["trained_symbols"]:
        raise ValueError(f"No trained history for {normalized_symbol}; prediction withheld")
    if not _execution_costs_match(metadata):
        raise ValueError("Candidate execution costs differ from current settings; retrain the model")
    features = _feature_frame(candles)
    market_context_symbols = metadata.get("market_context_symbols", [])
    if market_context_symbols:
        if not market_candles:
            raise ValueError("NIFTY50 market context is required for this candidate")
        market_features = _market_feature_frame(market_candles)
        if market_features.empty:
            raise ValueError("Insufficient NIFTY50 market history for this candidate")
        features = features.merge(
            market_features,
            on="timestamp",
            how="left",
            validate="one_to_one",
        )
    model_feature_columns = metadata.get("features", FEATURE_COLUMNS)
    required_features = [
        *FEATURE_COLUMNS,
        *(
            MARKET_FEATURE_COLUMNS
            if market_context_symbols
            else []
        ),
    ]
    latest = features.dropna(subset=required_features).tail(1)
    if latest.empty:
        raise ValueError(f"Insufficient valid daily candles to predict {normalized_symbol}")
    if market_context_symbols:
        latest_market_timestamp = (
            _market_feature_frame(market_candles)
            .dropna(subset=MARKET_FEATURE_COLUMNS)["timestamp"]
            .tail(1)
        )
        if latest_market_timestamp.empty or (
            latest_market_timestamp.iloc[0] != latest["timestamp"].iloc[0]
        ):
            raise ValueError("NIFTY50 market data is not aligned with the latest stock session")
    training_date = pd.Timestamp(metadata["artifact_training"]["through"]).date()
    if not shadow_mode and latest["timestamp"].iloc[0].date() > training_date:
        raise ValueError("Candidate is stale relative to the latest completed daily candle")
    model = model_override or bundle["model"]
    latest = latest.assign(symbol=normalized_symbol)
    expected_net_return_pct = float(
        model.predict(_model_input(latest, model_feature_columns))[0]
    )
    if not np.isfinite(expected_net_return_pct):
        raise ValueError("Candidate returned a non-finite return estimate")
    return {
        "decision": "TRADE" if expected_net_return_pct > 0 else "NO_TRADE",
        "expected_net_return_pct": round(expected_net_return_pct, 4),
        "return_estimate_is_calibrated": False,
        "as_of": latest["timestamp"].iloc[0].isoformat(),
        "trained_through": metadata["artifact_training"]["through"],
        "data_source": metadata.get("data_source"),
        "model": model_name_override or metadata["model_type"],
        "mode": "shadow_research" if shadow_mode else "research_only",
    }
