import asyncio
import json
import os
import pandas as pd
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
    """Create AFML-style labels using profit, stop, and time barriers."""
    rows = []
    round_trip_cost_pct = 0.15

    for symbol, candles in historical_data.items():
        if not candles:
            continue
        frame = _compute_features_for_df(pd.DataFrame(candles).copy())
        frame = frame.reset_index(drop=True)
        if len(frame) <= horizon_bars:
            continue

        for index, row in frame.iloc[:-horizon_bars].iterrows():
            entry_price = float(row["close"])
            atr = max(float(row["atr14"]), entry_price * 0.001)
            pt_distance = max(atr * take_profit_atr, entry_price * round_trip_cost_pct / 100)
            sl_distance = max(atr * stop_loss_atr, entry_price * 0.10 / 100)
            future = frame.iloc[index + 1:index + 1 + horizon_bars]
            common = {
                "timestamp": row["timestamp"],
                "rsi": row.get("rsi"),
                "ema9": row.get("ema9"),
                "ema21": row.get("ema21"),
                "vwap": row.get("vwap"),
                "atr14": row.get("atr14"),
                "vol_ratio": row.get("vol_ratio"),
                "momentum": row.get("momentum"),
                "volatility": row.get("volatility"),
                "trend_strength": row.get("trend_strength"),
                "range_pct": row.get("range_pct"),
                "return_5": row.get("return_5"),
                "return_20": row.get("return_20"),
                "frac_diff": row.get("frac_diff"),
                "cusum_event": row.get("cusum_event", 0.0),
                "symbol": symbol,
            }

            long_pt = entry_price + pt_distance
            long_sl = entry_price - sl_distance
            long_pt_bar = next((bar for bar, (_, candle) in enumerate(future.iterrows()) if candle["high"] >= long_pt), None)
            long_sl_bar = next((bar for bar, (_, candle) in enumerate(future.iterrows()) if candle["low"] <= long_sl), None)
            long_target = int(long_pt_bar is not None and (long_sl_bar is None or long_pt_bar < long_sl_bar))

            short_pt = entry_price - pt_distance
            short_sl = entry_price + sl_distance
            short_pt_bar = next((bar for bar, (_, candle) in enumerate(future.iterrows()) if candle["low"] <= short_pt), None)
            short_sl_bar = next((bar for bar, (_, candle) in enumerate(future.iterrows()) if candle["high"] >= short_sl), None)
            short_target = int(short_pt_bar is not None and (short_sl_bar is None or short_pt_bar < short_sl_bar))

            rows.append({**common, "direction": 1.0, "target": long_target})
            rows.append({**common, "direction": -1.0, "target": short_target})

    return pd.DataFrame(rows)

async def main():
    print("=" * 50)
    print("  PHASE 2A: TRAINING MACHINE LEARNING FILTER")
    print("=" * 50)
    
    # 1. Select the research corpus explicitly. Yahoo is historical-only;
    # Upstox remains the live/execution data source.
    source = os.environ.get("TRAINING_DATA_SOURCE", "upstox").lower()
    training_mode = os.environ.get("ML_TRAINING_MODE", "aggressive").lower()
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
