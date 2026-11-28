"""
portfolio_intelligence/opportunity_evaluation.py — Opportunity Evaluation Engine
================================================================================

Scores a candidate trade before it reaches portfolio allocation.
This module strictly evaluates the opportunity on its own merits, divorced
from current portfolio state (which Capital Allocation handles).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class OpportunityScore:
    symbol: str
    direction: str
    base_confidence: float
    catalyst_strength: float
    technical_alignment: float
    fundamental_margin_of_safety: float
    final_score: float
    is_viable: bool
    rejection_reason: Optional[str] = None


class OpportunityEvaluationEngine:
    """Evaluates raw signals for viability as standalone opportunities."""

    def __init__(self, min_score_threshold: float = 0.6) -> None:
        self.min_score_threshold = min_score_threshold

    def evaluate(
        self,
        symbol: str,
        direction: str,
        base_confidence: float,
        catalyst_strength: float,
        technical_alignment: float,
        fundamental_margin_of_safety: float,
    ) -> OpportunityScore:
        """
        Evaluate an opportunity based on conviction across multiple pillars.
        """
        
        # Penalize if fundamentals or technicals strongly disagree
        if technical_alignment < 0.2:
            return OpportunityScore(
                symbol=symbol, direction=direction,
                base_confidence=base_confidence, catalyst_strength=catalyst_strength,
                technical_alignment=technical_alignment, fundamental_margin_of_safety=fundamental_margin_of_safety,
                final_score=0.0, is_viable=False,
                rejection_reason="Technical structure strongly contradicts the trade."
            )

        # Composite score
        score = (
            base_confidence * 0.4 +
            catalyst_strength * 0.3 +
            technical_alignment * 0.15 +
            fundamental_margin_of_safety * 0.15
        )

        is_viable = score >= self.min_score_threshold

        return OpportunityScore(
            symbol=symbol,
            direction=direction,
            base_confidence=base_confidence,
            catalyst_strength=catalyst_strength,
            technical_alignment=technical_alignment,
            fundamental_margin_of_safety=fundamental_margin_of_safety,
            final_score=score,
            is_viable=is_viable,
            rejection_reason="Score below threshold." if not is_viable else None
        )
