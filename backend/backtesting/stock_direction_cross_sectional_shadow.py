"""Forward-only paper evaluation for the regime-aware cross-sectional challenger."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv

from backtesting.stock_direction_shadow import SHADOW_EVALUATION_SESSION_LIMIT
from backtesting.upstox_stock_history import fetch_upstox_daily_data
from core.config import get_settings
from intelligence.stock_direction import (
    DATA_DIR,
    MARKET_CONTEXT_SYMBOL,
    PAPER_MAX_DRAWDOWN,
    PAPER_PROFIT_TARGET,
    _after_cost_long_return_pct,
    _execution_costs_match,
    _load_bundle,
    _market_feature_frame,
    _simulate_long_only_paper_backtest,
    _validated_candles,
    _feature_frame,
)
from intelligence.stock_direction_cross_sectional import (
    CROSS_SECTIONAL_MODEL_PATH,
    CROSS_SECTIONAL_SCHEMA_VERSION,
    REGIME_FEATURES,
    _feature_input,
    _top_one_signals,
)

load_dotenv(find_dotenv())

CROSS_SECTIONAL_SHADOW_LOG_PATH = (
    DATA_DIR / "stock_direction_cross_sectional_shadow_predictions.json"
)


def _read_log(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    entries = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"Invalid cross-sectional shadow log format: {log_path}")
    required_keys = {
        "symbol",
        "as_of",
        "candidate_id",
        "rank_score",
        "expected_net_return_pct",
        "decision",
        "actual_net_return_pct",
    }
    if any(not required_keys.issubset(entry) for entry in entries):
        raise ValueError(f"Cross-sectional shadow log is missing required fields: {log_path}")
    return entries


def _latest_session_rows(
    historical_data: dict[str, list[dict[str, Any]]],
    trained_symbols: list[str],
    trained_through: str,
) -> pd.DataFrame:
    market_features = _market_feature_frame(
        historical_data.get(MARKET_CONTEXT_SYMBOL, [])
    )
    if market_features.empty:
        raise ValueError("Cross-sectional shadow evaluation requires NIFTY50 candles")

    frames = []
    for symbol in trained_symbols:
        candles = historical_data.get(symbol, [])
        clean_candles = _validated_candles(candles)
        if clean_candles.empty:
            continue
        features = _feature_frame(clean_candles.to_dict("records"))
        if features.empty:
            continue
        features["symbol"] = symbol.upper()
        frames.append(
            features.merge(
                market_features,
                on="timestamp",
                how="left",
                validate="one_to_one",
            )
        )
    if not frames:
        return pd.DataFrame()

    cutoff_date = pd.Timestamp(trained_through).date()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.loc[
        (combined["timestamp"].dt.date > cutoff_date)
        & combined["nifty_return_20"].notna()
        & combined["nifty_realized_volatility_20"].notna()
    ]
    if combined.empty:
        return combined

    latest_timestamp = combined["timestamp"].max()
    latest = combined.loc[combined["timestamp"] == latest_timestamp]
    return (
        latest.sort_values("symbol")
        .drop_duplicates("symbol", keep="last")
        .reset_index(drop=True)
    )


def _resolve_pending(
    entries: list[dict[str, Any]],
    historical_data: dict[str, list[dict[str, Any]]],
    commission_pct: float,
    slippage_pct: float,
) -> int:
    frames = {
        symbol.upper(): _validated_candles(candles)
        for symbol, candles in historical_data.items()
    }
    resolved_count = 0
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


def _candidate_metrics(
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
    trade_entries = [entry for entry in resolved if entry["decision"] == "TRADE"]
    wins = sum(float(entry["actual_net_return_pct"]) > 0 for entry in trade_entries)
    grouped = pd.DataFrame(resolved)
    correlations: list[float] = []
    if not grouped.empty:
        for _, session in grouped.groupby("as_of", sort=True):
            if (
                len(session) < 2
                or session["rank_score"].nunique() < 2
                or session["actual_net_return_pct"].nunique() < 2
            ):
                continue
            correlation = session["rank_score"].rank().corr(
                session["actual_net_return_pct"].rank()
            )
            if pd.notna(correlation):
                correlations.append(float(correlation))

    paper_backtest = None
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
        predictions = np.array(
            [
                entry["expected_net_return_pct"]
                if entry["decision"] == "TRADE"
                else 0.0
                for entry in resolved
            ],
            dtype=float,
        )
        settings = get_settings()
        paper_backtest = _simulate_long_only_paper_backtest(
            pd.DataFrame(simulation_rows),
            predictions,
            initial_capital=settings.paper_trading_initial_capital,
            profit_target=PAPER_PROFIT_TARGET,
            max_drawdown=PAPER_MAX_DRAWDOWN,
            max_position_pct=settings.max_position_size_pct,
            commission_pct=settings.backtest_default_commission_pct,
            slippage_pct=settings.backtest_default_slippage_pct,
        )

    return {
        "candidate_id": candidate_id,
        "predictions": len(candidate_entries),
        "resolved_predictions": len(resolved),
        "pending_predictions": len(candidate_entries) - len(resolved),
        "trade_predictions": len(trade_entries),
        "trade_win_rate": round(wins / len(trade_entries), 4)
        if trade_entries
        else None,
        "mean_session_spearman_correlation": round(float(np.mean(correlations)), 4)
        if correlations
        else None,
        "mean_realized_trade_return_pct": round(
            float(np.mean([entry["actual_net_return_pct"] for entry in trade_entries])),
            4,
        )
        if trade_entries
        else None,
        "paper_backtest": paper_backtest,
    }


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


def record_cross_sectional_shadow_predictions(
    historical_data: dict[str, list[dict[str, Any]]],
    model_path: Path = CROSS_SECTIONAL_MODEL_PATH,
    log_path: Path = CROSS_SECTIONAL_SHADOW_LOG_PATH,
) -> dict[str, Any]:
    bundle = _load_bundle(model_path)
    metadata = bundle["metadata"]
    if metadata.get("schema_version") != CROSS_SECTIONAL_SCHEMA_VERSION:
        raise ValueError("Cross-sectional candidate schema is outdated; retrain it")
    if metadata.get("eligible_for_live_display") or metadata.get("live_trading_enabled"):
        raise ValueError("Cross-sectional shadow runner accepts research-only candidates")
    if not _execution_costs_match(metadata):
        raise ValueError("Candidate execution costs differ from current settings")

    execution_costs = metadata["execution_costs"]
    commission_pct = float(execution_costs["commission_pct_per_side"])
    slippage_pct = float(execution_costs["slippage_pct_per_side"])
    candidate_id = (
        f"{metadata['artifact_training']['generated_at']}:"
        f"{metadata['architecture']}"
    )
    entries = _read_log(log_path)
    resolved_count = _resolve_pending(
        entries,
        historical_data,
        commission_pct,
        slippage_pct,
    )
    progress = _evaluation_progress(entries, candidate_id)
    new_count = 0

    if (
        not progress["complete"]
        and progress["sessions_started"] < SHADOW_EVALUATION_SESSION_LIMIT
    ):
        latest = _latest_session_rows(
            historical_data,
            metadata["trained_symbols"],
            metadata["artifact_training"]["through"],
        )
        if len(latest) >= 2:
            feature_columns = [
                column
                for column in metadata["features"]
                if column not in REGIME_FEATURES
            ]
            features = _feature_input(
                latest,
                feature_columns,
                float(metadata["regime_volatility_threshold"]),
            )
            rank_predictions = bundle["rank_model"].predict(features)
            return_predictions = bundle["return_model"].predict(features)
            signals = _top_one_signals(
                latest,
                rank_predictions,
                return_predictions,
            )
            as_of = latest["timestamp"].iloc[0].isoformat()
            existing_keys = {
                (str(entry["symbol"]).upper(), entry["as_of"], entry["candidate_id"])
                for entry in entries
            }
            recorded_at = datetime.now(timezone.utc).isoformat()
            for index, row in latest.iterrows():
                key = (str(row["symbol"]).upper(), as_of, candidate_id)
                if key in existing_keys:
                    continue
                entries.append(
                    {
                        "symbol": str(row["symbol"]).upper(),
                        "as_of": as_of,
                        "candidate_id": candidate_id,
                        "candidate_group_id": metadata["artifact_training"][
                            "generated_at"
                        ],
                        "architecture": metadata["architecture"],
                        "rank_score": float(rank_predictions[index]),
                        "expected_net_return_pct": float(return_predictions[index]),
                        "decision": "TRADE" if signals[index] > 0 else "NO_TRADE",
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

    progress = _evaluation_progress(entries, candidate_id)
    return {
        **_candidate_metrics(entries, candidate_id),
        "new_predictions": new_count,
        "newly_resolved_predictions": resolved_count,
        "evaluation_session_limit": SHADOW_EVALUATION_SESSION_LIMIT,
        "evaluation_sessions_started": progress["sessions_started"],
        "evaluation_sessions_resolved": progress["sessions_resolved"],
        "evaluation_complete": progress["complete"],
        "log_file": log_path.name,
    }


def main() -> None:
    if not CROSS_SECTIONAL_MODEL_PATH.is_file():
        raise FileNotFoundError(
            "No cross-sectional challenger exists; run its training command first."
        )
    metadata = _load_bundle(CROSS_SECTIONAL_MODEL_PATH)["metadata"]
    historical_data, data_report = asyncio.run(
        fetch_upstox_daily_data(
            days_back=45,
            symbols=metadata["trained_symbols"],
            persist_cache=False,
        )
    )
    result = record_cross_sectional_shadow_predictions(historical_data)
    result["data_source"] = data_report["provider"]
    result["fetched_symbols"] = data_report["fetched_symbols"]
    result["failed_symbols"] = sorted(data_report["failed_symbols"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
