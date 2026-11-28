"""
backtesting/compare.py — Runs the backtest comparison between v1, Phase-1, and Phase-2A (ML).
"""
import asyncio
from backtesting.historical_fetcher import fetch_historical_data
from backtesting.engine import run_backtest

async def main():
    print("=" * 65)
    print("  MARKET INTELLIGENCE AI - BACKTEST COMPARISON")
    print("=" * 65)
    
    # 1. Fetch/Load Data
    data = await fetch_historical_data(days_back=15)  # 15 days of 30m candles
    
    # 2. Run Baseline v1
    print("\n🏃 Running Baseline v1 (RSI < 35, Fixed +1.5% TP)...")
    v1_results = run_backtest(data, use_phase1=False)
    
    # 3. Run Phase-1
    print("🏃 Running Phase-1 (Ranker + ATR Exits)...")
    p1_results = run_backtest(data, use_phase1=True, use_ml_filter=False)

    # 4. Run Phase-2A (ML Filter)
    print("🏃 Running Phase-2A (Ranker + ATR + ML Quality Filter)...")
    p2_results = run_backtest(data, use_phase1=True, use_ml_filter=True)
    
    # 5. Print Comparison
    print("\n" + "=" * 65)
    print("  RESULTS (Paper Capital: ₹50,000)")
    print("=" * 65)
    
    def print_stat(name, v1_val, p1_val, p2_val, suffix=""):
        print(f"{name:<15} | v1: {str(v1_val)+suffix:>8} | Phase-1: {str(p1_val)+suffix:>8} | Phase-2A: {str(p2_val)+suffix:>8}")
        
    print_stat("Total Trades", v1_results["total_trades"], p1_results["total_trades"], p2_results["total_trades"])
    print_stat("Win Rate", v1_results["win_rate_pct"], p1_results["win_rate_pct"], p2_results["win_rate_pct"], "%")
    print_stat("Net Profit", v1_results["net_profit"], p1_results["net_profit"], p2_results["net_profit"], " ₹")
    print_stat("Avg Win", v1_results["avg_win"], p1_results["avg_win"], p2_results["avg_win"], " ₹")
    print_stat("Avg Loss", v1_results["avg_loss"], p1_results["avg_loss"], p2_results["avg_loss"], " ₹")
    
    print("=" * 65)
    
    if p2_results["net_profit"] > p1_results["net_profit"]:
        print("🏆 ML Filter successfully protected capital compared to Phase-1!")
        if p2_results["net_profit"] > v1_results["net_profit"]:
             print("🚀 Phase-2A is the overall winner!")
    else:
        print("⚠️ ML Filter needs more tuning.")

if __name__ == "__main__":
    asyncio.run(main())
