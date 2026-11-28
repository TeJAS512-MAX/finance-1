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
from services.providers.upstox_market_data import compute_frac_diff

def _position_pnl_pct(direction: str, entry_price: float, current_price: float) -> float:
    """Return signed percentage PnL for LONG or SHORT positions."""
    raw_pnl_pct = (current_price - entry_price) / entry_price * 100
    return raw_pnl_pct if direction == "LONG" else -raw_pnl_pct


class SimulatedBroker:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> position details
        self.trade_history: List[Dict] = []
        self.equity_curve: List[float] = []
        self.risk_manager = RiskManager()
        self.peak_equity = initial_capital
        self._daily_losses: Dict[Any, float] = {}
        
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
        max_pos_pct = get_settings().max_position_size_pct
        size_pct = max_pos_pct
        if ml_probability is not None:
            # Scale within the hard max_position_size_pct cap by ML confidence.
            confidence_factor = min(1.0, max(0.5, 0.5 + max(0.0, ml_probability - 0.4)))
            size_pct = max_pos_pct * confidence_factor

        available_buying_power = self.cash * (size_pct / 100.0)
        qty = int(available_buying_power / price)
        if qty <= 0: return False

        current_drawdown = max(0.0, (self.peak_equity - self.cash) / self.peak_equity)
        t_entry_ts = pd.to_datetime(time_str)
        entry_date = t_entry_ts.date()
        daily_loss = self._daily_losses.get(entry_date, 0.0)
        daily_loss_pct = daily_loss / self.cash * 100 if self.cash > 0 else 100.0
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
            clock_now=t_entry_ts.timestamp(),
        )
        if not risk_decision.approved:
            return False
        qty = int(risk_decision.approved_quantity)
        if qty <= 0:
            return False
        
        cost = qty * price
        # Realistic Slippage + Brokerage (Upstox intraday equity: 0.05% slippage + min(20, 0.05%) brokerage per side)
        slippage = cost * 0.0005
        brokerage = min(20.0, cost * 0.0005)
        entry_fee = slippage + brokerage
        
        t_entry = t_entry_ts.to_pydatetime()
        
        ema_aligned = bool(features.get("ema9", 0) > features.get("ema21", 0)) if (features and direction == "LONG") else bool(features.get("ema9", 0) < features.get("ema21", 0)) if features else True
        exit_plan = exit_engine.compute_exits(
            entry_price=price,
            atr14=atr,
            direction=direction,
            entry_time=t_entry,
            take_profit_mult=take_profit_mult,
            stop_loss_mult=stop_loss_mult,
            max_hold_minutes=max_hold_minutes,
            ema_trend_aligned=ema_aligned,
        )
        
        self.positions[symbol] = {
            "quantity": qty,
            "entry_price": price,
            "direction": direction,
            "entry_time": time_str,
            "entry_dt": t_entry,
            "entry_fee": entry_fee,
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
            
        # Deduct round-trip slippage and brokerage (entry + exit sides)
        trade_value = price * qty
        exit_fee = trade_value * 0.0005 + min(20.0, trade_value * 0.0005)
        entry_fee = pos.get("entry_fee", 0.0)
        net_pnl = gross_pnl - exit_fee - entry_fee
        
        self.cash += net_pnl
        if net_pnl < 0:
            exit_date = pd.to_datetime(time_str).date()
            self._daily_losses[exit_date] = self._daily_losses.get(exit_date, 0.0) + abs(net_pnl)
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

    # Fractional Differentiation (d=0.5, window=10) and scale-invariant ratios
    df["frac_diff"] = compute_frac_diff(close, d=0.5, window=10)
    df["ema9_dist_pct"] = (close - df["ema9"]) / close * 100.0
    df["ema21_dist_pct"] = (close - df["ema21"]) / close * 100.0
    df["frac_diff_pct"] = df["frac_diff"] / close * 100.0
    df["rsi_delta"] = df["rsi"] - df["prev_rsi"]
    span = (high - low).replace(0.0, np.nan)
    df["body_pct"] = ((close - df["open"]) / span).fillna(0.0)
    df["return_1"] = close.pct_change(1).fillna(0.0) * 100.0

    # VWAP (guard zero volume)
    dt_parsed = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df['dt'] = dt_parsed
    dt_ist = dt_parsed.dt.tz_convert("Asia/Kolkata")
    df['date'] = dt_ist.dt.date
    df['hour_ist'] = dt_ist.dt.hour + dt_ist.dt.minute / 60.0
    df['vp'] = ((high + low + close) / 3) * volume
    cum_vol = df.groupby('date')['volume'].cumsum()
    cum_vp = df.groupby('date')['vp'].cumsum()
    df['vwap'] = np.where(cum_vol > 0, cum_vp / cum_vol, close)
    df['vwap_dist_pct'] = np.where(df['vwap'] > 0, (close - df['vwap']) / df['vwap'] * 100.0, 0.0)

    # Causal CUSUM Filter (expanding ATR prevents future threshold leakage)
    atr_thresholds = df["atr14"].expanding(min_periods=14).mean().bfill().fillna(0.0).to_numpy() * 2.0
    diffs = close.diff().fillna(0.0).to_numpy()
    events = np.zeros(len(diffs))
    pos_sum, neg_sum = 0.0, 0.0
    for i in range(len(diffs)):
        pos_sum = max(0.0, pos_sum + diffs[i])
        neg_sum = min(0.0, neg_sum + diffs[i])
        thr = float(atr_thresholds[i]) if atr_thresholds[i] > 0 else float("inf")
        if pos_sum > thr:
            pos_sum = 0.0
            events[i] = 1
        elif neg_sum < -thr:
            neg_sum = 0.0
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
    
    # 1. Precompute features and timestamp-indexed lookups for all symbols
    dfs = {}
    rows_by_symbol: Dict[str, Dict[Any, Dict[str, Any]]] = {}
    for sym, candles in historical_data.items():
        if not candles: continue
        df = pd.DataFrame(candles)
        df = _compute_features_for_df(df)
        dfs[sym] = df
        ts_map: Dict[Any, Dict[str, Any]] = {}
        for row_dict in df.to_dict("records"):
            ts_map.setdefault(row_dict["timestamp"], row_dict)
        rows_by_symbol[sym] = ts_map
        
    if not dfs:
        return {"error": "No data to backtest"}

    # 2. Find common timeline and optional vectorized ML batch cache
    all_times = sorted(list(set(t for ts_map in rows_by_symbol.values() for t in ts_map)))
    ml_batch_probs: Dict[tuple, float] | None = None
    if (
        use_phase1
        and use_ml_filter
        and getattr(ml_filter, "is_loaded", False)
        and "predict" not in getattr(ml_filter, "__dict__", {})
        and hasattr(ml_filter, "predict_batch")
    ):
        batch_frames = []
        for sym, df_sym in dfs.items():
            if df_sym.empty:
                continue
            for dir_val in (1.0, -1.0):
                sub = df_sym.copy()
                sub["symbol"] = sym
                sub["direction"] = dir_val
                batch_frames.append(sub)
        if batch_frames:
            all_df = pd.concat(batch_frames, ignore_index=True)
            probs = ml_filter.predict_batch(all_df)
            ml_batch_probs = {
                (row.symbol, row.timestamp, float(row.direction)): float(p)
                for row, p in zip(
                    all_df[["symbol", "timestamp", "direction"]].itertuples(index=False),
                    probs,
                )
            }
    
    # 3. Step through time
    for t in all_times:
        current_features = []
        current_time = pd.to_datetime(t).to_pydatetime()
        
        # Check exits first
        for sym, pos in list(broker.positions.items()):
            row_dict = rows_by_symbol[sym].get(t)
            if row_dict is None: continue
            current_price = row_dict['close']
            
            if use_phase1:
                # 1. Check if SL or TP was hit during the candle
                sl = pos["exit_plan"]["stop_loss"]
                tp = pos["exit_plan"]["take_profit"]
                direction = pos["direction"]
                
                hit_sl = False
                hit_tp = False
                if direction == "LONG":
                    if row_dict['low'] <= sl:
                        hit_sl = True
                        sl_fill = min(float(row_dict['open']), float(sl))
                    elif row_dict['high'] >= tp:
                        hit_tp = True
                        tp_fill = max(float(row_dict['open']), float(tp))
                else:
                    if row_dict['high'] >= sl:
                        hit_sl = True
                        sl_fill = max(float(row_dict['open']), float(sl))
                    elif row_dict['low'] <= tp:
                        hit_tp = True
                        tp_fill = min(float(row_dict['open']), float(tp))
                    
                if hit_sl:
                    broker.sell(sym, sl_fill, t, "ATR_STOP (intra-candle)")
                    continue
                elif hit_tp:
                    broker.sell(sym, tp_fill, t, "ATR_TP (intra-candle)")
                    continue
                    
                # 2. Check other conditions at Close
                decision = exit_engine.should_exit(
                    position={"pnl_pct": _position_pnl_pct(direction, pos["entry_price"], current_price)},
                    current_price=current_price,
                    exits=pos["exit_plan"],
                    current_features=row_dict,
                    entry_time=pos.get("entry_dt") or pd.to_datetime(pos["entry_time"]).to_pydatetime(),
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
        for sym, ts_map in rows_by_symbol.items():
            raw_row = ts_map.get(t)
            if raw_row is not None:
                r = dict(raw_row)
                r["symbol"] = sym
                r["ltp"] = r["close"]
                r["candle_open"] = r["open"]
                r["candle_close"] = r["close"]
                current_features.append(r)

        # Decide entries
        if use_phase1 and use_ml_filter:
            ml_candidates = []
            ml_threshold = float(getattr(ml_filter, "approval_threshold", 0.56))
            for f in current_features:
                sym = f["symbol"]
                if sym in broker.positions:
                    continue
                if ml_batch_probs is not None:
                    p_long = ml_batch_probs.get((sym, t, 1.0), 0.0)
                    p_short = ml_batch_probs.get((sym, t, -1.0), 0.0)
                    best_dir, prob = ("LONG", p_long) if p_long >= p_short else ("SHORT", p_short)
                else:
                    sc = opportunity_ranker.score(f)
                    if sc.get("candidate_direction") == "NO_TRADE" or sc.get("opportunity_score", 0.0) < min_score:
                        continue
                    best_dir = sc["candidate_direction"]
                    f_cand = {**sc, "direction": best_dir}
                    prob = ml_filter.predict(f_cand)
                if prob < ml_threshold:
                    continue
                mock_event = {"headline": "NO_CATALYST"}
                debate_res = ai_debate_engine.analyze_event(
                    mock_event, {}, ml_probability=prob
                )
                if debate_res.get("final_decision") != "TRADE":
                    continue
                ml_candidates.append({**f, "candidate_direction": best_dir, "direction": best_dir, "_ml_prob": prob})

            ml_candidates.sort(key=lambda x: x["_ml_prob"], reverse=True)
            for candidate in ml_candidates:
                if len(broker.positions) >= 5:
                    break
                if candidate["symbol"] in broker.positions:
                    continue
                broker.buy(
                    symbol=candidate["symbol"],
                    price=candidate["ltp"],
                    atr=candidate["atr14"],
                    direction=candidate["candidate_direction"],
                    time_str=t,
                    features=candidate,
                    take_profit_mult=take_profit_mult,
                    stop_loss_mult=stop_loss_mult,
                    max_hold_minutes=max_hold_minutes,
                    ml_probability=candidate["_ml_prob"],
                )
        elif use_phase1:
            scored = [opportunity_ranker.score(f) for f in current_features]
            ranked = opportunity_ranker.rank(scored)
            for candidate in ranked:
                if len(broker.positions) >= 5:
                    break
                if (
                    candidate.get("opportunity_score", 0.0) < min_score
                    or candidate.get("candidate_direction") == "NO_TRADE"
                    or candidate["symbol"] in broker.positions
                ):
                    continue

                candidate["direction"] = candidate["candidate_direction"]
                broker.buy(
                    symbol=candidate["symbol"],
                    price=candidate["ltp"],
                    atr=candidate["atr14"],
                    direction=candidate["candidate_direction"],
                    time_str=t,
                    features=candidate,
                    take_profit_mult=take_profit_mult,
                    stop_loss_mult=stop_loss_mult,
                    max_hold_minutes=max_hold_minutes,
                    ml_probability=None,
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
    gross_wins = sum(t["net_pnl"] for t in win_trades)
    gross_losses = abs(sum(t["net_pnl"] for t in loss_trades))
    profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (round(gross_wins, 2) if gross_wins > 0 else 0.0)
    peak_eq = broker.initial_capital
    max_drawdown = 0.0
    for eq in broker.equity_curve:
        peak_eq = max(peak_eq, eq)
        max_drawdown = max(max_drawdown, peak_eq - eq)
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
        "max_drawdown": round(max_drawdown, 2),
        "profit_factor": profit_factor,
        "avg_win": round(np.mean([t["net_pnl"] for t in win_trades]), 2) if win_trades else 0,
        "avg_loss": round(np.mean([t["net_pnl"] for t in loss_trades]), 2) if loss_trades else 0,
        "trade_pnls": [t["net_pnl"] for t in trades],
        "ml_dataset": pd.DataFrame(ml_dataset) if ml_dataset else None
    }
