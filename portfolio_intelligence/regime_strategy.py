"""
portfolio_intelligence/regime_strategy.py — Item 54: Regime-Switching Strategy Engine
=======================================================================================

Determines which strategy families are appropriate for the current market regime.

Strategy families:
  TREND | MOMENTUM | MEAN_REVERSION | EVENT_DRIVEN | FUNDAMENTAL | NEWS_DRIVEN

Market regimes:
  BULL_TREND | BEAR_TREND | RANGING | HIGH_VOLATILITY | LOW_VOLATILITY |
  CRISIS | RECOVERY | UNKNOWN

Design principles:
  - Never assume one strategy works universally
  - Different regimes favor different strategies
  - Uncertainty about regime reduces allocation to all strategies
  - In CRISIS regime: all strategies move to minimum allocation or zero
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .models import MarketRegime, StrategyFamily


# ---------------------------------------------------------------------------
# Strategy suitability matrix
# (regime → strategy → suitability score 0..1)
# ---------------------------------------------------------------------------

REGIME_STRATEGY_SUITABILITY: Dict[MarketRegime, Dict[StrategyFamily, float]] = {
    MarketRegime.BULL_TREND: {
        StrategyFamily.TREND:          0.90,
        StrategyFamily.MOMENTUM:       0.85,
        StrategyFamily.MEAN_REVERSION: 0.20,
        StrategyFamily.EVENT_DRIVEN:   0.70,
        StrategyFamily.FUNDAMENTAL:    0.75,
        StrategyFamily.NEWS_DRIVEN:    0.65,
    },
    MarketRegime.BEAR_TREND: {
        StrategyFamily.TREND:          0.70,  # Short bias
        StrategyFamily.MOMENTUM:       0.60,  # Downward momentum
        StrategyFamily.MEAN_REVERSION: 0.25,
        StrategyFamily.EVENT_DRIVEN:   0.60,
        StrategyFamily.FUNDAMENTAL:    0.50,
        StrategyFamily.NEWS_DRIVEN:    0.70,  # Negative catalysts
    },
    MarketRegime.RANGING: {
        StrategyFamily.TREND:          0.20,
        StrategyFamily.MOMENTUM:       0.30,
        StrategyFamily.MEAN_REVERSION: 0.85,
        StrategyFamily.EVENT_DRIVEN:   0.75,
        StrategyFamily.FUNDAMENTAL:    0.70,
        StrategyFamily.NEWS_DRIVEN:    0.55,
    },
    MarketRegime.HIGH_VOLATILITY: {
        StrategyFamily.TREND:          0.30,
        StrategyFamily.MOMENTUM:       0.25,
        StrategyFamily.MEAN_REVERSION: 0.40,
        StrategyFamily.EVENT_DRIVEN:   0.65,
        StrategyFamily.FUNDAMENTAL:    0.40,
        StrategyFamily.NEWS_DRIVEN:    0.70,
    },
    MarketRegime.LOW_VOLATILITY: {
        StrategyFamily.TREND:          0.60,
        StrategyFamily.MOMENTUM:       0.55,
        StrategyFamily.MEAN_REVERSION: 0.70,
        StrategyFamily.EVENT_DRIVEN:   0.60,
        StrategyFamily.FUNDAMENTAL:    0.75,
        StrategyFamily.NEWS_DRIVEN:    0.45,
    },
    MarketRegime.CRISIS: {
        StrategyFamily.TREND:          0.10,
        StrategyFamily.MOMENTUM:       0.10,
        StrategyFamily.MEAN_REVERSION: 0.05,
        StrategyFamily.EVENT_DRIVEN:   0.20,
        StrategyFamily.FUNDAMENTAL:    0.15,
        StrategyFamily.NEWS_DRIVEN:    0.30,
    },
    MarketRegime.RECOVERY: {
        StrategyFamily.TREND:          0.65,
        StrategyFamily.MOMENTUM:       0.70,
        StrategyFamily.MEAN_REVERSION: 0.40,
        StrategyFamily.EVENT_DRIVEN:   0.80,
        StrategyFamily.FUNDAMENTAL:    0.85,
        StrategyFamily.NEWS_DRIVEN:    0.75,
    },
    MarketRegime.UNKNOWN: {
        StrategyFamily.TREND:          0.25,
        StrategyFamily.MOMENTUM:       0.25,
        StrategyFamily.MEAN_REVERSION: 0.25,
        StrategyFamily.EVENT_DRIVEN:   0.35,
        StrategyFamily.FUNDAMENTAL:    0.35,
        StrategyFamily.NEWS_DRIVEN:    0.30,
    },
}

# Minimum suitability score to activate a strategy
ACTIVATION_THRESHOLD = 0.50


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class RegimeStrategyDecision:
    regime: MarketRegime
    regime_confidence: float          # How confident are we in the regime classification
    active_strategies: List[StrategyFamily]
    inactive_strategies: List[StrategyFamily]
    suitability_scores: Dict[str, float]
    allocation_multipliers: Dict[str, float]  # Scale factor for position sizing
    rationale: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RegimeStrategyEngine:
    """
    Determines which strategies are appropriate for the current market regime.

    Usage
    -----
    engine = RegimeStrategyEngine()
    decision = engine.evaluate(regime=MarketRegime.BULL_TREND, confidence=0.8)
    """

    def __init__(
        self,
        activation_threshold: float = ACTIVATION_THRESHOLD,
        crisis_override: bool = True,
    ) -> None:
        self._threshold = activation_threshold
        self._crisis_override = crisis_override
        self._history: List[RegimeStrategyDecision] = []

    def evaluate(
        self,
        regime: MarketRegime,
        regime_confidence: float,
    ) -> RegimeStrategyDecision:
        """
        Evaluate which strategies are active for the current regime.

        Parameters
        ----------
        regime            : Current market regime classification.
        regime_confidence : Confidence [0, 1] in the regime classification.
                            Low confidence reduces all allocation multipliers.
        """
        warnings: List[str] = []

        # Scale threshold by confidence (higher uncertainty → fewer active strategies)
        effective_threshold = self._threshold + (1.0 - regime_confidence) * 0.3

        suitability = REGIME_STRATEGY_SUITABILITY.get(regime, REGIME_STRATEGY_SUITABILITY[MarketRegime.UNKNOWN])

        active: List[StrategyFamily] = []
        inactive: List[StrategyFamily] = []
        multipliers: Dict[str, float] = {}
        scores: Dict[str, float] = {}

        for strategy, score in suitability.items():
            scores[strategy.value] = score
            # Confidence-adjusted score
            adj_score = score * regime_confidence
            multipliers[strategy.value] = adj_score

            if adj_score >= effective_threshold:
                active.append(strategy)
            else:
                inactive.append(strategy)

        # Crisis override: drastically reduce everything
        if regime == MarketRegime.CRISIS and self._crisis_override:
            active = []  # No strategies active in crisis
            warnings.append(
                "⚠️  CRISIS regime detected. All strategy allocations set to ZERO. "
                "System will not generate new positions until regime normalises."
            )
            multipliers = {k: 0.0 for k in multipliers}

        if regime == MarketRegime.UNKNOWN:
            warnings.append(
                "Regime is UNKNOWN — using minimal allocations. "
                "Prefer NO TRADE until regime is classifiable."
            )

        if regime_confidence < 0.5:
            warnings.append(
                f"Regime confidence is low ({regime_confidence:.0%}). "
                "Allocation multipliers are significantly reduced."
            )

        rationale = self._build_rationale(regime, regime_confidence, active, inactive)

        decision = RegimeStrategyDecision(
            regime=regime,
            regime_confidence=regime_confidence,
            active_strategies=active,
            inactive_strategies=inactive,
            suitability_scores=scores,
            allocation_multipliers=multipliers,
            rationale=rationale,
            warnings=warnings,
        )

        self._history.append(decision)
        return decision

    def is_strategy_active(
        self,
        strategy: StrategyFamily,
        regime: MarketRegime,
        confidence: float = 1.0,
    ) -> bool:
        """Quick check: is a specific strategy active for this regime?"""
        decision = self.evaluate(regime, confidence)
        return strategy in decision.active_strategies

    def _build_rationale(
        self,
        regime: MarketRegime,
        confidence: float,
        active: List[StrategyFamily],
        inactive: List[StrategyFamily],
    ) -> str:
        active_names = [s.value for s in active]
        inactive_names = [s.value for s in inactive]
        return (
            f"Regime: {regime.value} (confidence: {confidence:.0%}). "
            f"Active strategies: {', '.join(active_names) or 'NONE'}. "
            f"Inactive strategies: {', '.join(inactive_names) or 'NONE'}."
        )

    def history(self) -> List[RegimeStrategyDecision]:
        return list(self._history)
