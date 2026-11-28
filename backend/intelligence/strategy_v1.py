"""
intelligence/strategy_v1.py — Baseline RSI/SMA Strategy (v1)

THIS IS THE PRESERVED BENCHMARK. DO NOT MODIFY THE LOGIC.

The original rule engine: random stock selection, RSI < 35 = BUY, RSI > 70 = no buy,
fixed +1.5% take profit / -1.0% stop loss.

This runs in SHADOW MODE alongside Phase-1. It never places real orders.
Its decisions are recorded so we can compare P&L vs Phase-1 and eventually vs AECE.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict


# ── Strategy constants (original, frozen) ─────────────────────────────────────
V1_RSI_BUY_THRESHOLD   = 35.0
V1_RSI_SELL_THRESHOLD  = 70.0
V1_CONFIDENCE_TRIGGER  = 90.0
V1_TAKE_PROFIT_PCT     = 1.5
V1_STOP_LOSS_PCT       = 1.0
STRATEGY_NAME          = "strategy_v1_rsi_sma"


def evaluate(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply the original fixed RSI/SMA rules to a feature set.
    Returns a decision dict — but NEVER places orders.
    This is hypothesis-only / shadow mode.

    Args:
        features: output from compute_features() — must contain rsi, ltp, sma20

    Returns:
        Decision dict with direction, confidence, take_profit, stop_loss
    """
    symbol     = features["symbol"]
    rsi        = features["rsi"]
    ltp        = features["ltp"]
    sma20      = features.get("sma20", ltp)

    # Original logic: RSI < 35 → BUY
    confidence = 0.0
    direction  = "NO_TRADE"
    rationale  = ""

    if rsi < V1_RSI_BUY_THRESHOLD:
        confidence = min(99.0, 80.0 + (V1_RSI_BUY_THRESHOLD - rsi))
        direction  = "LONG"
        rationale  = f"RSI={rsi:.1f} < {V1_RSI_BUY_THRESHOLD} (oversold bounce)"
    elif rsi > V1_RSI_SELL_THRESHOLD:
        direction  = "NO_TRADE"   # v1 never shorts
        confidence = 0.0
        rationale  = f"RSI={rsi:.1f} > {V1_RSI_SELL_THRESHOLD} (overbought, v1 skips)"
    else:
        direction  = "NO_TRADE"
        confidence = 0.0
        rationale  = f"RSI={rsi:.1f} in neutral zone (v1 skips)"

    would_execute = direction == "LONG" and confidence > V1_CONFIDENCE_TRIGGER

    # Fixed exits
    take_profit_price = round(ltp * (1 + V1_TAKE_PROFIT_PCT / 100), 2)
    stop_loss_price   = round(ltp * (1 - V1_STOP_LOSS_PCT  / 100), 2)

    return {
        "strategy":         STRATEGY_NAME,
        "symbol":           symbol,
        "direction":        direction,
        "confidence":       round(confidence, 1),
        "would_execute":    would_execute,
        "take_profit":      take_profit_price,
        "stop_loss":        stop_loss_price,
        "tp_pct":           V1_TAKE_PROFIT_PCT,
        "sl_pct":           V1_STOP_LOSS_PCT,
        "rationale":        rationale,
        "features_used":    ["rsi", "sma20"],
        "evaluated_at":     datetime.now().isoformat(),
    }
