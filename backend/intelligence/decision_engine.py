"""Shared AI decision pipeline for live signals and backtests."""
from __future__ import annotations

from typing import Any, Dict

from intelligence import opportunity_ranker
from intelligence.ai_debate import ai_debate_engine
from intelligence.ml_filter import ml_filter


def analyze_setup(
    features: Dict[str, Any],
    *,
    min_score: float = 40.0,
    include_debate: bool = True,
) -> Dict[str, Any]:
    """Score, filter, and explain one setup using the production AI layers.

    The function is deliberately side-effect free so the API and backtest can
    use the same decision contract. A missing/unloaded model never becomes an
    automatic approval.
    """
    scored = opportunity_ranker.score(features)
    result: Dict[str, Any] = {
        "symbol": scored.get("symbol"),
        "technical_score": scored.get("opportunity_score", 0.0),
        "candidate_direction": scored.get("candidate_direction", "NO_TRADE"),
        "score_breakdown": scored.get("score_breakdown", {}),
        "ml_probability": None,
        "decision": "NO_TRADE",
        "reason": "No qualifying Phase-1 setup.",
    }

    if scored.get("candidate_direction") == "NO_TRADE":
        return result
    if scored.get("opportunity_score", 0.0) < min_score:
        result["reason"] = f"Technical score below {min_score:.1f}."
        return result

    probability = float(ml_filter.predict(scored))
    result["ml_probability"] = probability
    threshold = float(getattr(ml_filter, "approval_threshold", 0.6))
    if probability < threshold:
        result["reason"] = f"ML probability below {threshold:.2f}."
        return result

    if not include_debate:
        result["decision"] = "TRADE"
        result["reason"] = "Passed technical and ML filters."
        return result

    analysis = ai_debate_engine.analyze_event(
        {"headline": "NO_CATALYST", "symbol": scored.get("symbol")},
        scored,
        ml_probability=probability,
    )
    result["analysis"] = analysis
    result["decision"] = analysis.get("final_decision", "NO_TRADE")
    result["reason"] = analysis.get("bear_case", "AI arbiter rejected the setup.")
    return result