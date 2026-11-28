import pandas as pd
import numpy as np
import copy
from typing import Dict, List, Any
import warnings

warnings.filterwarnings('ignore')

def inject_slippage_shock(historical_data: Dict[str, List[Dict]], multiplier: float = 3.0) -> Dict[str, List[Dict]]:
    """
    Simulates severe liquidity dry-ups by aggressively expanding the bid-ask spread
    and worsening the entry/exit prices.
    """
    shocked_data = copy.deepcopy(historical_data)
    for sym, candles in shocked_data.items():
        for candle in candles:
            # We assume a base spread of 0.05%, multiplied by the shock factor
            spread_shock = (candle['close'] * 0.0005) * multiplier
            candle['high'] -= spread_shock  # Worse for longs taking profit
            candle['low'] += spread_shock   # Worse for longs getting stopped out
    return shocked_data

def inject_packet_loss(historical_data: Dict[str, List[Dict]], drop_rate: float = 0.05) -> Dict[str, List[Dict]]:
    """
    Randomly drops candles to simulate API disconnects and websocket failures.
    Tests if the feature engine explodes with NaNs or handles missing data gracefully.
    """
    shocked_data = {}
    np.random.seed(42) # Deterministic chaos
    for sym, candles in historical_data.items():
        surviving_candles = []
        for candle in candles:
            if np.random.random() > drop_rate:
                surviving_candles.append(candle)
        shocked_data[sym] = surviving_candles
    return shocked_data

def run_adversarial_audit(historical_data: Dict[str, List[Dict]], engine_func):
    """
    Runs the strategy through the Adversarial Crucible.
    """
    print("=" * 60)
    print(" 🛡️ STARTING ADVERSARIAL AUDIT")
    print("=" * 60)
    
    print("\n[1] Running Baseline (No Shocks)...")
    baseline = engine_func(historical_data, use_phase1=True, use_ml_filter=True)
    baseline_pnl = baseline.get('net_profit', 0)
    baseline_winrate = baseline.get('win_rate_pct', 0)
    print(f"    Net Profit: {baseline_pnl} | Win Rate: {baseline_winrate}%")
    
    print("\n[2] Injecting 3x Slippage Shock (Liquidity Crisis)...")
    slippage_data = inject_slippage_shock(historical_data, multiplier=3.0)
    slippage_result = engine_func(slippage_data, use_phase1=True, use_ml_filter=True)
    slip_pnl = slippage_result.get('net_profit', 0)
    slip_winrate = slippage_result.get('win_rate_pct', 0)
    print(f"    Net Profit: {slip_pnl} | Win Rate: {slip_winrate}%")
    
    print("\n[3] Injecting 5% Packet Loss (API Outage)...")
    packet_data = inject_packet_loss(historical_data, drop_rate=0.05)
    packet_result = engine_func(packet_data, use_phase1=True, use_ml_filter=True)
    pack_pnl = packet_result.get('net_profit', 0)
    pack_winrate = packet_result.get('win_rate_pct', 0)
    print(f"    Net Profit: {pack_pnl} | Win Rate: {pack_winrate}%")
    
    print("\n[4] The Ultimate Crucible (3x Slippage + 5% Packet Loss)...")
    crucible_data = inject_packet_loss(slippage_data, drop_rate=0.05)
    crucible_result = engine_func(crucible_data, use_phase1=True, use_ml_filter=True)
    cruc_pnl = crucible_result.get('net_profit', 0)
    cruc_winrate = crucible_result.get('win_rate_pct', 0)
    print(f"    Net Profit: {cruc_pnl} | Win Rate: {cruc_winrate}%")
    
    print("\n" + "=" * 60)
    print(" 📊 AUDIT RESULTS")
    print("=" * 60)
    if cruc_pnl > 0:
        print("✅ PASS: The system survived the Adversarial Crucible with positive expectancy.")
    else:
        print("❌ FAIL: The strategy's edge was destroyed by real-world market friction.")
    print("=" * 60)

if __name__ == "__main__":
    from backtesting.historical_fetcher import fetch_historical_data
    from backtesting.engine import run_backtest
    import asyncio
    
    async def main():
        data = await fetch_historical_data(days_back=180)
        run_adversarial_audit(data, run_backtest)
        
    asyncio.run(main())
