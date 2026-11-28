import asyncio
import json
import os
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from backtesting.historical_fetcher import fetch_historical_data
from backtesting.engine import run_backtest
from backtesting.engine import _compute_features_for_df
from intelligence.ml_filter import MLQualityFilter


def build_triple_barrier_dataset(
    historical_data,
    horizon_bars: int = 15,
    take_profit_atr: float = 2.5,
    stop_loss_atr: float = 1.5,
) -> pd.DataFrame:
    """Create vectorized AFML-style labels using profit, stop, and time barriers."""
    round_trip_cost_pct = 0.15
    feature_cols = [
        "timestamp", "rsi", "rsi_delta", "ema9", "ema21", "vwap", "atr14",
        "ema9_dist_pct", "ema21_dist_pct", "vwap_dist_pct",
        "vol_ratio", "momentum", "volatility", "trend_strength",
        "range_pct", "return_1", "return_5", "return_20",
        "frac_diff", "frac_diff_pct", "cusum_event", "body_pct", "hour_ist",
    ]
    parts = []

    for symbol, candles in historical_data.items():
        if not candles:
            continue
        frame = _compute_features_for_df(pd.DataFrame(candles).copy()).reset_index(drop=True)
        n = len(frame) - horizon_bars
        if n <= 0:
            continue

        close_arr = frame["close"].to_numpy(dtype=float)[:n]
        atr_raw = frame["atr14"].to_numpy(dtype=float)[:n]
        high_arr = frame["high"].to_numpy(dtype=float)
        low_arr = frame["low"].to_numpy(dtype=float)

        atr = np.maximum(atr_raw, close_arr * 0.001)
        pt_distance = np.maximum(atr * take_profit_atr, close_arr * round_trip_cost_pct / 100.0)
        sl_distance = np.maximum(atr * stop_loss_atr, close_arr * 0.10 / 100.0)

        w_high = sliding_window_view(high_arr[1:], horizon_bars)[:n]
        w_low = sliding_window_view(low_arr[1:], horizon_bars)[:n]

        long_pt_hits = w_high >= (close_arr + pt_distance)[:, None]
        long_sl_hits = w_low <= (close_arr - sl_distance)[:, None]
        has_lpt = long_pt_hits.any(axis=1)
        has_lsl = long_sl_hits.any(axis=1)
        lpt_bar = np.where(has_lpt, long_pt_hits.argmax(axis=1), horizon_bars + 1)
        lsl_bar = np.where(has_lsl, long_sl_hits.argmax(axis=1), horizon_bars + 1)
        long_target = (has_lpt & (lpt_bar < lsl_bar)).astype(int)

        short_pt_hits = w_low <= (close_arr - pt_distance)[:, None]
        short_sl_hits = w_high >= (close_arr + sl_distance)[:, None]
        has_spt = short_pt_hits.any(axis=1)
        has_ssl = short_sl_hits.any(axis=1)
        spt_bar = np.where(has_spt, short_pt_hits.argmax(axis=1), horizon_bars + 1)
        ssl_bar = np.where(has_ssl, short_sl_hits.argmax(axis=1), horizon_bars + 1)
        short_target = (has_spt & (spt_bar < ssl_bar)).astype(int)

        base = frame.iloc[:n].reindex(columns=feature_cols).copy()
        if "cusum_event" in base:
            base["cusum_event"] = base["cusum_event"].fillna(0.0)
        base["symbol"] = symbol

        long_df = base.copy()
        long_df["direction"] = 1.0
        long_df["target"] = long_target
        short_df = base.copy()
        short_df["direction"] = -1.0
        short_df["target"] = short_target

        parts.append(long_df)
        parts.append(short_df)

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(["symbol", "timestamp", "direction"]).reset_index(drop=True)

async def main():
    print("=" * 50)
    print("  PHASE 2A: TRAINING MACHINE LEARNING FILTER")
    print("=" * 50)
    
    # 1. Select the research corpus explicitly. Yahoo is historical-only;
    # Upstox remains the live/execution data source.
    source = os.environ.get("TRAINING_DATA_SOURCE", "upstox").lower()
    training_mode = os.environ.get("ML_TRAINING_MODE", "standard").lower()
    days_back = int(os.environ.get("TRAINING_DAYS_BACK", "180"))
    model = MLQualityFilter(
        model_prefix=f"candidate_ml_model_ensemble_{source}"
    )
    print("\n[INFO] Saving as CANDIDATE model. Production model remains frozen.")
    print("[INFO] To promote this model to production, rename the candidate files manually.")
    if source == "yahoo":
        from backtesting.yahoo_historical_fetcher import CACHE_FILE as YAHOO_CACHE_FILE

        if not YAHOO_CACHE_FILE.exists():
            from backtesting.yahoo_historical_fetcher import fetch_yahoo_daily_data
            data = fetch_yahoo_daily_data(years_back=10)
        else:
            data = json.loads(YAHOO_CACHE_FILE.read_text())
        print(f"[INFO] Using Yahoo historical-only corpus: {YAHOO_CACHE_FILE.name}")
    else:
        data = await fetch_historical_data(days_back=days_back)
        print(f"[INFO] Using Upstox historical candle corpus ({days_back} requested days).")
    
    df = None
    if source != "yahoo" and os.environ.get("ML_USE_TRADE_DATASET", "0") == "1":
        print("\n[INFO] Generating Dataset via Phase-1 Simulation...")
        p1_results = run_backtest(data, use_phase1=True)
        candidate_df = p1_results.get("ml_dataset")
        required_features = set(model.feature_cols + ["target"])
        if (
            candidate_df is not None
            and len(candidate_df) >= 2000
            and required_features.issubset(candidate_df.columns)
        ):
            df = candidate_df
            print(f"[OK] Generated dataset with {len(df)} samples.")
            print(f"Wins: {len(df[df['target'] == 1])}, Losses: {len(df[df['target'] == 0])}")

    if df is None:
        print("\n[INFO] Generating AFML Triple-Barrier Dataset...")
        df = build_triple_barrier_dataset(data)
        print(f"[OK] Generated triple-barrier dataset with {len(df)} samples.")
        print(f"Wins: {len(df[df['target'] == 1])}, Losses: {len(df[df['target'] == 0])}")

    # 3. Save dataset and Train ML Model
    if df is not None and not df.empty:
        dataset_path = Path(__file__).parent.parent / "data" / "triple_barrier_dataset_upstox.csv"
        df.to_csv(dataset_path, index=False)
        if not model.train_on_backtest_data(df, mode=training_mode):
            raise RuntimeError("ML training refused the dataset; inspect class balance and sample count.")
    else:
        raise RuntimeError("No usable training dataset was generated.")

if __name__ == "__main__":
    asyncio.run(main())
