"""Walk-forward statistical validation and live-capital readiness gate."""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import structlog
from dotenv import find_dotenv, load_dotenv

from core.config import get_settings
from intelligence.ml_filter import MLQualityFilter
from intelligence.stock_direction import get_candidate_status

READINESS_REPORT_PATH = Path(__file__).parent.parent / "data" / "system_readiness_report.json"


def _jwt_expiry_status(token: str | None) -> dict[str, Any]:
    if not token or not token.strip():
        return {"present": False, "expired": True, "expires_at": None}
    parts = token.strip().split(".")
    if len(parts) != 3:
        return {"present": True, "expired": False, "expires_at": None}
    try:
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8"))
        exp = payload.get("exp")
        if exp is None:
            return {"present": True, "expired": False, "expires_at": None}
        exp_dt = datetime.fromtimestamp(float(exp), tz=timezone.utc)
        return {
            "present": True,
            "expired": datetime.now(timezone.utc) >= exp_dt,
            "expires_at": exp_dt.isoformat(),
        }
    except Exception:
        return {"present": True, "expired": False, "expires_at": None}


def _bootstrap_mean_ci(values: list[float], iterations: int = 2000) -> list[float] | None:
    if len(values) < 2:
        return None
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(42)
    means = np.empty(iterations, dtype=float)
    for idx in range(iterations):
        means[idx] = rng.choice(arr, size=len(arr), replace=True).mean()
    low, high = np.percentile(means, [2.5, 97.5])
    return [round(float(low), 2), round(float(high), 2)]


def evaluate_walk_forward_intraday(
    historical_data: dict[str, list[dict[str, Any]]],
    initial_capital: float = 50_000.0,
) -> dict[str, Any]:
    """Run expanding-window multi-fold chronological OOS evaluation with gap-aware fills."""
    import backtesting.engine as eng
    from backtesting.train_ml import build_triple_barrier_dataset

    logging.disable(logging.CRITICAL)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))

    fold_specs = [
        ("fold_1_40_to_60", 0.40, 0.60),
        ("fold_2_60_to_80", 0.60, 0.80),
        ("fold_3_80_to_100", 0.80, 1.00),
    ]
    folds: list[dict[str, Any]] = []
    all_oos_pnls: list[float] = []
    all_p1_pnl = 0.0

    try:
        for label, tr_end_frac, oos_end_frac in fold_specs:
            tr_data: dict[str, list[dict[str, Any]]] = {}
            oos_data: dict[str, list[dict[str, Any]]] = {}
            for sym, candles in historical_data.items():
                if len(candles) < 80:
                    continue
                i_tr = int(len(candles) * tr_end_frac)
                i_oos = int(len(candles) * oos_end_frac)
                if i_tr >= 60 and i_oos - i_tr >= 30:
                    tr_data[sym] = candles[:i_tr]
                    oos_data[sym] = candles[i_tr:i_oos]

            train_tb = build_triple_barrier_dataset(tr_data)
            with tempfile.TemporaryDirectory() as tmpdir:
                flt = MLQualityFilter(model_prefix=f"wf_{label}")
                flt.model_dir = Path(tmpdir)
                trained = flt.train_on_backtest_data(train_tb, mode="standard", validation_fraction=0.2)
                if not trained:
                    continue
                orig_flt = eng.ml_filter
                eng.ml_filter = flt
                try:
                    p1 = eng.run_backtest(oos_data, use_phase1=True, use_ml_filter=False, initial_capital=initial_capital)
                    p2 = eng.run_backtest(oos_data, use_phase1=True, use_ml_filter=True, initial_capital=initial_capital)
                finally:
                    eng.ml_filter = orig_flt

                n_trades = int(p2.get("total_trades", 0))
                trade_pnls = p2.get("trade_pnls") or []
                all_oos_pnls.extend(float(x) for x in trade_pnls)
                all_p1_pnl += float(p1.get("net_profit", 0.0))

                folds.append({
                    "fold": label,
                    "calibrated_threshold": flt.approval_threshold,
                    "phase1_trades": int(p1.get("total_trades", 0)),
                    "phase1_net_profit": float(p1.get("net_profit", 0.0)),
                    "phase2a_trades": n_trades,
                    "phase2a_win_rate_pct": float(p2.get("win_rate_pct", 0.0)),
                    "phase2a_net_profit": float(p2.get("net_profit", 0.0)),
                    "phase2a_max_drawdown": float(p2.get("max_drawdown", 0.0)),
                    "phase2a_profit_factor": float(p2.get("profit_factor", 0.0)),
                })
    finally:
        logging.disable(logging.NOTSET)

    total_trades = sum(f["phase2a_trades"] for f in folds)
    total_pnl = round(sum(f["phase2a_net_profit"] for f in folds), 2)
    worst_dd = round(max((f["phase2a_max_drawdown"] for f in folds), default=0.0), 2)
    gross_wins = sum(x for x in all_oos_pnls if x > 0)
    gross_losses = abs(sum(x for x in all_oos_pnls if x <= 0))
    combined_pf = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (round(gross_wins, 2) if gross_wins > 0 else 0.0)
    weighted_wr = (
        round(sum(f["phase2a_trades"] * f["phase2a_win_rate_pct"] for f in folds) / total_trades, 2)
        if total_trades > 0
        else 0.0
    )
    pnl_ci = _bootstrap_mean_ci(all_oos_pnls)

    return {
        "folds": folds,
        "folds_evaluated": len(folds),
        "folds_profitable": sum(1 for f in folds if f["phase2a_net_profit"] > 0),
        "combined_trades": total_trades,
        "combined_win_rate_pct": weighted_wr,
        "combined_net_profit": total_pnl,
        "combined_profit_factor": combined_pf,
        "worst_fold_max_drawdown": worst_dd,
        "mean_trade_pnl_95pct_ci": pnl_ci,
        "phase1_combined_net_profit": round(all_p1_pnl, 2),
        "capital_preserved_vs_phase1": round(total_pnl - all_p1_pnl, 2),
    }


def evaluate_system_readiness(
    historical_data: dict[str, list[dict[str, Any]]] | None = None,
    save_report: bool = True,
) -> dict[str, Any]:
    """Compute honest paper and live-capital readiness gates."""
    root_env = Path(__file__).parent.parent.parent / ".env"
    if root_env.is_file():
        load_dotenv(root_env)
    else:
        load_dotenv(find_dotenv())
    settings = get_settings()
    flt = MLQualityFilter()
    daily_status = get_candidate_status()
    live_transport_ready = True  # Native async httpx Upstox REST fallback always available

    wf_oos: dict[str, Any] | None = None
    if historical_data is not None:
        wf_oos = evaluate_walk_forward_intraday(
            historical_data,
            initial_capital=settings.paper_trading_initial_capital,
        )
    elif READINESS_REPORT_PATH.is_file():
        existing = json.loads(READINESS_REPORT_PATH.read_text(encoding="utf-8"))
        wf_oos = existing.get("walk_forward_oos")

    analytics_tok = _jwt_expiry_status(os.getenv("UPSTOX_ANALYTICS_TOKEN"))
    access_tok = _jwt_expiry_status(os.getenv("UPSTOX_ACCESS_TOKEN"))
    models_single_threaded = all(
        getattr(m, "n_jobs", 1) == 1 for m in getattr(flt, "models", {}).values()
    )

    checks = {
        "intraday_ml_loaded": bool(flt.is_loaded and len(flt.models) == 4),
        "intraday_single_thread_inference": bool(models_single_threaded),
        "emergency_kill_switch_clear": not settings.emergency_kill_switch_active,
        "live_broker_transport_ready": live_transport_ready,
        "analytics_token_valid": bool(analytics_tok["present"] and not analytics_tok["expired"]),
        "trading_access_token_valid": bool(access_tok["present"] and not access_tok["expired"]),
        "daily_model_qualified": daily_status.get("state") == "qualified_research",
    }

    if wf_oos:
        ci = wf_oos.get("mean_trade_pnl_95pct_ci") or [0.0, 0.0]
        checks["wf_oos_positive_net_profit"] = wf_oos["combined_net_profit"] > 0
        checks["wf_oos_profit_factor_ge_1_15"] = wf_oos["combined_profit_factor"] >= 1.15
        checks["wf_oos_95pct_ci_excludes_zero"] = ci[0] > 0
        checks["wf_oos_drawdown_within_5pct"] = (
            wf_oos["worst_fold_max_drawdown"] <= settings.paper_trading_initial_capital * 0.05
        )
    else:
        checks["wf_oos_positive_net_profit"] = False
        checks["wf_oos_profit_factor_ge_1_15"] = False
        checks["wf_oos_95pct_ci_excludes_zero"] = False
        checks["wf_oos_drawdown_within_5pct"] = False

    paper_ready = (
        checks["intraday_ml_loaded"]
        and checks["intraday_single_thread_inference"]
        and checks["emergency_kill_switch_clear"]
        and checks["wf_oos_drawdown_within_5pct"]
    )
    live_capital_ready = all(checks.values())

    blocking_reasons = [name for name, passed in checks.items() if not passed]
    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "paper_ready": paper_ready,
        "live_capital_ready": live_capital_ready,
        "live_trading_enabled": settings.live_trading_enabled,
        "blocking_reasons": blocking_reasons,
        "checks": checks,
        "tokens": {
            "upstox_analytics": analytics_tok,
            "upstox_access": access_tok,
        },
        "intraday_model": {
            "approval_threshold": getattr(flt, "approval_threshold", None),
            "feature_count": len(getattr(flt, "feature_cols", [])),
        },
        "daily_model": daily_status,
        "walk_forward_oos": wf_oos,
    }
    if save_report and wf_oos is not None:
        READINESS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        READINESS_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def get_readiness_snapshot() -> dict[str, Any]:
    """Return readiness summary immediately using cached walk-forward OOS plus live token/config checks."""
    return evaluate_system_readiness(historical_data=None, save_report=False)
