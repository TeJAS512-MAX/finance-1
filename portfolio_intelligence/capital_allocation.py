"""
portfolio_intelligence/capital_allocation.py — Item 55: Portfolio Capital Allocation Engine
============================================================================================

Treats capital as a LIMITED resource.

For every candidate opportunity, calculates:
  - Expected opportunity score
  - Risk score
  - Uncertainty penalty
  - Correlation penalty (with existing positions)
  - Liquidity adjustment
  - Portfolio impact
  - Transaction cost penalty

The system may allocate ZERO capital even if the underlying thesis appears attractive.

Allocation decision: APPROVED | REDUCED | REJECTED
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    AllocationDecision,
    AllocationResult,
    Portfolio,
    StrategyFamily,
    TradeCandidate,
    MarketRegime,
)


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHTS = {
    "opportunity":    0.25,
    "risk":          -0.30,   # Negative: higher risk → lower allocation
    "uncertainty":   -0.20,
    "correlation":   -0.15,
    "liquidity":      0.10,
    "portfolio_impact": -0.05,
    "transaction_cost": -0.05,
}

# Maximum fraction of portfolio equity for any single trade
MAX_ALLOCATION_FRACTION = 0.10
MIN_ALLOCATION_FRACTION = 0.005    # Below this → ZERO (not worth the costs)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class AllocationScore:
    opportunity_score:    float = 0.0
    risk_score:           float = 0.0
    uncertainty_score:    float = 0.0
    correlation_penalty:  float = 0.0
    liquidity_score:      float = 0.0
    portfolio_impact:     float = 0.0
    transaction_cost_pct: float = 0.0
    composite_score:      float = 0.0
    recommended_fraction: float = 0.0
    rejection_reasons:    List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CapitalAllocationEngine:
    """
    Allocates portfolio capital to candidate opportunities.

    Usage
    -----
    engine = CapitalAllocationEngine()
    result = engine.allocate(
        candidate=trade_candidate,
        portfolio=portfolio,
        existing_correlations={symbol: corr},
        regime=MarketRegime.BULL_TREND,
        avg_daily_volume=1_000_000,
    )
    """

    def __init__(
        self,
        max_allocation_fraction: float = MAX_ALLOCATION_FRACTION,
        min_allocation_fraction: float = MIN_ALLOCATION_FRACTION,
    ) -> None:
        self._max_frac = max_allocation_fraction
        self._min_frac = min_allocation_fraction
        self._allocation_log: List[AllocationResult] = []

    def allocate(
        self,
        candidate: TradeCandidate,
        portfolio: Portfolio,
        existing_correlations: Dict[str, float],
        regime: MarketRegime,
        avg_daily_volume: float,
        volatility_pct: float = 0.02,
        transaction_cost_pct: float = 0.0003,
    ) -> AllocationResult:
        """
        Determine how much capital (if any) to allocate to a candidate trade.

        Parameters
        ----------
        candidate            : Proposed trade.
        portfolio            : Current portfolio state.
        existing_correlations: {symbol: correlation} for positions already held.
        regime               : Current market regime.
        avg_daily_volume     : Average daily trading volume in base currency.
        volatility_pct       : Estimated volatility of the candidate (daily).
        transaction_cost_pct : Round-trip transaction cost fraction.
        """
        score = AllocationScore()
        rejection_reasons: List[str] = []

        portfolio_equity = portfolio.total_equity
        if portfolio_equity <= 0:
            return self._zero_allocation(candidate.trade_id, ["Portfolio equity is zero or negative"])

        # ── 1. Opportunity score from signal strength ────────
        score.opportunity_score = candidate.signal_strength  # 0..1

        # ── 2. Risk score (volatility-adjusted) ──────────────
        score.risk_score = min(1.0, volatility_pct * 20)   # High vol → high risk score

        # ── 3. Uncertainty ───────────────────────────────────
        # Lower confidence → higher uncertainty penalty
        confidence = candidate.signal_strength
        score.uncertainty_score = 1.0 - confidence

        # ── 4. Correlation penalty ────────────────────────────
        max_corr = max(
            (abs(c) for c in existing_correlations.values()),
            default=0.0,
        )
        score.correlation_penalty = max_corr

        if max_corr > 0.8:
            rejection_reasons.append(
                f"HIGH_CORRELATION: max correlation {max_corr:.2f} with existing positions "
                f"(limit: 0.8). Trade would concentrate portfolio risk."
            )

        # ── 5. Liquidity adjustment ───────────────────────────
        proposed_notional = candidate.proposed_quantity * candidate.proposed_price
        if avg_daily_volume > 0:
            volume_participation = proposed_notional / avg_daily_volume
            # We should not exceed 5% of average daily volume
            if volume_participation > 0.05:
                score.liquidity_score = max(0.0, 1.0 - (volume_participation / 0.05 - 1.0))
                rejection_reasons.append(
                    f"LOW_LIQUIDITY: trade is {volume_participation*100:.1f}% of average daily volume "
                    f"(limit: 5%). Execution at proposed price may not be achievable."
                )
            else:
                score.liquidity_score = 1.0
        else:
            score.liquidity_score = 0.5
            rejection_reasons.append("UNKNOWN_LIQUIDITY: average daily volume not available")

        # ── 6. Portfolio impact ───────────────────────────────
        portfolio_drawdown = portfolio.drawdown
        score.portfolio_impact = portfolio_drawdown   # Higher drawdown → more caution

        if portfolio_drawdown > 0.10:
            rejection_reasons.append(
                f"PORTFOLIO_STRESS: current drawdown is {portfolio_drawdown*100:.1f}%. "
                f"Reducing new position sizes."
            )

        # ── 7. Transaction costs ──────────────────────────────
        # If expected net return is less than 3× transaction costs → not worthwhile
        score.transaction_cost_pct = transaction_cost_pct
        min_required_return = transaction_cost_pct * 3
        if candidate.signal_strength < min_required_return:
            rejection_reasons.append(
                f"COST_PROHIBITIVE: signal strength {candidate.signal_strength:.3f} "
                f"insufficient to overcome transaction costs ({transaction_cost_pct*100:.3f}%)."
            )

        # ── 8. Regime adjustment ──────────────────────────────
        regime_multiplier = self._regime_multiplier(regime)

        # ── 9. Composite score ────────────────────────────────
        composite = (
            WEIGHTS["opportunity"]     * score.opportunity_score
            + WEIGHTS["risk"]          * score.risk_score
            + WEIGHTS["uncertainty"]   * score.uncertainty_score
            + WEIGHTS["correlation"]   * score.correlation_penalty
            + WEIGHTS["liquidity"]     * score.liquidity_score
            + WEIGHTS["portfolio_impact"] * score.portfolio_impact
            + WEIGHTS["transaction_cost"] * score.transaction_cost_pct * 100
        ) * regime_multiplier

        score.composite_score = max(0.0, min(1.0, composite + 0.5))  # Center around 0.5

        # ── 10. Recommended fraction ──────────────────────────
        recommended_frac = score.composite_score * self._max_frac

        # ── 11. Hard rejection conditions ─────────────────────
        if len(rejection_reasons) >= 2 or max_corr > 0.8:
            return self._zero_allocation(candidate.trade_id, rejection_reasons)

        # Below minimum → ZERO
        if recommended_frac < self._min_frac:
            rejection_reasons.append(
                f"BELOW_MINIMUM: recommended allocation {recommended_frac:.3%} "
                f"is below minimum {self._min_frac:.3%}. Not worth transaction costs."
            )
            return self._zero_allocation(candidate.trade_id, rejection_reasons)

        # Available capital check
        available_capital = portfolio.cash
        approved_notional = min(
            recommended_frac * portfolio_equity,
            available_capital * 0.95,  # Never use more than 95% of cash
        )
        approved_quantity = (
            approved_notional / candidate.proposed_price
            if candidate.proposed_price > 0
            else 0.0
        )

        decision = (
            AllocationDecision.APPROVED
            if approved_quantity >= candidate.proposed_quantity
            else AllocationDecision.REDUCED
        )

        result = AllocationResult(
            trade_id=candidate.trade_id,
            decision=decision,
            approved_quantity=approved_quantity,
            approved_notional=approved_notional,
            rejection_reasons=rejection_reasons,
            risk_metrics={
                "composite_score": score.composite_score,
                "opportunity_score": score.opportunity_score,
                "risk_score": score.risk_score,
                "correlation_penalty": score.correlation_penalty,
                "liquidity_score": score.liquidity_score,
                "regime_multiplier": regime_multiplier,
                "recommended_fraction": recommended_frac,
            },
        )

        self._allocation_log.append(result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _zero_allocation(
        self, trade_id: str, reasons: List[str]
    ) -> AllocationResult:
        result = AllocationResult(
            trade_id=trade_id,
            decision=AllocationDecision.REJECTED,
            approved_quantity=0.0,
            approved_notional=0.0,
            rejection_reasons=reasons,
        )
        self._allocation_log.append(result)
        return result

    @staticmethod
    def _regime_multiplier(regime: MarketRegime) -> float:
        """Scale all allocations by regime risk level."""
        multipliers = {
            MarketRegime.BULL_TREND:      1.0,
            MarketRegime.RECOVERY:        0.9,
            MarketRegime.LOW_VOLATILITY:  0.85,
            MarketRegime.RANGING:         0.75,
            MarketRegime.HIGH_VOLATILITY: 0.50,
            MarketRegime.BEAR_TREND:      0.40,
            MarketRegime.UNKNOWN:         0.30,
            MarketRegime.CRISIS:          0.0,   # No new positions in crisis
        }
        return multipliers.get(regime, 0.3)

    def allocation_history(self) -> List[AllocationResult]:
        return list(self._allocation_log)

    def rejection_rate(self) -> float:
        if not self._allocation_log:
            return 0.0
        rejections = sum(
            1 for r in self._allocation_log
            if r.decision == AllocationDecision.REJECTED
        )
        return rejections / len(self._allocation_log)
