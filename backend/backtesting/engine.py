"""
backtesting/engine.py — The core backtest replay engine for Phase 2A.
Simulates trades using historical candles to compare Phase-1 vs Baseline v1.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any

from intelligence import strategy_v1, opportunity_ranker, exit_engine
from intelligence.ml_filter import ml_filter
from intelligence.ai_debate import ai_debate_engine
from core.config import get_settings
from risk.risk_manager import RiskManager

def _get_weights_ffd(d: float, window: int) -> np.ndarray:
    """Generate weights for fractional differentiation."""
    weights = [1.]
    for k in range(1, window):
        w_k = -weights[-1] / k * (d - k + 1)
        weights.append(w_k)
    return np.array(weights[::-1])

class SimulatedBroker:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> position details
        self.trade_history: List[Dict] = []
        self.equity_curve: List[float] = []
        self.risk_manager = RiskManager()
        self.peak_equity = initial_capital
        
    def buy(
        self,
        symbol: str,
        price: float,
        atr: float,
        direction: str,
        time_str: str,
        features: dict = None,
        take_profit_mult: float | None = None,
        stop_loss_mult: float | None = None,
        max_hold_minutes: int | None = None,
        ml_probability: float | None = None,
    ):
        # AGGRESSIVE MODE: Scale up to 3x base size on very high confidence
        multiplier = 1.0
        if ml_probability is not None and ml_probability > 0.5:
            # e.g., 0.85 prob -> (0.85 - 0.5) * 6 = 3.1x size. 0.99 prob -> 3.94x size.
            multiplier = 1.0 + ((ml_probability - 0.5) * 6)
            
        # Allocate buying power (total allowed is 5x cash, split across max 5 positions to compound harder)
        available_buying_power = ((self.cash * 5) / 5.0) * multiplier
        qty = int(available_buying_power / price)
        if qty <= 0: return False

        current_drawdown = max(0.0, (self.peak_equity - self.cash) / self.peak_equity)
        entry_date = pd.to_datetime(time_str).date()
        daily_loss = sum(
            trade["net_pnl"]
            for trade in self.trade_history
            if pd.to_datetime(trade["exit_time"]).date() == entry_date and trade["net_pnl"] < 0
        )
        daily_loss_pct = abs(daily_loss) / self.cash * 100 if self.cash > 0 else 100.0
        risk_decision = self.risk_manager.evaluate_trade(
            ticker=symbol,
            direction=direction,
            quantity=qty,
            price=price,
            portfolio_equity=self.cash,
            portfolio_positions=self.positions,
            portfolio_cash=self.cash * 5,
            portfolio_drawdown=current_drawdown,
            sector="UNKNOWN",
            sector_current_pct=0.0,
            daily_realised_loss_pct=daily_loss_pct,
            price_age_seconds=0.0,
            is_live=False,
            clock_now=pd.to_datetime(time_str).timestamp(),
        )
        if not risk_decision.approved:
            return False
        qty = int(risk_decision.approved_quantity)
        if qty <= 0:
            return False
        
        cost = qty * price
        # Realistic Slippage + Brokerage (Upstox intraday equity: 0.05% or 20, whichever is lower)
        slippage = cost * 0.0005
        brokerage = min(20.0, cost * 0.0005)
        total_cost = cost + slippage + brokerage
        
        # We don't actually subtract 5x cost from cash, we just track the margin impact
        # In reality, you only need cost/5 in cash. But for P&L tracking, we just need entry price.
        
        # Convert time safely
        t_entry = pd.to_datetime(time_str).to_pydatetime()
        
        exit_plan = exit_engine.compute_exits(
            entry_price=price,
            atr14=atr,
            direction=direction,
            entry_time=t_entry,
            take_profit_mult=take_profit_mult,
            stop_loss_mult=stop_loss_mult,
            max_hold_minutes=max_hold_minutes,
        )
        
        self.positions[symbol] = {
            "quantity": qty,
            "entry_price": price,
            "direction": direction,
            "direction": direction,
            "entry_time": time_str,
            "exit_plan": exit_plan,
            "features": features
        }
        return True

    def sell(self, symbol: str, price: float, time_str: str, reason: str):
        if symbol not in self.positions: return
        pos = self.positions.pop(symbol)
        
        qty = pos["quantity"]
        entry = pos["entry_price"]
        
        # Calculate PnL
        if pos["direction"] == "LONG":
            gross_pnl = (price - entry) * qty
        else:
            gross_pnl = (entry - price) * qty
            
        # Deduct exit slippage and commission
        trade_value = price * qty
        slippage = trade_value * 0.0005
        brokerage = min(20.0, trade_value * 0.0005)
        net_pnl = gross_pnl - slippage - brokerage
        
        self.cash += net_pnl
        self.peak_equity = max(self.peak_equity, self.cash)
        self.equity_curve.append(self.cash)
        
        self.trade_history.append({
            "symbol": symbol,
            "direction": pos["direction"],
            "entry_time": pos["entry_time"],
            "entry_price": entry,
            "exit_time": time_str,
            "exit_price": price,
            "net_pnl": round(net_pnl, 2),
            "pnl_pct": round((net_pnl / (entry * qty)) * 100, 2),
            "reason": reason,
            "features": pos.get("features", {})
        })

def _compute_features_for_df(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized calculation of our 11 features over historical data."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["prev_rsi"] = df["rsi"].shift(1)

    # MAs
    df["sma20"] = close.rolling(20).mean()
    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()

    # ATR
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()

    # Volume Ratio
    df["vol_ratio"] = volume / volume.rolling(20).mean()
    df["momentum"] = (close - close.shift(10)) / close.shift(10) * 100
    df["volatility"] = df["atr14"] / close * 100
    df["trend_strength"] = (df["ema9"] - df["ema21"]) / close * 100
    df["range_pct"] = (high - low) / close * 100
    df["return_5"] = close.pct_change(5) * 100
    df["return_20"] = close.pct_change(20) * 100

    # Fractional Differentiation (d=0.5, window=10)
    w_ffd = _get_weights_ffd(d=0.5, window=10)
    df["frac_diff"] = close.rolling(10).apply(lambda x: np.dot(x, w_ffd), raw=True)

    # VWAP
    df['dt'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['dt'].dt.date
    df['vp'] = ((high + low + close) / 3) * volume
    df['vwap'] = df.groupby('date')['vp'].cumsum() / df.groupby('date')['volume'].cumsum()
    # CUSUM Filter (Structural Break Detection)
    threshold = df["atr14"].mean() * 2.0
    diffs = close.diff().fillna(0).values
    events = np.zeros(len(diffs))
    pos_sum, neg_sum = 0, 0
    for i in range(len(diffs)):
        pos_sum = max(0, pos_sum + diffs[i])
        neg_sum = min(0, neg_sum + diffs[i])
        if pos_sum > threshold:
            pos_sum = 0
            events[i] = 1
        elif neg_sum < -threshold:
            neg_sum = 0
            events[i] = -1
    df["cusum_event"] = events
    
    return df.dropna()

def run_backtest(
    historical_data: Dict[str, List[Dict]],
    use_phase1: bool = True,
    use_ml_filter: bool = False,
    initial_capital: float | None = None,
    min_score: float = 40.0,
    take_profit_mult: float | None = None,
    stop_loss_mult: float | None = None,
    max_hold_minutes: int | None = None,
):
    """
    Replay history tick-by-tick across all symbols.
    If use_phase1 is True, runs the opportunity ranker + ATR exits.
    If use_ml_filter is True, runs the trained RandomForest on top of Phase-1 to veto trades.
    If both False, runs the v1 baseline (RSI < 35, 1.5% TP).
    """
    broker = SimulatedBroker(
        initial_capital=(
            initial_capital
            if initial_capital is not None
            else get_settings().paper_trading_initial_capital
        )
    )
    
    # 1. Precompute features for all symbols
    dfs = {}
    for sym, candles in historical_data.items():
        if not candles: continue
        df = pd.DataFrame(candles)
        df = _compute_features_for_df(df)
        dfs[sym] = df
        
    if not dfs:
        return {"error": "No data to backtest"}

    # 2. Find common timeline (to step through chronologically)
    all_times = sorted(list(set(t for df in dfs.values() for t in df['timestamp'])))
    
    # 3. Step through time
    for t in all_times:
        current_features = []
        
        # Check exits first
        for sym, pos in list(broker.positions.items()):
            df = dfs[sym]
            row = df[df['timestamp'] == t]
            if row.empty: continue
            row_dict = row.iloc[0].to_dict()
            current_price = row_dict['close']
            
            # Simulated intra-candle price action:
            current_time = pd.to_datetime(t).to_pydatetime()
            
            if use_phase1:
                # 1. Check if SL or TP was hit during the candle
                sl = pos["exit_plan"]["stop_loss"]
                tp = pos["exit_plan"]["take_profit"]
                direction = pos["direction"]
                
                hit_sl = False
                hit_tp = False
                if direction == "LONG":
                    if row_dict['low'] <= sl: hit_sl = True
                    elif row_dict['high'] >= tp: hit_tp = True
                else:
                    if row_dict['high'] >= sl: hit_sl = True
                    elif row_dict['low'] <= tp: hit_tp = True
                    
                if hit_sl:
                    broker.sell(sym, sl, t, "ATR_STOP (intra-candle)")
                    continue
                elif hit_tp:
                    broker.sell(sym, tp, t, "ATR_TP (intra-candle)")
                    continue
                    
                # 2. Check other conditions at Close
                decision = exit_engine.should_exit(
                    position={"pnl_pct": (current_price - pos["entry_price"]) / pos["entry_price"] * 100},
                    current_price=current_price,
                    exits=pos["exit_plan"],
                    current_features=row_dict,
                    entry_time=pd.to_datetime(pos["entry_time"]).to_pydatetime(),
                    current_time=current_time
                )
                if decision["exit"]:
                    broker.sell(sym, current_price, t, decision["reason"])
            else:
                # v1 exits
                # Basic intra-candle check for v1
                entry = pos["entry_price"]
                direction = pos["direction"]
                if direction == "LONG":
                    max_pnl_pct = (row_dict['high'] - entry) / entry * 100
                    min_pnl_pct = (row_dict['low'] - entry) / entry * 100
                    if max_pnl_pct >= 1.5:
                        broker.sell(sym, entry * 1.015, t, "v1_TAKE_PROFIT (intra)")
                        continue
                    elif min_pnl_pct <= -1.0:
                        broker.sell(sym, entry * 0.99, t, "v1_STOP_LOSS (intra)")
                        continue

        # Collect features for new entries
        for sym, df in dfs.items():
            row = df[df['timestamp'] == t]
            if not row.empty:
                r = row.iloc[0].to_dict()
                r["symbol"] = sym
                r["ltp"] = r["close"]
                r["candle_open"] = r["open"]
                r["candle_close"] = r["close"]
                current_features.append(r)

        # Decide entries
        if use_phase1:
            scored = [opportunity_ranker.score(f) for f in current_features]
            ranked = opportunity_ranker.rank(scored)
            best = opportunity_ranker.best_candidate(ranked, min_score=min_score)
            
            # AGGRESSIVE MODE: Allow max 5 concurrent positions
            if best and len(broker.positions) < 5 and best["symbol"] not in broker.positions:
                
                # Assign direction BEFORE ML prediction so features match training
                best["direction"] = "LONG" if best["rsi"] < 50 else "SHORT"

                # Phase 2A: Machine Learning Quality Filter + Meta Labeler
                approve_trade = True
                if use_ml_filter:
                    prob = ml_filter.predict(best)
                    if prob < ml_filter.approval_threshold:
                        approve_trade = False
                    else:
                        # Feed to AI Debate (Meta-Labeler)
                        mock_event = {"headline": "NO_CATALYST"} # In live, this would pull from event radar
                        debate_res = ai_debate_engine.analyze_event(mock_event, {}, ml_probability=prob)
                        if debate_res.get("final_decision") != "TRADE":
                            approve_trade = False
                        
                if approve_trade:
                    broker.buy(
                        symbol=best["symbol"],
                        price=best["ltp"],
                        atr=best["atr14"],
                        direction=best["candidate_direction"],
                        time_str=t,
                        features=best,
                        take_profit_mult=take_profit_mult,
                        stop_loss_mult=stop_loss_mult,
                        max_hold_minutes=max_hold_minutes,
                        ml_probability=prob if use_ml_filter else None,
                    )
        else:
            # v1 baseline
            for f in current_features:
                if len(broker.positions) >= 5: break
                dec = strategy_v1.evaluate(f)
                if dec["would_execute"] and f["symbol"] not in broker.positions:
                    broker.buy(
                        symbol=f["symbol"],
                        price=f["ltp"],
                        atr=f["atr14"],
                        direction="LONG",
                        time_str=t
                    )

    # Compile report
    trades = broker.trade_history
    win_trades = [t for t in trades if t["net_pnl"] > 0]
    loss_trades = [t for t in trades if t["net_pnl"] <= 0]
    
    win_rate = len(win_trades) / len(trades) * 100 if trades else 0
    total_pnl = sum(t["net_pnl"] for t in trades)
    # Generate ML Dataset
    ml_dataset = []
    if use_phase1:
        for t in trades:
            f = t.get("features", {})
            if not f: continue
            ml_dataset.append({
                'timestamp': t.get('exit_time', t.get('entry_time')),
                'rsi': f.get('rsi', 0),
                'ema9': f.get('ema9', 0),
                'ema21': f.get('ema21', 0),
                'vwap': f.get('vwap', 0),
                'atr14': f.get('atr14', 0),
                'vol_ratio': f.get('vol_ratio', 0),
                'momentum': f.get('momentum', 0),
                'volatility': f.get('volatility', 0),
                'trend_strength': f.get('trend_strength', 0),
                'range_pct': f.get('range_pct', 0),
                'return_5': f.get('return_5', 0),
                'return_20': f.get('return_20', 0),
                'frac_diff': f.get('frac_diff', 0),
                'direction': 1 if t.get('direction') == 'LONG' else -1,
                'target': 1 if t["net_pnl"] > 0 else 0
            })
            
    
    strategy_name = "v1 Baseline (RSI+Fixed)"
    if use_phase1:
        strategy_name = "Phase-2A (Ranker + ML)" if use_ml_filter else "Phase-1 (ATR+Ranker)"

    return {
        "strategy": strategy_name,
        "total_trades": len(trades),
        "win_rate_pct": round(win_rate, 2),
        "net_profit": round(total_pnl, 2),
        "final_capital": round(broker.cash, 2),
        "avg_win": round(np.mean([t["net_pnl"] for t in win_trades]), 2) if win_trades else 0,
        "avg_loss": round(np.mean([t["net_pnl"] for t in loss_trades]), 2) if loss_trades else 0,
        "ml_dataset": pd.DataFrame(ml_dataset) if ml_dataset else None
    }
