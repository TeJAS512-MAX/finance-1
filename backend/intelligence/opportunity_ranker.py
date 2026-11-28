"""
intelligence/opportunity_ranker.py — Phase-1 Opportunity Scorer

Replaces random stock selection with a scored, ranked scan of the full watchlist.
Every symbol gets an opportunity score based on multiple features.
The highest-scoring setup is selected for potential execution.

Score components:
  - RSI edge:      how far from 35/65 thresholds (oversold/overbought)
  - EMA alignment: is price above EMA9 and EMA21? (trend confirmation)
  - Volume surge:  is volume notably above its 20-period average?
  - VWAP edge:     is price close to VWAP (institutional reference)?
  - Momentum:      is price accelerating in the right direction?
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def score(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute an opportunity score for a single symbol's feature set.

    Returns the features dict enriched with:
      - opportunity_score (0–100)
      - candidate_direction ("LONG" | "SHORT" | "NO_TRADE")
      - score_breakdown: dict of individual component scores
    """
    rsi       = features.get("rsi", 50.0)
    close_price = features.get("close", 0.0)
    ema9      = features.get("ema9", close_price)
    ema21     = features.get("ema21", close_price)
    vol_ratio = features.get("vol_ratio", 1.0)
    momentum  = features.get("momentum", 0.0)
    vwap      = features.get("vwap", close_price)
    atr14     = features.get("atr14", 0.0)

    # ── 1. RSI Edge & Reversal Confirmation (0–40 pts) ─────────────────────────
    # Strong LONG edge when RSI < 35 AND turning up (prev_rsi < rsi) AND current candle is green
    rsi_score       = 0.0
    candidate_dir   = "NO_TRADE"
    prev_rsi        = features.get("prev_rsi", rsi)
    candle_open     = features.get("open", close_price)
    candle_close    = features.get("close", close_price)

    if rsi < 45 and rsi > prev_rsi and candle_close > candle_open:
        rsi_score     = min(40.0, (45.0 - rsi) * 2.5)   # max 40 at RSI=29
        candidate_dir = "LONG"
    elif rsi > 55 and rsi < prev_rsi and candle_close < candle_open:
        rsi_score     = min(40.0, (rsi - 55.0) * 2.5)   # max 40 at RSI=71
        candidate_dir = "SHORT"
    else:
        rsi_score     = 0.0
        candidate_dir = "NO_TRADE"

    # ── 2. EMA Alignment (0–20 pts) ───────────────────────────────────────────
    # LONG: price > EMA9 > EMA21 (uptrend)
    # SHORT: price < EMA9 < EMA21 (downtrend)
    ema_score = 0.0
    if candidate_dir == "LONG":
        if close_price > ema9 and ema9 > ema21:
            ema_score = 20.0
        elif close_price > ema21:
            ema_score = 10.0
    elif candidate_dir == "SHORT":
        if close_price < ema9 and ema9 < ema21:
            ema_score = 20.0
        elif close_price < ema21:
            ema_score = 10.0

    # ── 3. Volume Surge (0–20 pts) ─────────────────────────────────────────────
    # Volume > 1.5x avg = confirmation; > 2x = strong confirmation
    if vol_ratio >= 2.0:
        vol_score = 20.0
    elif vol_ratio >= 1.5:
        vol_score = 12.0
    elif vol_ratio >= 1.2:
        vol_score = 6.0
    else:
        vol_score = 0.0

    # ── 4. VWAP Proximity (0–10 pts) ──────────────────────────────────────────
    # Price near VWAP (within 0.3%) = potential bounce zone
    if vwap > 0:
        vwap_deviation_pct = abs(close_price - vwap) / vwap * 100
        if vwap_deviation_pct < 0.3:
            vwap_score = 10.0
        elif vwap_deviation_pct < 0.8:
            vwap_score = 5.0
        else:
            vwap_score = 0.0
    else:
        vwap_score = 0.0

    # ── 5. Momentum Confirmation (0–10 pts) ───────────────────────────────────
    # Momentum should align with candidate direction
    momentum_score = 0.0
    if candidate_dir == "LONG" and momentum > 0.5:
        momentum_score = min(10.0, momentum * 2)
    elif candidate_dir == "SHORT" and momentum < -0.5:
        momentum_score = min(10.0, abs(momentum) * 2)

    # ── Total ──────────────────────────────────────────────────────────────────
    total = rsi_score + ema_score + vol_score + vwap_score + momentum_score
    total = min(100.0, total)

    return {
        **features,
        "opportunity_score":    round(total, 1),
        "candidate_direction":  candidate_dir,
        "score_breakdown": {
            "rsi_edge":    round(rsi_score, 1),
            "ema_align":   round(ema_score, 1),
            "volume_surge":round(vol_score, 1),
            "vwap_prox":   round(vwap_score, 1),
            "momentum":    round(momentum_score, 1),
        },
    }


def rank(scored_symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort symbols by opportunity_score descending. NO_TRADE candidates go last."""
    tradeable = [s for s in scored_symbols if s.get("candidate_direction") != "NO_TRADE"]
    no_trade  = [s for s in scored_symbols if s.get("candidate_direction") == "NO_TRADE"]
    tradeable_sorted = sorted(tradeable, key=lambda x: x["opportunity_score"], reverse=True)
    no_trade_sorted  = sorted(no_trade,  key=lambda x: x["opportunity_score"], reverse=True)
    return tradeable_sorted + no_trade_sorted


def best_candidate(ranked: List[Dict[str, Any]], min_score: float = 40.0) -> Optional[Dict[str, Any]]:
    """
    Return the top-ranked symbol if it meets the minimum score threshold.
    Returns None if no setup meets the bar — meaning we sit on our hands.
    """
    if not ranked:
        return None
    top = ranked[0]
    if top["opportunity_score"] >= min_score and top["candidate_direction"] != "NO_TRADE":
        return top
    return None
