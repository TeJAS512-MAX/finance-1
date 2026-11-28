"""Forward-only paper evaluation for an unqualified next-session model."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv

from backtesting.upstox_stock_history import fetch_upstox_daily_data
from core.config import get_settings
from intelligence.stock_direction import (
    DATA_DIR,
    MARKET_CONTEXT_SYMBOL,
    MODEL_SCHEMA_VERSION,
    PAPER_MAX_DRAWDOWN,
    PAPER_PROFIT_TARGET,
    SHADOW_MODEL_PATH,
    _after_cost_long_return_pct,
    _execution_costs_match,
    _load_bundle,
    _simulate_long_only_paper_backtest,
    _validated_candles,
    predict_next_session,
)

load_dotenv(find_dotenv())

SHADOW_LOG_PATH = DATA_DIR / "stock_direction_shadow_predictions.json"
SHADOW_HISTORY_DAYS = 45
SHADOW_EVALUATION_SESSION_LIMIT = 90


def _read_log(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    entries = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"Invalid shadow prediction log format: {log_path}")
    required_keys = {
        "symbol",
        "as_of",
        "candidate_id",
        "decision",
        "expected_net_return_pct",
        "actual_net_return_pct",
    }
    if any(not required_keys.issubset(entry) for entry in entries):
        raise ValueError(f"Shadow prediction log is missing required fields: {log_path}")
    return entries


def _resolve_pending_predictions(
    entries: list[dict[str, Any]],
    historical_data: dict[str, list[dict[str, Any]]],
    commission_pct: float,
    slippage_pct: float,
) -> int:
    resolved_count = 0
    frames = {
        symbol.upper(): _validated_candles(candles)
        for symbol, candles in historical_data.items()
    }
    for entry in entries:
        if entry["actual_net_return_pct"] is not None:
            continue
        candles = frames.get(str(entry["symbol"]).upper())
        if candles is None or candles.empty:
            continue
        as_of = pd.Timestamp(entry["as_of"])
        next_sessions = candles.loc[candles["timestamp"] > as_of]
        if next_sessions.empty:
            continue
        outcome = next_sessions.iloc[0]
        entry["target_date"] = outcome["timestamp"].isoformat()
        entry["next_open"] = float(outcome["open"])
        entry["next_close"] = float(outcome["close"])
        entry["actual_net_return_pct"] = float(
            _after_cost_long_return_pct(
                float(outcome["open"]),
                float(outcome["close"]),
                commission_pct,
                slippage_pct,
            )
        )
        entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
        resolved_count += 1
    return resolved_count


def _current_candidate_metrics(
    entries: list[dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    candidate_entries = [
        entry for entry in entries if entry["candidate_id"] == candidate_id
    ]
    resolved = [
        entry
        for entry in candidate_entries
        if entry["actual_net_return_pct"] is not None
    ]
    resolved_trades = [entry for entry in resolved if entry["decision"] == "TRADE"]
    wins = sum(float(entry["actual_net_return_pct"]) > 0 for entry in resolved_trades)

    metrics: dict[str, Any] = {
        "candidate_id": candidate_id,
        "predictions": len(candidate_entries),
        "resolved_predictions": len(resolved),
        "pending_predictions": len(candidate_entries) - len(resolved),
        "resolved_trade_predictions": len(resolved_trades),
        "trade_win_rate": round(wins / len(resolved_trades), 4)
        if resolved_trades
        else None,
        "mean_realized_trade_return_pct": round(
            float(np.mean([entry["actual_net_return_pct"] for entry in resolved_trades])),
            4,
        )
        if resolved_trades
        else None,
        "paper_backtest": None,
    }
    if resolved:
        simulation_rows = [
            {
                "timestamp": entry["target_date"],
                "symbol": entry["symbol"],
                "next_open": entry["next_open"],
                "next_close": entry["next_close"],
            }
            for entry in resolved
        ]
        predicted_returns = np.array(
            [entry["expected_net_return_pct"] for entry in resolved], dtype=float
        )
        settings = get_settings()
        metrics["paper_backtest"] = _simulate_long_only_paper_backtest(
            pd.DataFrame(simulation_rows),
            predicted_returns,
            initial_capital=settings.paper_trading_initial_capital,
            profit_target=PAPER_PROFIT_TARGET,
            max_drawdown=PAPER_MAX_DRAWDOWN,
            max_position_pct=settings.max_position_size_pct,
            commission_pct=settings.backtest_default_commission_pct,
            slippage_pct=settings.backtest_default_slippage_pct,
        )
    return metrics


def _evaluation_progress(
    entries: list[dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    candidate_entries = [
        entry for entry in entries if entry["candidate_id"] == candidate_id
    ]
    forecast_dates = {
        pd.Timestamp(entry["as_of"]).date() for entry in candidate_entries
    }
    resolved_dates = {
        pd.Timestamp(entry["as_of"]).date()
        for entry in candidate_entries
        if entry["actual_net_return_pct"] is not None
    }
    return {
        "sessions_started": len(forecast_dates),
        "sessions_resolved": len(resolved_dates),
        "complete": len(resolved_dates) >= SHADOW_EVALUATION_SESSION_LIMIT
        and all(
            entry["actual_net_return_pct"] is not None
            for entry in candidate_entries
        ),
    }


def record_shadow_predictions(
    historical_data: dict[str, list[dict[str, Any]]],
    model_path: Path = SHADOW_MODEL_PATH,
    log_path: Path = SHADOW_LOG_PATH,
) -> dict[str, Any]:
    """Resolve prior forecasts and record only forecasts beyond candidate training data."""
    bundle = _load_bundle(model_path)
    metadata = bundle["metadata"]
    if metadata.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ValueError("Shadow candidate uses an older schema and must be retrained")
    if not _execution_costs_match(metadata):
        raise ValueError("Shadow candidate execution costs differ from current settings")

    execution_costs = metadata["execution_costs"]
    commission_pct = float(execution_costs["commission_pct_per_side"])
    slippage_pct = float(execution_costs["slippage_pct_per_side"])
    training_date = pd.Timestamp(metadata["artifact_training"]["through"]).date()
    candidate_group_id = str(
        metadata["artifact_training"].get(
            "generated_at", metadata["artifact_training"]["through"]
        )
    )
    shadow_models = bundle.get("shadow_models")
    if not isinstance(shadow_models, dict) or metadata["model_type"] not in shadow_models:
        raise ValueError("Shadow candidate is missing its selected/challenger model pack")
    candidate_ids = {
        model_name: f"{candidate_group_id}:{model_name}"
        for model_name in shadow_models
    }
    selected_candidate_id = candidate_ids[metadata["model_type"]]
    entries = _read_log(log_path)
    resolved_count = _resolve_pending_predictions(
        entries,
        historical_data,
        commission_pct,
        slippage_pct,
    )
    existing_keys = {
        (entry["symbol"].upper(), entry["as_of"], entry["candidate_id"])
        for entry in entries
    }
    new_count = 0
    recorded_at = datetime.now(timezone.utc).isoformat()
    progress = _evaluation_progress(entries, selected_candidate_id)

    if (
        not progress["complete"]
        and progress["sessions_started"] < SHADOW_EVALUATION_SESSION_LIMIT
    ):
        for symbol in metadata["trained_symbols"]:
            candles = historical_data.get(symbol)
            if not candles:
                continue
            clean_candles = _validated_candles(candles)
            if clean_candles.empty:
                continue
            latest_date = clean_candles["timestamp"].iloc[-1].date()
            if latest_date <= training_date:
                continue
            for model_name, challenger in shadow_models.items():
                prediction = predict_next_session(
                    symbol,
                    candles,
                    model_path=model_path,
                    shadow_mode=True,
                    market_candles=historical_data.get(MARKET_CONTEXT_SYMBOL),
                    model_override=challenger,
                    model_name_override=model_name,
                )
                candidate_id = candidate_ids[model_name]
                key = (symbol.upper(), prediction["as_of"], candidate_id)
                if key in existing_keys:
                    continue
                entries.append(
                    {
                        "symbol": symbol.upper(),
                        "as_of": prediction["as_of"],
                        "candidate_id": candidate_id,
                        "candidate_group_id": candidate_group_id,
                        "model": model_name,
                        "candidate_trained_through": prediction["trained_through"],
                        "decision": prediction["decision"],
                        "expected_net_return_pct": prediction["expected_net_return_pct"],
                        "actual_net_return_pct": None,
                        "target_date": None,
                        "next_open": None,
                        "next_close": None,
                        "recorded_at": recorded_at,
                    }
                )
                existing_keys.add(key)
                new_count += 1

    if new_count or resolved_count:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_log_path = log_path.with_suffix(log_path.suffix + ".tmp")
        temporary_log_path.write_text(
            json.dumps(entries, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary_log_path.replace(log_path)

    progress = _evaluation_progress(entries, selected_candidate_id)
    metrics = _current_candidate_metrics(entries, selected_candidate_id)
    return {
        **metrics,
        "selected_model": metadata["model_type"],
        "challenger_metrics": {
            model_name: _current_candidate_metrics(entries, candidate_id)
            for model_name, candidate_id in candidate_ids.items()
        },
        "new_predictions": new_count,
        "newly_resolved_predictions": resolved_count,
        "evaluation_session_limit": SHADOW_EVALUATION_SESSION_LIMIT,
        "evaluation_sessions_started": progress["sessions_started"],
        "evaluation_sessions_resolved": progress["sessions_resolved"],
        "evaluation_complete": progress["complete"],
        "log_file": log_path.name,
    }


def main() -> None:
    if not SHADOW_MODEL_PATH.is_file():
        raise FileNotFoundError(
            "No shadow candidate is saved. Run backtesting.train_stock_direction first."
        )
    bundle = _load_bundle(SHADOW_MODEL_PATH)
    metadata = bundle["metadata"]
    if metadata.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ValueError("Shadow candidate uses an older schema; retrain before evaluation")
    historical_data, data_report = asyncio.run(
        fetch_upstox_daily_data(
            days_back=SHADOW_HISTORY_DAYS,
            symbols=metadata["trained_symbols"],
            persist_cache=False,
        )
    )
    result = record_shadow_predictions(historical_data)
    result["data_source"] = data_report["provider"]
    result["fetched_symbols"] = data_report["fetched_symbols"]
    result["failed_symbols"] = sorted(data_report["failed_symbols"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
