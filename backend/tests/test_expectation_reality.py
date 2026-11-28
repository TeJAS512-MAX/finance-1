"""
tests/test_expectation_reality.py — Expectation vs Reality engine tests.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portfolio_intelligence.expectation_reality import (
    ExpectationRealityEngine,
    MarketReaction,
    ReactionAlignment,
)
from portfolio_intelligence.models import CatalystEvent, ExpectationResult


def make_event(**kwargs) -> CatalystEvent:
    return CatalystEvent(
        event_type="earnings",
        symbol="RELIANCE",
        **kwargs,
    )


@pytest.fixture
def engine() -> ExpectationRealityEngine:
    return ExpectationRealityEngine()


def test_beat_classification(engine: ExpectationRealityEngine) -> None:
    event = make_event(
        actual_result=110.0,
        market_expectation=100.0,    # +10% → BEAT
        analyst_consensus=105.0,     # +4.8% → BEAT
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.BEAT


def test_miss_classification(engine: ExpectationRealityEngine) -> None:
    event = make_event(
        actual_result=90.0,
        market_expectation=100.0,    # -10% → MISS
        analyst_consensus=98.0,      # -8.2% → MISS
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.MISS


def test_in_line_classification(engine: ExpectationRealityEngine) -> None:
    event = make_event(
        actual_result=101.0,
        market_expectation=100.0,    # +1% → IN_LINE
        analyst_consensus=100.5,     # +0.5% → IN_LINE
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.IN_LINE


def test_uncertain_with_no_benchmarks(engine: ExpectationRealityEngine) -> None:
    event = make_event(actual_result=100.0)  # No benchmarks provided
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.UNCERTAIN


def test_uncertain_with_no_actual_result(engine: ExpectationRealityEngine) -> None:
    event = make_event(market_expectation=100.0)  # No actual result
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.UNCERTAIN


def test_positive_result_absolute_not_enough_for_beat(engine: ExpectationRealityEngine) -> None:
    """
    CRITICAL: A positive absolute number should NOT classify as BEAT
    if it missed expectations.
    """
    event = make_event(
        actual_result=50.0,         # Positive absolute value
        market_expectation=100.0,   # But massively missed expectations
        analyst_consensus=95.0,
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.MISS, (
        "Positive absolute result that misses expectations must be classified as MISS, not BEAT"
    )


def test_sell_the_news_detection(engine: ExpectationRealityEngine) -> None:
    """BEAT + negative market reaction = SELL_THE_NEWS."""
    event = make_event(
        actual_result=110.0,
        market_expectation=100.0,
        analyst_consensus=105.0,
        market_reaction_pct=-2.0,  # Stock fell despite beat
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.BEAT
    assert result.reaction_alignment == ReactionAlignment.SELL_THE_NEWS


def test_buy_the_dip_detection(engine: ExpectationRealityEngine) -> None:
    """MISS + positive market reaction = BUY_THE_DIP."""
    event = make_event(
        actual_result=90.0,
        market_expectation=100.0,
        analyst_consensus=98.0,
        market_reaction_pct=3.5,  # Stock rose despite miss
    )
    result = engine.analyse(event)
    assert result.verdict == ExpectationResult.MISS
    assert result.reaction_alignment == ReactionAlignment.BUY_THE_DIP


def test_beat_rate_calculation(engine: ExpectationRealityEngine) -> None:
    # 2 beats
    for _ in range(2):
        engine.analyse(make_event(
            actual_result=110.0,
            market_expectation=100.0,
            analyst_consensus=105.0,
        ))
    # 1 miss
    engine.analyse(make_event(
        actual_result=85.0,
        market_expectation=100.0,
        analyst_consensus=95.0,
    ))
    rate = engine.beat_rate(symbol="RELIANCE")
    assert abs(rate - 2/3) < 0.01  # ~66.7%


def test_strong_positive_reaction_classification(engine: ExpectationRealityEngine) -> None:
    event = make_event(
        actual_result=110.0,
        market_expectation=100.0,
        analyst_consensus=105.0,
        market_reaction_pct=5.0,  # > 3% = STRONG_POSITIVE
    )
    result = engine.analyse(event)
    assert result.market_reaction == MarketReaction.STRONG_POSITIVE
