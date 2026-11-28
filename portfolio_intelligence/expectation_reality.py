"""
expectation_reality.py — Item 52: Expectation vs Reality Engine
================================================================

For every measurable event (earnings, guidance, contracts, macro data):

  1. Compare actual result against multiple expectation benchmarks:
       - market_expectation      (implied by options / futures)
       - analyst_consensus       (publicly available)
       - previous_guidance       (company's own prior forecast)

  2. Classify the outcome:
       BEAT | IN_LINE | MISS | UNCERTAIN

  3. Measure and classify the market reaction:
       STRONG_POSITIVE | POSITIVE | NEUTRAL | NEGATIVE | STRONG_NEGATIVE

  4. Flag "sell-the-news" or "buy-the-dip" setups where the reaction
     diverges from the fundamental verdict.

Classification thresholds are configurable per event type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .models import CatalystEvent, ExpectationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MarketReaction(Enum):
    STRONG_POSITIVE = "strong_positive"   # > +3 %
    POSITIVE        = "positive"          # +1 % to +3 %
    NEUTRAL         = "neutral"           # -1 % to +1 %
    NEGATIVE        = "negative"          # -3 % to -1 %
    STRONG_NEGATIVE = "strong_negative"   # < -3 %


class ReactionAlignment(Enum):
    ALIGNED          = "aligned"           # reaction matches verdict
    SELL_THE_NEWS    = "sell_the_news"     # BEAT but negative reaction
    BUY_THE_DIP      = "buy_the_dip"       # MISS but positive reaction
    MUTED_BEAT       = "muted_beat"        # BEAT but only neutral reaction
    MUTED_MISS       = "muted_miss"        # MISS but only neutral reaction
    UNCERTAIN_SIGNAL = "uncertain_signal"  # UNCERTAIN verdict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ExpectationThresholds:
    """Configurable thresholds for beat/miss classification."""
    beat_pct:      float = 2.0    # must exceed expectation by this %
    miss_pct:      float = -2.0   # must fall below expectation by this %
    uncertain_min: int   = 2      # minimum benchmarks required for certainty
    reaction_strong_pos: float = 3.0
    reaction_pos:        float = 1.0
    reaction_neg:        float = -1.0
    reaction_strong_neg: float = -3.0


DEFAULT_THRESHOLDS: Dict[str, ExpectationThresholds] = {
    "earnings":       ExpectationThresholds(beat_pct=2.0,  miss_pct=-2.0),
    "guidance":       ExpectationThresholds(beat_pct=1.0,  miss_pct=-1.0),
    "macro":          ExpectationThresholds(beat_pct=0.5,  miss_pct=-0.5),
    "contract":       ExpectationThresholds(beat_pct=5.0,  miss_pct=-5.0),
    "default":        ExpectationThresholds(),
}


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

@dataclass
class ExpectationAnalysis:
    event_id: str
    symbol: Optional[str]
    event_type: str
    verdict: ExpectationResult
    market_reaction: Optional[MarketReaction]
    reaction_alignment: Optional[ReactionAlignment]
    beat_pct_vs_market:  Optional[float]       # % vs market expectation
    beat_pct_vs_analyst: Optional[float]       # % vs analyst consensus
    beat_pct_vs_guidance: Optional[float]      # % vs prior guidance
    composite_beat_pct:  Optional[float]       # average across available
    reaction_pct:        Optional[float]
    analysis_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ExpectationRealityEngine:
    """
    Analyses measurable events and classifies them as BEAT / IN_LINE /
    MISS / UNCERTAIN, then evaluates the market reaction alignment.

    Usage
    -----
    engine = ExpectationRealityEngine()
    result = engine.analyse(catalyst_event)
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, ExpectationThresholds]] = None,
    ) -> None:
        self._thresholds = thresholds or DEFAULT_THRESHOLDS
        self._history: List[ExpectationAnalysis] = []

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyse(self, event: CatalystEvent) -> ExpectationAnalysis:
        """
        Analyse a CatalystEvent and return an ExpectationAnalysis.

        The event must have `actual_result` set.  At least one of
        market_expectation, analyst_consensus, or previous_guidance is
        required for a non-UNCERTAIN verdict.
        """
        thresh = self._get_thresholds(event.event_type)
        notes: List[str] = []

        if event.actual_result is None:
            notes.append("actual_result not available — verdict UNCERTAIN")
            analysis = ExpectationAnalysis(
                event_id=event.event_id,
                symbol=event.symbol,
                event_type=event.event_type,
                verdict=ExpectationResult.UNCERTAIN,
                market_reaction=self._classify_reaction(event.market_reaction_pct, thresh),
                reaction_alignment=None,
                beat_pct_vs_market=None,
                beat_pct_vs_analyst=None,
                beat_pct_vs_guidance=None,
                composite_beat_pct=None,
                reaction_pct=event.market_reaction_pct,
                notes=notes,
            )
            self._history.append(analysis)
            return analysis

        actual = event.actual_result
        deltas: List[float] = []

        # vs market expectation
        d_market: Optional[float] = None
        if event.market_expectation is not None and event.market_expectation != 0:
            d_market = (actual - event.market_expectation) / abs(event.market_expectation) * 100
            deltas.append(d_market)
            notes.append(f"vs market: {d_market:+.2f}%")

        # vs analyst consensus
        d_analyst: Optional[float] = None
        if event.analyst_consensus is not None and event.analyst_consensus != 0:
            d_analyst = (actual - event.analyst_consensus) / abs(event.analyst_consensus) * 100
            deltas.append(d_analyst)
            notes.append(f"vs analyst: {d_analyst:+.2f}%")

        # vs previous guidance
        d_guidance: Optional[float] = None
        if event.previous_guidance is not None and event.previous_guidance != 0:
            d_guidance = (actual - event.previous_guidance) / abs(event.previous_guidance) * 100
            deltas.append(d_guidance)
            notes.append(f"vs guidance: {d_guidance:+.2f}%")

        # Verdict
        if len(deltas) < thresh.uncertain_min:
            verdict = ExpectationResult.UNCERTAIN
            notes.append(
                f"Only {len(deltas)} benchmark(s) available "
                f"(need {thresh.uncertain_min}) — UNCERTAIN"
            )
            composite = sum(deltas) / len(deltas) if deltas else None
        else:
            composite = sum(deltas) / len(deltas)
            verdict = self._classify_verdict(composite, thresh)
            notes.append(f"composite delta: {composite:+.2f}% → {verdict.value}")

        # Market reaction
        reaction = self._classify_reaction(event.market_reaction_pct, thresh)
        alignment = self._classify_alignment(verdict, reaction)

        if alignment in (ReactionAlignment.SELL_THE_NEWS, ReactionAlignment.BUY_THE_DIP):
            notes.append(f"⚠️  Reaction divergence detected: {alignment.value}")

        analysis = ExpectationAnalysis(
            event_id=event.event_id,
            symbol=event.symbol,
            event_type=event.event_type,
            verdict=verdict,
            market_reaction=reaction,
            reaction_alignment=alignment,
            beat_pct_vs_market=d_market,
            beat_pct_vs_analyst=d_analyst,
            beat_pct_vs_guidance=d_guidance,
            composite_beat_pct=composite,
            reaction_pct=event.market_reaction_pct,
            notes=notes,
        )

        # Store on the event itself
        event.expectation_result = verdict

        self._history.append(analysis)
        logger.info(
            "ExpectationReality [%s/%s]: verdict=%s reaction=%s alignment=%s",
            event.symbol, event.event_type, verdict.value,
            reaction.value if reaction else "unknown",
            alignment.value if alignment else "unknown",
        )
        return analysis

    # ------------------------------------------------------------------
    # History queries
    # ------------------------------------------------------------------

    def history(
        self,
        symbol: Optional[str] = None,
        event_type: Optional[str] = None,
        verdict: Optional[ExpectationResult] = None,
    ) -> List[ExpectationAnalysis]:
        results = self._history
        if symbol:
            results = [r for r in results if r.symbol == symbol]
        if event_type:
            results = [r for r in results if r.event_type == event_type]
        if verdict:
            results = [r for r in results if r.verdict == verdict]
        return results

    def beat_rate(self, symbol: Optional[str] = None) -> Optional[float]:
        """Return the fraction of events classified as BEAT (excluding UNCERTAIN)."""
        h = self.history(symbol=symbol)
        definite = [r for r in h if r.verdict != ExpectationResult.UNCERTAIN]
        if not definite:
            return None
        beats = sum(1 for r in definite if r.verdict == ExpectationResult.BEAT)
        return beats / len(definite)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_thresholds(self, event_type: str) -> ExpectationThresholds:
        return self._thresholds.get(event_type, self._thresholds["default"])

    @staticmethod
    def _classify_verdict(
        composite_pct: float,
        thresh: ExpectationThresholds,
    ) -> ExpectationResult:
        if composite_pct >= thresh.beat_pct:
            return ExpectationResult.BEAT
        if composite_pct <= thresh.miss_pct:
            return ExpectationResult.MISS
        return ExpectationResult.IN_LINE

    @staticmethod
    def _classify_reaction(
        reaction_pct: Optional[float],
        thresh: ExpectationThresholds,
    ) -> Optional[MarketReaction]:
        if reaction_pct is None:
            return None
        if reaction_pct >= thresh.reaction_strong_pos:
            return MarketReaction.STRONG_POSITIVE
        if reaction_pct >= thresh.reaction_pos:
            return MarketReaction.POSITIVE
        if reaction_pct <= thresh.reaction_strong_neg:
            return MarketReaction.STRONG_NEGATIVE
        if reaction_pct <= thresh.reaction_neg:
            return MarketReaction.NEGATIVE
        return MarketReaction.NEUTRAL

    @staticmethod
    def _classify_alignment(
        verdict: ExpectationResult,
        reaction: Optional[MarketReaction],
    ) -> Optional[ReactionAlignment]:
        if verdict == ExpectationResult.UNCERTAIN:
            return ReactionAlignment.UNCERTAIN_SIGNAL
        if reaction is None:
            return None
        positive_reaction = reaction in (MarketReaction.STRONG_POSITIVE, MarketReaction.POSITIVE)
        negative_reaction = reaction in (MarketReaction.STRONG_NEGATIVE, MarketReaction.NEGATIVE)
        neutral_reaction  = reaction == MarketReaction.NEUTRAL

        if verdict == ExpectationResult.BEAT:
            if positive_reaction:
                return ReactionAlignment.ALIGNED
            if negative_reaction:
                return ReactionAlignment.SELL_THE_NEWS
            return ReactionAlignment.MUTED_BEAT

        if verdict == ExpectationResult.MISS:
            if negative_reaction:
                return ReactionAlignment.ALIGNED
            if positive_reaction:
                return ReactionAlignment.BUY_THE_DIP
            return ReactionAlignment.MUTED_MISS

        # IN_LINE — neutral is aligned
        if neutral_reaction:
            return ReactionAlignment.ALIGNED
        return ReactionAlignment.ALIGNED  # mild reactions on in-line are also fine
