"""Long-only 15-trading-day NSE delivery swing alpha engine (purged multi-fold + blind holdout validated)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).parent.parent / "data"
DAILY_CACHE_PATH = DATA_DIR / "historical_candles_upstox_daily.json"
SWING_MODEL_PATH = DATA_DIR / "swing_15d_candidate.joblib"
SWING_REPORT_PATH = DATA_DIR / "swing_15d_report.json"

SWING_SCHEMA_VERSION = 3
SWING_HORIZON_SESSIONS = 15
SWING_REBALANCE_STEP = 5  # Weekly staggered tranches (3 concurrent tranches)
SWING_MAX_POSITIONS = 5
SWING_MAX_PER_SECTOR = 2
SWING_TOTAL_ALLOCATION_PCT = 50.0
SWING_DELIVERY_RT_COST_PCT = 0.32  # Delivery STT + brokerage + stamp/exchange/GST + slippage
SWING_RIDGE_ALPHA = 500.0
SWING_TARGET_CLIP_PCT = 25.0
SWING_PURGE_SESSIONS = 17  # Strictly >= H + 2 so zero target overlap across train/OOS
SWING_HOLDOUT_SESSIONS = 250


class _QuantileWinsorizer(BaseEstimator, TransformerMixin):
    """Clip numerical feature extremes to training-only [low_q, high_q] bounds."""

    def __init__(self, low_q: float = 0.01, high_q: float = 0.99) -> None:
        self.low_q = low_q
        self.high_q = high_q

    def fit(self, X, y=None):
        arr = np.asarray(X, dtype=float)
        self.lower_bounds_ = np.nanquantile(arr, self.low_q, axis=0)
        self.upper_bounds_ = np.nanquantile(arr, self.high_q, axis=0)
        return self

    def transform(self, X):
        arr = np.asarray(X, dtype=float)
        return np.clip(arr, self.lower_bounds_, self.upper_bounds_)

SWING_FEATURE_COLUMNS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "ret_10",
    "ret_20",
    "ret_60",
    "ret_120",
    "vol_20",
    "vol_60",
    "sharpe_20",
    "sharpe_60",
    "pos_frac_20",
    "sma20_dist",
    "sma50_dist",
    "sma200_dist",
    "dist_20_high",
    "dist_60_high",
    "vol_ratio",
    "rsi14",
    "rsi2",
    "gap_pct",
    "mkt_ret_1",
    "mkt_ret_5",
    "mkt_ret_20",
    "mkt_ret_60",
    "mkt_above_sma50",
    "mkt_above_sma200",
    "mkt_vol_20",
    # Note: excess_5, excess_20, excess_60 removed (collinear with ret_* - mkt_ret_*)
    # Dev-fold ablation confirms 28-orthogonal-feature Ridge(α=500) is superior.
]

logger = logging.getLogger(__name__)


def bootstrap_mean_ci(
    values: list[float] | np.ndarray,
    iterations: int = 2000,
    decimals: int = 2,
) -> list[float] | None:
    """Compute a deterministic percentile bootstrap 95% CI for sample mean."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 2:
        return None
    rng = np.random.default_rng(42)
    means = np.empty(iterations, dtype=float)
    for idx in range(iterations):
        means[idx] = rng.choice(arr, size=len(arr), replace=True).mean()
    low, high = np.percentile(means, [2.5, 97.5])
    return [round(float(low), decimals), round(float(high), decimals)]


def _compute_rsi(close: pd.Series, window: int) -> pd.Series:
    """Compute Wilder-style SMA RSI while guarding zero-loss/zero-gain edge cases."""
    delta = close.diff()
    gain = delta.clip(lower=0.0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0.0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.mask((loss == 0.0) & (gain > 0.0), 100.0)
    rsi = rsi.mask((gain == 0.0) & (loss > 0.0), 0.0)
    rsi = rsi.mask((gain == 0.0) & (loss == 0.0), 50.0)
    return rsi


def _normalize_daily_candles(candles: list[dict[str, Any]]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles).copy()
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame()
    df["_raw_ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["dt"] = df["_raw_ts"].dt.tz_convert("Asia/Kolkata").dt.normalize()
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["dt", "open", "high", "low", "close", "volume"])
    valid = (df[["open", "high", "low", "close"]] > 0).all(axis=1) & (df["volume"] >= 0)
    return (
        df.loc[valid]
        .sort_values("_raw_ts")
        .drop_duplicates("dt", keep="last")
        .sort_values("dt")
        .drop(columns="_raw_ts")
        .reset_index(drop=True)
    )


def _market_context_frame(candles: list[dict[str, Any]]) -> pd.DataFrame:
    df = _normalize_daily_candles(candles)
    if len(df) < 200:
        return pd.DataFrame()
    cs = df["close"].astype(float)
    df["mkt_ret_1"] = cs.pct_change(1) * 100.0
    df["mkt_ret_5"] = cs.pct_change(5) * 100.0
    df["mkt_ret_20"] = cs.pct_change(20) * 100.0
    df["mkt_ret_60"] = cs.pct_change(60) * 100.0
    df["mkt_sma50"] = cs.rolling(50).mean()
    df["mkt_sma200"] = cs.rolling(200).mean()
    df["mkt_above_sma50"] = (cs > df["mkt_sma50"]).astype(float)
    df["mkt_above_sma200"] = (cs > df["mkt_sma200"]).astype(float)
    df["mkt_vol_20"] = cs.pct_change().rolling(20).std() * 100.0 * np.sqrt(252)
    return df[
        [
            "dt",
            "mkt_ret_1",
            "mkt_ret_5",
            "mkt_ret_20",
            "mkt_ret_60",
            "mkt_above_sma50",
            "mkt_above_sma200",
            "mkt_vol_20",
        ]
    ]


def build_swing_panel(
    historical_data: dict[str, list[dict[str, Any]]],
    include_targets: bool = True,
) -> pd.DataFrame:
    """Build causal 31-feature cross-sectional panel (with optional 15d next-open target)."""
    from trading.bot_engine import SYMBOL_SECTORS

    mkt_candles = historical_data.get("NIFTY50") or []
    nifty = _market_context_frame(mkt_candles)
    if nifty.empty:
        raise ValueError("NIFTY50 daily market context (>=200 sessions) is required for swing features.")

    frames: list[pd.DataFrame] = []
    for sym, candles in historical_data.items():
        sym_u = sym.upper()
        if sym_u == "NIFTY50":
            continue
        df = _normalize_daily_candles(candles)
        if len(df) < 220:
            continue

        cs = df["close"].astype(float)
        os_ = df["open"].astype(float)
        vs = df["volume"].astype(float)

        df["ret_1"] = cs.pct_change(1) * 100.0
        df["ret_3"] = cs.pct_change(3) * 100.0
        df["ret_5"] = cs.pct_change(5) * 100.0
        df["ret_10"] = cs.pct_change(10) * 100.0
        df["ret_20"] = cs.pct_change(20) * 100.0
        df["ret_60"] = cs.pct_change(60) * 100.0
        df["ret_120"] = cs.pct_change(120) * 100.0
        df["vol_20"] = cs.pct_change().rolling(20).std() * 100.0
        df["vol_60"] = cs.pct_change().rolling(60).std() * 100.0
        df["sharpe_20"] = df["ret_20"] / df["vol_20"].replace(0.0, np.nan)
        df["sharpe_60"] = df["ret_60"] / df["vol_60"].replace(0.0, np.nan)
        df["pos_frac_20"] = (cs.pct_change(1) > 0).rolling(20).mean()
        df["sma20_dist"] = (cs / cs.rolling(20).mean() - 1.0) * 100.0
        df["sma50_dist"] = (cs / cs.rolling(50).mean() - 1.0) * 100.0
        df["sma200_dist"] = (cs / cs.rolling(200).mean() - 1.0) * 100.0
        df["dist_20_high"] = (cs / cs.rolling(20).max() - 1.0) * 100.0
        df["dist_60_high"] = (cs / cs.rolling(60).max() - 1.0) * 100.0
        df["vol_ratio"] = vs / vs.rolling(20).mean().replace(0.0, np.nan)

        df["rsi14"] = _compute_rsi(cs, 14)
        df["rsi2"] = _compute_rsi(cs, 2)
        df["gap_pct"] = (os_ / cs.shift(1) - 1.0) * 100.0

        df["symbol"] = sym_u
        # Keep unmapped custom symbols isolated so unrelated stocks do not collapse into one 2-slot bucket.
        df["sector"] = SYMBOL_SECTORS.get(sym_u, f"UNMAPPED:{sym_u}")
        if include_targets:
            entry_open = os_.shift(-1)
            exit_close = cs.shift(-SWING_HORIZON_SESSIONS)
            df["fwd_15d"] = (exit_close / entry_open - 1.0) * 100.0

        df = df.merge(nifty, on="dt", how="left")
        df["excess_5"] = df["ret_5"] - df["mkt_ret_5"]
        df["excess_20"] = df["ret_20"] - df["mkt_ret_20"]
        df["excess_60"] = df["ret_60"] - df["mkt_ret_60"]
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["dt", "symbol"]).reset_index(drop=True)


def _make_swing_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("winsor", _QuantileWinsorizer(0.01, 0.99)),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=SWING_RIDGE_ALPHA)),
        ]
    )


def _fit_swing_model(frame: pd.DataFrame) -> Pipeline:
    y_winsorized = frame["fwd_15d"].clip(-SWING_TARGET_CLIP_PCT, SWING_TARGET_CLIP_PCT)
    return _make_swing_pipeline().fit(frame[SWING_FEATURE_COLUMNS], y_winsorized)


def _simulate_swing_partition_all_offsets(
    scored_df: pd.DataFrame,
    initial_capital: float = 50_000.0,
    equal_weight_benchmark: bool = False,
) -> dict[str, Any]:
    """Evaluate weekly-staggered 15d CNC delivery across all 5 weekday offsets."""
    n_tranches = SWING_HORIZON_SESSIONS // SWING_REBALANCE_STEP
    slot_cap = len(scored_df["symbol"].unique()) if equal_weight_benchmark else SWING_MAX_POSITIONS
    slot_pct = (SWING_TOTAL_ALLOCATION_PCT / max(slot_cap, 1)) / max(n_tranches, 1)

    date_map: dict[pd.Timestamp, tuple[np.ndarray, np.ndarray, np.ndarray, float]] = {}
    daily_ics: list[float] = []
    for dt_val, grp in scored_df.groupby("dt"):
        ic = grp["pred_15d"].rank().corr(grp["fwd_15d"].rank())
        if pd.notna(ic):
            daily_ics.append(float(ic))
        ordered = grp.sort_values("pred_15d", ascending=False)
        date_map[pd.Timestamp(dt_val)] = (
            ordered["pred_15d"].to_numpy(float),
            ordered["fwd_15d"].to_numpy(float),
            ordered["sector"].to_numpy(str),
            float(ordered["fwd_15d"].mean()),
        )

    dates = sorted(date_map.keys())
    offset_pnls: list[float] = []
    offset_dd_pcts: list[float] = []
    offset_dds_inr: list[float] = []
    offset_pfs: list[float] = []
    offset_wrs: list[float] = []
    offset_trades: list[int] = []
    all_trade_pnls: list[float] = []
    all_excess_vs_univ: list[float] = []
    all_period_pnls: list[float] = []

    for off in range(SWING_REBALANCE_STEP):
        eq = float(initial_capital)
        peak = eq
        max_dd_inr = 0.0
        max_dd_pct = 0.0
        trade_pnls: list[float] = []

        for dt_val in dates[off::SWING_REBALANCE_STEP]:
            preds, rets, secs, univ_mean = date_map[dt_val]
            picked: list[int] = []
            sec_counts: dict[str, int] = {}
            for idx in range(len(preds)):
                if not equal_weight_benchmark and preds[idx] <= SWING_DELIVERY_RT_COST_PCT:
                    break
                sec = str(secs[idx])
                if not equal_weight_benchmark and sec_counts.get(sec, 0) >= SWING_MAX_PER_SECTOR:
                    continue
                picked.append(idx)
                sec_counts[sec] = sec_counts.get(sec, 0) + 1
                if len(picked) >= slot_cap:
                    break
            if not picked:
                continue

            alloc = eq * (slot_pct / 100.0)
            per_pnl = 0.0
            for idx in picked:
                tp = alloc * ((rets[idx] - SWING_DELIVERY_RT_COST_PCT) / 100.0)
                per_pnl += tp
                trade_pnls.append(tp)
            all_period_pnls.append(per_pnl)
            all_excess_vs_univ.append(float(np.mean([rets[i] for i in picked])) - univ_mean)

            eq += per_pnl
            peak = max(peak, eq)
            dd_inr = peak - eq
            max_dd_inr = max(max_dd_inr, dd_inr)
            if peak > 0:
                max_dd_pct = max(max_dd_pct, (dd_inr / peak) * 100.0)

        offset_pnls.append(eq - initial_capital)
        offset_dds_inr.append(max_dd_inr)
        offset_dd_pcts.append(max_dd_pct)
        offset_trades.append(len(trade_pnls))
        all_trade_pnls.extend(trade_pnls)
        gw = sum(x for x in trade_pnls if x > 0)
        gl = abs(sum(x for x in trade_pnls if x <= 0))
        offset_pfs.append(gw / gl if gl > 0 else (gw if gw > 0 else 0.0))
        offset_wrs.append((sum(1 for x in trade_pnls if x > 0) / len(trade_pnls) * 100.0) if trade_pnls else 0.0)

    return {
        "start": dates[0].isoformat() if dates else None,
        "end": dates[-1].isoformat() if dates else None,
        "scored_sessions": len(dates),
        "mean_daily_spearman_ic": round(float(np.mean(daily_ics)), 4) if daily_ics else 0.0,
        "mean_net_profit": round(float(np.mean(offset_pnls)), 2) if offset_pnls else 0.0,
        "min_offset_net_profit": round(float(np.min(offset_pnls)), 2) if offset_pnls else 0.0,
        "max_offset_net_profit": round(float(np.max(offset_pnls)), 2) if offset_pnls else 0.0,
        "mean_win_rate_pct": round(float(np.mean(offset_wrs)), 2) if offset_wrs else 0.0,
        "mean_profit_factor": round(float(np.mean(offset_pfs)), 2) if offset_pfs else 0.0,
        "worst_offset_max_drawdown": round(float(np.max(offset_dds_inr)), 2) if offset_dds_inr else 0.0,
        "worst_offset_max_drawdown_pct": round(float(np.max(offset_dd_pcts)), 2) if offset_dd_pcts else 0.0,
        "mean_trades_per_offset": round(float(np.mean(offset_trades)), 1) if offset_trades else 0.0,
        "mean_excess_alpha_pct": round(float(np.mean(all_excess_vs_univ)), 3) if all_excess_vs_univ else 0.0,
        "excess_alpha_95pct_ci_pct": bootstrap_mean_ci(all_excess_vs_univ, decimals=3),
        "period_pnl_95pct_ci": bootstrap_mean_ci(all_period_pnls, decimals=2),
        "_period_pnls": all_period_pnls,
        "_excess_alpha": all_excess_vs_univ,
        "_trade_pnls": all_trade_pnls,
    }


def train_and_evaluate_swing_alpha(
    historical_data: dict[str, list[dict[str, Any]]],
    initial_capital: float = 50_000.0,
    holdout_sessions: int = SWING_HOLDOUT_SESSIONS,
    save_artifacts: bool = True,
    extra_training_data: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Train and evaluate the 15-day CNC Ridge Swing model across 5 purged dev folds + blind holdout."""
    panel = build_swing_panel(historical_data, include_targets=True)
    clean = panel.dropna(subset=[*SWING_FEATURE_COLUMNS, "fwd_15d"]).copy()
    extra_clean: pd.DataFrame | None = None
    if extra_training_data:
        extra_panel = build_swing_panel(extra_training_data, include_targets=True)
        extra_subset = extra_panel.dropna(subset=[*SWING_FEATURE_COLUMNS, "fwd_15d"]).copy()
        eval_syms = set(clean["symbol"].unique())
        extra_subset = extra_subset[~extra_subset["symbol"].isin(eval_syms)]
        if not extra_subset.empty:
            extra_clean = extra_subset
    all_dates = sorted(clean["dt"].unique())
    if len(all_dates) < holdout_sessions + 600:
        raise ValueError(f"Insufficient daily sessions ({len(all_dates)}) for purged 5-fold + {holdout_sessions}-day holdout.")

    holdout_start = all_dates[-holdout_sessions]
    holdout_train_cutoff = all_dates[-holdout_sessions - SWING_PURGE_SESSIONS]
    dev_dates = all_dates[:-holdout_sessions]
    usable_dev_dates = [d for d in dev_dates if d >= dev_dates[500]]
    fold_buckets = np.array_split(usable_dev_dates, 5)

    dev_folds: list[dict[str, Any]] = []
    pooled_excess: list[float] = []
    pooled_periods: list[float] = []
    pooled_trades: list[float] = []
    all_ics: list[float] = []

    def _purged_train_slice(cutoff) -> pd.DataFrame:
        base_tr = clean[clean["dt"] <= cutoff]
        if extra_clean is None:
            return base_tr
        return pd.concat([base_tr, extra_clean[extra_clean["dt"] <= cutoff]], ignore_index=True)

    for idx, bucket in enumerate(fold_buckets, start=1):
        oos_start, oos_end = bucket[0], bucket[-1]
        oos_idx = dev_dates.index(oos_start)
        tr_cutoff = dev_dates[max(0, oos_idx - SWING_PURGE_SESSIONS)]
        tr = _purged_train_slice(tr_cutoff)
        oos = clean[(clean["dt"] >= oos_start) & (clean["dt"] <= oos_end)].copy()
        model = _fit_swing_model(tr)
        oos["pred_15d"] = model.predict(oos[SWING_FEATURE_COLUMNS])

        fold_res = _simulate_swing_partition_all_offsets(oos, initial_capital=initial_capital)
        bench_res = _simulate_swing_partition_all_offsets(oos, initial_capital=initial_capital, equal_weight_benchmark=True)
        pooled_excess.extend(fold_res.pop("_excess_alpha"))
        pooled_periods.extend(fold_res.pop("_period_pnls"))
        pooled_trades.extend(fold_res.pop("_trade_pnls"))
        bench_res.pop("_excess_alpha", None)
        bench_res.pop("_period_pnls", None)
        bench_res.pop("_trade_pnls", None)
        all_ics.append(fold_res["mean_daily_spearman_ic"])
        fold_res["fold"] = f"dev_fold_{idx}"
        fold_res["benchmark_equal_weight_profit"] = bench_res["mean_net_profit"]
        dev_folds.append(fold_res)

    # Strict zero-leakage blind holdout evaluation
    ho_train = _purged_train_slice(holdout_train_cutoff)
    ho_test = clean[clean["dt"] >= holdout_start].copy()
    ho_model = _fit_swing_model(ho_train)
    ho_test["pred_15d"] = ho_model.predict(ho_test[SWING_FEATURE_COLUMNS])
    holdout_res = _simulate_swing_partition_all_offsets(ho_test, initial_capital=initial_capital)
    holdout_bench = _simulate_swing_partition_all_offsets(ho_test, initial_capital=initial_capital, equal_weight_benchmark=True)

    pooled_excess.extend(holdout_res.pop("_excess_alpha"))
    pooled_periods.extend(holdout_res.pop("_period_pnls"))
    pooled_trades.extend(holdout_res.pop("_trade_pnls"))
    holdout_bench.pop("_excess_alpha", None)
    holdout_bench.pop("_period_pnls", None)
    holdout_bench.pop("_trade_pnls", None)
    holdout_res["benchmark_equal_weight_profit"] = holdout_bench["mean_net_profit"]

    # Fit production artifact on full labeled dataset
    full_train = pd.concat([clean, extra_clean], ignore_index=True) if extra_clean is not None else clean
    final_model = _fit_swing_model(full_train)
    coefs = {
        col: round(float(val), 4)
        for col, val in sorted(
            zip(SWING_FEATURE_COLUMNS, final_model.named_steps["ridge"].coef_),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )
    }

    combined_net = round(sum(f["mean_net_profit"] for f in dev_folds) + holdout_res["mean_net_profit"], 2)
    combined_bench = round(
        sum(f["benchmark_equal_weight_profit"] for f in dev_folds) + holdout_bench["mean_net_profit"], 2
    )
    gw = sum(x for x in pooled_trades if x > 0)
    gl = abs(sum(x for x in pooled_trades if x <= 0))
    combined_pf = round(gw / gl, 2) if gl > 0 else round(gw, 2)
    excess_ci = bootstrap_mean_ci(pooled_excess, decimals=3)
    period_ci = bootstrap_mean_ci(pooled_periods, decimals=2)

    all_fold_profits = [f["mean_net_profit"] for f in dev_folds] + [holdout_res["mean_net_profit"]]
    worst_dd_pct = round(
        max([f["worst_offset_max_drawdown_pct"] for f in dev_folds] + [holdout_res["worst_offset_max_drawdown_pct"]]),
        2,
    )

    gates = {
        "combined_oos_net_profit_positive": bool(combined_net > 0),
        "combined_oos_profit_factor_ge_1_25": bool(combined_pf >= 1.25),
        "combined_excess_alpha_95pct_ci_positive": bool(excess_ci and excess_ci[0] > 0),
        "combined_period_pnl_95pct_ci_positive": bool(period_ci and period_ci[0] > 0),
        "blind_holdout_net_profit_positive": bool(holdout_res["mean_net_profit"] > 0),
        "blind_holdout_all_offsets_profitable": bool(holdout_res["min_offset_net_profit"] > 0),
        "blind_holdout_excess_alpha_ci_positive": bool(
            holdout_res["excess_alpha_95pct_ci_pct"] and holdout_res["excess_alpha_95pct_ci_pct"][0] > 0
        ),
        "blind_holdout_max_dd_within_10pct": bool(holdout_res["worst_offset_max_drawdown_pct"] <= 10.0),
    }

    latest_dt = panel["dt"].max()
    report = {
        "schema_version": SWING_SCHEMA_VERSION,
        "architecture": "long_only_15d_cnc_ridge_staggered_5d",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_through": latest_dt.isoformat() if pd.notna(latest_dt) else None,
        "labeled_samples": int(len(clean)),
        "symbols_count": int(clean["symbol"].nunique()),
        "strategy_rules": {
            "holding_horizon_sessions": SWING_HORIZON_SESSIONS,
            "rebalance_step_sessions": SWING_REBALANCE_STEP,
            "max_positions_per_tranche": SWING_MAX_POSITIONS,
            "max_per_sector": SWING_MAX_PER_SECTOR,
            "total_deployed_pct": SWING_TOTAL_ALLOCATION_PCT,
            "delivery_round_trip_cost_pct": SWING_DELIVERY_RT_COST_PCT,
            "product": "D",
        },
        "swing_oos_ready": bool(all(gates.values())),
        "gates": gates,
        "summary": {
            "folds_evaluated": len(dev_folds) + 1,
            "folds_profitable": int(sum(1 for p in all_fold_profits if p > 0)),
            "combined_net_profit": combined_net,
            "combined_benchmark_profit": combined_bench,
            "combined_outperformance_vs_benchmark": round(float(combined_net - combined_bench), 2),
            "combined_profit_factor": combined_pf,
            "worst_fold_max_drawdown_pct": worst_dd_pct,
            "mean_daily_spearman_ic": round(float(np.mean([*all_ics, holdout_res["mean_daily_spearman_ic"]])), 4),
            "combined_excess_alpha_95pct_ci_pct": excess_ci,
            "combined_period_pnl_95pct_ci": period_ci,
        },
        "dev_folds": dev_folds,
        "blind_holdout": holdout_res,
        "top_ridge_coefficients": coefs,
    }

    if save_artifacts:
        SWING_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_model = SWING_MODEL_PATH.with_suffix(".joblib.tmp")
        tmp_report = SWING_REPORT_PATH.with_suffix(".json.tmp")
        joblib.dump(
            {
                "model": final_model,
                "schema_version": SWING_SCHEMA_VERSION,
                "feature_cols": SWING_FEATURE_COLUMNS,
                "generated_at": report["generated_at"],
                "data_through": report["data_through"],
            },
            tmp_model,
        )
        tmp_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        tmp_model.replace(SWING_MODEL_PATH)
        tmp_report.replace(SWING_REPORT_PATH)

    return report


def get_swing_status() -> dict[str, Any]:
    """Return persisted 15-day swing model OOS readiness summary."""
    if not SWING_MODEL_PATH.is_file() or not SWING_REPORT_PATH.is_file():
        return {"state": "not_trained", "swing_oos_ready": False}
    try:
        report = json.loads(SWING_REPORT_PATH.read_text(encoding="utf-8"))
        return {
            "state": "validated_oos" if report.get("swing_oos_ready") else "research_only",
            "swing_oos_ready": bool(report.get("swing_oos_ready", False)),
            "schema_version": report.get("schema_version"),
            "architecture": report.get("architecture"),
            "data_through": report.get("data_through"),
            "symbols_count": report.get("symbols_count"),
            "strategy_rules": report.get("strategy_rules"),
            "summary": report.get("summary"),
            "dev_folds": report.get("dev_folds", []),
            "blind_holdout": report.get("blind_holdout"),
            "gates": report.get("gates"),
            "top_ridge_coefficients": report.get("top_ridge_coefficients", {}),
        }
    except Exception as exc:
        logger.warning("Failed to load swing status: %s", exc)
        return {"state": "unavailable", "swing_oos_ready": False}


def score_latest_swing_universe(
    historical_data: dict[str, list[dict[str, Any]]] | None = None,
    capital: float = 50_000.0,
) -> dict[str, Any]:
    """Score the NIFTY-50 universe for today's 15-day CNC swing rebalance tranche."""
    from trading.bot_engine import SYMBOL_SECTORS

    if not SWING_MODEL_PATH.is_file():
        return {"status": "not_trained", "recommendations": [], "all_ranked": []}

    data_source = "provided"
    if historical_data is None:
        if not DAILY_CACHE_PATH.is_file():
            return {"status": "no_daily_cache", "recommendations": [], "all_ranked": []}
        historical_data = json.loads(DAILY_CACHE_PATH.read_text(encoding="utf-8"))
        data_source = "cached_upstox_daily"

    bundle = joblib.load(SWING_MODEL_PATH)
    model = bundle["model"]
    feat_cols = bundle["feature_cols"]
    panel = build_swing_panel(historical_data, include_targets=False)
    latest_rows = (
        panel.dropna(subset=feat_cols)
        .sort_values("dt")
        .groupby("symbol", as_index=False)
        .tail(1)
        .copy()
    )
    if latest_rows.empty:
        return {"status": "insufficient_history", "recommendations": [], "all_ranked": []}

    # Keep only symbols on the latest session date
    latest_dt = latest_rows["dt"].max()
    latest_rows = latest_rows[latest_rows["dt"] == latest_dt].copy()
    latest_rows["pred_15d"] = model.predict(latest_rows[feat_cols])
    latest_rows = latest_rows.sort_values("pred_15d", ascending=False).reset_index(drop=True)

    n_tranches = SWING_HORIZON_SESSIONS // SWING_REBALANCE_STEP
    tranche_slot_pct = (SWING_TOTAL_ALLOCATION_PCT / SWING_MAX_POSITIONS) / max(n_tranches, 1)
    tranche_budget = capital * (tranche_slot_pct / 100.0)

    recommendations: list[dict[str, Any]] = []
    all_ranked: list[dict[str, Any]] = []
    sec_counts: dict[str, int] = {}

    for rank_idx, row in latest_rows.iterrows():
        sym = str(row["symbol"])
        pred_pct = round(float(row["pred_15d"]), 3)
        close_px = round(float(row["close"]), 2)
        sector = str(row["sector"])
        net_after_cost = round(pred_pct - SWING_DELIVERY_RT_COST_PCT, 3)

        entry = {
            "rank": rank_idx + 1,
            "symbol": sym,
            "sector": sector,
            "direction": "LONG" if pred_pct > SWING_DELIVERY_RT_COST_PCT else "NO_TRADE",
            "product": "D",
            "horizon_sessions": SWING_HORIZON_SESSIONS,
            "last_close": close_px,
            "predicted_15d_gross_pct": pred_pct,
            "predicted_15d_net_pct": net_after_cost,
            "rsi14": round(float(row["rsi14"]), 1),
            "sharpe_20": round(float(row["sharpe_20"]), 2),
            "sma200_dist_pct": round(float(row["sma200_dist"]), 2),
            "ret_20": round(float(row["ret_20"]), 2),
            "dist_20_high_pct": round(float(row["dist_20_high"]), 2),
            "dist_60_high_pct": round(float(row["dist_60_high"]), 2),
        }
        all_ranked.append(entry)

        if (
            pred_pct > SWING_DELIVERY_RT_COST_PCT
            and sec_counts.get(sector, 0) < SWING_MAX_PER_SECTOR
            and len(recommendations) < SWING_MAX_POSITIONS
        ):
            qty = int(tranche_budget / close_px) if close_px > 0 else 0
            # NSE equities require >= 1 integer share; allow 1 share when it still respects the 10% single-name cap.
            if qty == 0 and 0 < close_px <= capital * 0.10:
                qty = 1
            recommendations.append(
                {
                    **entry,
                    "suggested_tranche_pct": round(tranche_slot_pct, 2),
                    "suggested_budget_inr": round(tranche_budget, 2),
                    "suggested_qty": qty,
                }
            )
            sec_counts[sector] = sec_counts.get(sector, 0) + 1

    stale_days = max(0, int((datetime.now(timezone.utc).date() - latest_dt.date()).days))
    return {
        "status": "ok",
        "data_source": data_source,
        "as_of": latest_dt.isoformat(),
        "stale_days": stale_days,
        "nifty_above_sma200": bool(float(latest_rows["mkt_above_sma200"].iloc[0]) >= 0.5),
        "nifty_above_sma50": bool(float(latest_rows["mkt_above_sma50"].iloc[0]) >= 0.5),
        "capital": float(capital),
        "tranche_slot_pct": round(tranche_slot_pct, 2),
        "recommendations": recommendations,
        "all_ranked": all_ranked,
    }


# ── Prospective 15-Day CNC Paper Ledger ─────────────────────────────────────

SWING_PAPER_LEDGER_PATH = DATA_DIR / "swing_paper_ledger.json"


def _load_ledger() -> dict:
    """Load the persistent swing paper ledger from disk."""
    if SWING_PAPER_LEDGER_PATH.exists():
        try:
            return json.loads(SWING_PAPER_LEDGER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"schema_version": 1, "tranches": []}


def _save_ledger(ledger: dict) -> None:
    """Atomically write the ledger to disk."""
    SWING_PAPER_LEDGER_PATH.write_text(
        json.dumps(ledger, indent=2, default=str), encoding="utf-8"
    )


def record_swing_paper_tranche(
    recommendations: list[dict],
    as_of: str,
    capital: float,
) -> dict:
    """
    Record a new 15-day swing tranche into the persistent paper ledger.

    Parameters
    ----------
    recommendations : Top-5 signals from score_latest_swing_universe()["recommendations"].
    as_of           : ISO date string of the scan (entry date).
    capital         : Capital at time of scan (for sizing reference).

    Returns the newly appended tranche dict.
    """
    ledger = _load_ledger()
    tranche = {
        "tranche_id": f"swing_{as_of.replace('-', '')[:8]}_{len(ledger['tranches']):04d}",
        "entry_date": as_of,
        "capital_at_entry": float(capital),
        "status": "open",   # → "resolved" once exit prices are logged
        "positions": [],
        "summary": None,
    }
    for rec in recommendations[:SWING_MAX_POSITIONS]:
        tranche["positions"].append({
            "symbol": rec["symbol"],
            "sector": rec.get("sector", "UNKNOWN"),
            "entry_close": rec.get("last_close", 0.0),
            "predicted_15d_pct": rec.get("predicted_15d_net_pct", 0.0),
            "suggested_qty": rec.get("suggested_qty", 0),
            "suggested_budget_inr": rec.get("suggested_budget_inr", 0.0),
            "exit_close": None,
            "realized_pct": None,
            "realized_pnl_inr": None,
            "result": None,   # "win" | "loss" | "breakeven"
        })
    ledger["tranches"].append(tranche)
    _save_ledger(ledger)
    logger.info("Recorded swing paper tranche %s (%d positions).", tranche["tranche_id"], len(tranche["positions"]))
    return tranche


def resolve_swing_paper_tranche(tranche_id: str, exit_prices: dict[str, float]) -> dict:
    """
    Mark positions in a tranche as resolved with their exit close prices.

    Parameters
    ----------
    tranche_id   : ID of the tranche to resolve (from ledger).
    exit_prices  : {symbol: exit_close_price} mapping for each held position.

    Returns the resolved tranche dict (with summary PnL/WR/PF).
    """
    ledger = _load_ledger()
    tranche = next((t for t in ledger["tranches"] if t["tranche_id"] == tranche_id), None)
    if tranche is None:
        raise ValueError(f"Tranche '{tranche_id}' not found in ledger.")

    wins, gross_win, gross_loss = 0, 0.0, 0.0
    for pos in tranche["positions"]:
        sym = pos["symbol"]
        if sym not in exit_prices:
            continue
        ep = float(exit_prices[sym])
        entry = float(pos["entry_close"]) if pos["entry_close"] else 0.0
        qty = int(pos["suggested_qty"] or 0)
        budget = float(pos["suggested_budget_inr"] or 0.0)
        if entry <= 0 or qty <= 0:
            pos["result"] = "skip"
            continue
        raw_pct = (ep - entry) / entry * 100.0
        net_pct = raw_pct - SWING_DELIVERY_RT_COST_PCT
        pnl = budget * net_pct / 100.0
        pos["exit_close"] = round(ep, 4)
        pos["realized_pct"] = round(net_pct, 4)
        pos["realized_pnl_inr"] = round(pnl, 2)
        if net_pct > 0:
            wins += 1
            gross_win += pnl
            pos["result"] = "win"
        elif net_pct < 0:
            gross_loss += abs(pnl)
            pos["result"] = "loss"
        else:
            pos["result"] = "breakeven"

    total_resolved = sum(1 for p in tranche["positions"] if p.get("result") not in (None, "skip"))
    pf = gross_win / gross_loss if gross_loss > 0 else 0.0
    wr = wins / total_resolved * 100.0 if total_resolved > 0 else 0.0
    net_pnl = gross_win - gross_loss

    tranche["status"] = "resolved"
    tranche["summary"] = {
        "positions_resolved": total_resolved,
        "wins": wins,
        "win_rate_pct": round(wr, 2),
        "gross_win_inr": round(gross_win, 2),
        "gross_loss_inr": round(gross_loss, 2),
        "net_pnl_inr": round(net_pnl, 2),
        "profit_factor": round(pf, 3),
    }
    _save_ledger(ledger)
    logger.info("Resolved tranche %s: WR=%.1f%% PF=%.2f Net=%.2f", tranche_id, wr, pf, net_pnl)
    return tranche


def get_swing_paper_ledger_stats() -> dict:
    """
    Aggregate lifetime stats across all resolved tranches: WR, PF, net PnL.
    Returns the full ledger with a top-level aggregated summary.
    """
    ledger = _load_ledger()
    total_trades, wins = 0, 0
    gross_win, gross_loss = 0.0, 0.0
    resolved_tranches = 0

    for t in ledger["tranches"]:
        s = t.get("summary")
        if not s:
            continue
        resolved_tranches += 1
        total_trades += s.get("positions_resolved", 0)
        wins += s.get("wins", 0)
        gross_win += s.get("gross_win_inr", 0.0)
        gross_loss += s.get("gross_loss_inr", 0.0)

    pf = gross_win / gross_loss if gross_loss > 0 else 0.0
    wr = wins / total_trades * 100.0 if total_trades > 0 else 0.0
    net = gross_win - gross_loss

    return {
        "ledger": ledger,
        "aggregate": {
            "open_tranches": sum(1 for t in ledger["tranches"] if t["status"] == "open"),
            "resolved_tranches": resolved_tranches,
            "total_positions_resolved": total_trades,
            "win_rate_pct": round(wr, 2),
            "profit_factor": round(pf, 3),
            "net_pnl_inr": round(net, 2),
            "gross_win_inr": round(gross_win, 2),
            "gross_loss_inr": round(gross_loss, 2),
        },
    }
