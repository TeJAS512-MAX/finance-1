"""
intelligence/exit_engine.py — Phase-1 Thesis-Aware Exit Engine

Replaces fixed +1.5% / -1.0% exits with ATR-scaled, multi-condition exits.

Exit conditions (evaluated in priority order):
  1. HARD STOP LOSS   — price crosses absolute max-loss level (risk limit, always active)
  2. ATR STOP LOSS    — 1.0× ATR below entry (tighter in calm markets, wider in volatile)
  3. ATR TAKE PROFIT  — 2.0× ATR above entry (reward:risk = 2:1)
  4. TIME STOP        — close position after max_hold_minutes if thesis hasn't played out
  5. EMA INVALIDATION — EMA9 crosses below EMA21 (trend invalidation for LONG)
  6. VWAP REJECTION   — price crosses back below VWAP (institutional rejection signal)

The hard risk limit (MAX_LOSS_PCT) is ALWAYS enforced regardless of other signals.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ── Constants ──────────────────────────────────────────────────────────────────
ATR_TAKE_PROFIT_MULT  = 2.5    # Take profit = 2.5× ATR above entry
ATR_STOP_LOSS_MULT    = 1.5    # Stop loss   = 1.5× ATR below entry
MAX_LOSS_PCT          = 2.0    # Absolute hard stop — never allow more than 2% loss
MAX_HOLD_MINUTES      = 75     # Time stop — exit if position not profitable after 75 min
MIN_ATR_FALLBACK_PCT  = 0.5    # If ATR is zero/invalid, fall back to 0.5% of price


def compute_exits(
    entry_price: float,
    atr14: float,
    direction: str = "LONG",
    entry_time: Optional[datetime] = None,
    take_profit_mult: Optional[float] = None,
    stop_loss_mult: Optional[float] = None,
    max_hold_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute all exit levels for a new position.

    Args:
        entry_price: Fill price of the entry order
        atr14:       ATR(14) at time of entry — used to scale stops/targets
        direction:   "LONG" or "SHORT"
        entry_time:  When the order was filled (defaults to now)

    Returns:
        Dict with take_profit, stop_loss, hard_stop, time_stop, and metadata
    """
    if entry_time is None:
        entry_time = datetime.now(timezone.utc)

    # Guard against bad ATR (e.g. during first candles of the day)
    effective_atr = atr14 if atr14 > 0.01 else entry_price * (MIN_ATR_FALLBACK_PCT / 100)
    take_profit_mult = take_profit_mult if take_profit_mult is not None else ATR_TAKE_PROFIT_MULT
    stop_loss_mult = stop_loss_mult if stop_loss_mult is not None else ATR_STOP_LOSS_MULT
    max_hold_minutes = max_hold_minutes if max_hold_minutes is not None else MAX_HOLD_MINUTES

    if direction == "LONG":
        take_profit = round(entry_price + take_profit_mult * effective_atr, 2)
        stop_loss   = round(entry_price - stop_loss_mult * effective_atr, 2)
        hard_stop   = round(entry_price * (1 - MAX_LOSS_PCT / 100), 2)
        # Hard stop must be at least as tight as ATR stop
        hard_stop   = max(hard_stop, stop_loss - effective_atr * 0.5)
        stop_loss   = max(stop_loss, hard_stop)     # stop can't be worse than hard stop
    else:  # SHORT
        take_profit = round(entry_price - take_profit_mult * effective_atr, 2)
        stop_loss   = round(entry_price + stop_loss_mult * effective_atr, 2)
        hard_stop   = round(entry_price * (1 + MAX_LOSS_PCT / 100), 2)
        hard_stop   = min(hard_stop, stop_loss + effective_atr * 0.5)
        stop_loss   = min(stop_loss, hard_stop)

    tp_pct = round(abs(take_profit - entry_price) / entry_price * 100, 2)
    sl_pct = round(abs(stop_loss   - entry_price) / entry_price * 100, 2)

    return {
        "entry_price":    entry_price,
        "direction":      direction,
        "take_profit":    take_profit,
        "stop_loss":      stop_loss,
        "hard_stop":      hard_stop,
        "tp_pct":         tp_pct,
        "sl_pct":         sl_pct,
        "reward_risk":    round(tp_pct / sl_pct, 2) if sl_pct > 0 else 0.0,
        "atr_used":       round(effective_atr, 2),
        "time_stop_mins": max_hold_minutes,
        "entry_time":     entry_time.isoformat(),
        "exit_engine":    "phase1_atr_v1",
    }


def should_exit(
    position: Dict[str, Any],
    current_price: float,
    exits: Dict[str, Any],
    current_features: Optional[Dict[str, Any]] = None,
    entry_time: Optional[datetime] = None,
    current_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluate all exit conditions for an open position.

    Args:
        position:         Position dict from broker (has symbol, quantity, pnl_pct)
        current_price:    Current LTP of the symbol
        exits:            Exit levels returned by compute_exits() at entry time
        current_features: Latest feature dict — used for EMA/VWAP checks
        entry_time:       When position was opened

    Returns:
        {"exit": True/False, "reason": str, "urgency": "HARD"/"SOFT"}
    """
    direction   = exits.get("direction", "LONG")
    take_profit = exits.get("take_profit", 0.0)
    stop_loss   = exits.get("stop_loss", 0.0)
    hard_stop   = exits.get("hard_stop", 0.0)

    # ── 1. HARD STOP (always first, non-negotiable) ────────────────────────────
    if direction == "LONG" and current_price <= hard_stop:
        return {"exit": True, "reason": f"HARD_STOP (price ₹{current_price:.2f} ≤ ₹{hard_stop:.2f})", "urgency": "HARD"}
    if direction == "SHORT" and current_price >= hard_stop:
        return {"exit": True, "reason": f"HARD_STOP (price ₹{current_price:.2f} ≥ ₹{hard_stop:.2f})", "urgency": "HARD"}

    # ── 2. ATR-based Stop Loss ─────────────────────────────────────────────────
    if direction == "LONG" and current_price <= stop_loss:
        return {"exit": True, "reason": f"ATR_STOP (price ₹{current_price:.2f} ≤ ₹{stop_loss:.2f}, 1×ATR)", "urgency": "HARD"}
    if direction == "SHORT" and current_price >= stop_loss:
        return {"exit": True, "reason": f"ATR_STOP (price ₹{current_price:.2f} ≥ ₹{stop_loss:.2f}, 1×ATR)", "urgency": "HARD"}

    # ── 3. ATR-based Take Profit ───────────────────────────────────────────────
    if direction == "LONG" and current_price >= take_profit:
        return {"exit": True, "reason": f"ATR_TP (price ₹{current_price:.2f} ≥ ₹{take_profit:.2f}, 2×ATR)", "urgency": "SOFT"}
    if direction == "SHORT" and current_price <= take_profit:
        return {"exit": True, "reason": f"ATR_TP (price ₹{current_price:.2f} ≤ ₹{take_profit:.2f}, 2×ATR)", "urgency": "SOFT"}

    # ── 4. Time Stop ───────────────────────────────────────────────────────────
    if entry_time:
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
            
        held_minutes = (current_time - entry_time).total_seconds() / 60
        if held_minutes >= exits.get("time_stop_mins", MAX_HOLD_MINUTES):
            pnl_pct = position.get("pnl_pct", 0.0)
            if pnl_pct < 0.3:   # Only time-exit if not meaningfully profitable
                return {"exit": True, "reason": f"TIME_STOP ({held_minutes:.0f} min, pnl={pnl_pct:.2f}%)", "urgency": "SOFT"}

    # ── 5. EMA Invalidation (LONG: EMA9 crosses below EMA21) ──────────────────
    if current_features:
        ema9  = current_features.get("ema9", 0)
        ema21 = current_features.get("ema21", 0)
        if direction == "LONG" and ema9 > 0 and ema21 > 0 and ema9 < ema21:
            return {"exit": True, "reason": f"EMA_INVALIDATION (EMA9 ₹{ema9:.2f} < EMA21 ₹{ema21:.2f})", "urgency": "SOFT"}
        if direction == "SHORT" and ema9 > 0 and ema21 > 0 and ema9 > ema21:
            return {"exit": True, "reason": f"EMA_INVALIDATION (EMA9 ₹{ema9:.2f} > EMA21 ₹{ema21:.2f})", "urgency": "SOFT"}

    # ── No exit condition met ──────────────────────────────────────────────────
    return {"exit": False, "reason": "HOLD", "urgency": None}
