"""
tests/test_information_decay.py — Information decay model tests.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portfolio_intelligence.information_decay import InformationDecayEngine
from portfolio_intelligence.models import InformationEvent


def make_event(event_type: str = "news", hours_ago: float = 0.0, **kwargs) -> InformationEvent:
    pub = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return InformationEvent(
        event_type=event_type,
        headline="Test headline",
        publication_time=pub,
        **kwargs,
    )


def test_fresh_event_has_high_relevance() -> None:
    engine = InformationDecayEngine()
    event = make_event("earnings", hours_ago=0.1)
    engine.register(event)
    rel = engine.get_relevance(event.event_id)
    assert rel > 0.95, f"Fresh event should be ~1.0, got {rel}"


def test_old_news_decays_significantly() -> None:
    engine = InformationDecayEngine()
    event = make_event("news", hours_ago=48.0)  # 48h old news (half-life=6h)
    engine.register(event)
    rel = engine.get_relevance(event.event_id)
    assert rel < 0.01, f"48h old news should be near 0, got {rel}"


def test_earnings_decays_slower_than_news() -> None:
    engine = InformationDecayEngine()
    hours_ago = 24.0
    earnings_event = make_event("earnings", hours_ago=hours_ago)
    news_event = make_event("news", hours_ago=hours_ago)
    engine.register(earnings_event)
    engine.register(news_event)

    earnings_rel = engine.get_relevance(earnings_event.event_id)
    news_rel = engine.get_relevance(news_event.event_id)
    assert earnings_rel > news_rel, "Earnings should decay slower than news"


def test_material_event_has_floor() -> None:
    engine = InformationDecayEngine()
    # Very old event (1000 hours)
    event = make_event("news", hours_ago=1000.0, is_materially_important=True)
    engine.register(event)
    rel = engine.get_relevance(event.event_id)
    assert rel >= 0.05, f"Material events must never decay below 5%, got {rel}"


def test_contradiction_reduces_relevance() -> None:
    engine = InformationDecayEngine()
    primary = make_event("earnings", hours_ago=1.0)
    contra = make_event("news", hours_ago=0.5)
    engine.register(primary)
    engine.register(contra)

    rel_before = engine.get_relevance(primary.event_id)
    engine.apply_contradiction(primary.event_id, contra.event_id, severity=0.8)
    rel_after = engine.get_relevance(primary.event_id)

    assert rel_after < rel_before, "Contradiction must reduce relevance"


def test_active_events_filtered_by_min_relevance() -> None:
    engine = InformationDecayEngine()
    fresh = make_event("earnings", hours_ago=1.0)
    stale = make_event("news", hours_ago=100.0)
    engine.register(fresh)
    engine.register(stale)

    active = engine.active_events(min_relevance=0.5)
    ids = [e.event_id for e in active]
    assert fresh.event_id in ids
    assert stale.event_id not in ids


def test_summary_returns_sorted_by_relevance() -> None:
    engine = InformationDecayEngine()
    old = make_event("news", hours_ago=48.0)
    fresh = make_event("earnings", hours_ago=0.1)
    engine.register(old)
    engine.register(fresh)

    summary = engine.summary()
    assert summary[0]["relevance"] >= summary[1]["relevance"]
