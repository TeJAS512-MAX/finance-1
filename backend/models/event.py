"""
models/event.py — Market event detection and tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A detected market-moving event.

    Categories: EARNINGS | CONTRACT | TENDER | PARTNERSHIP | ACQUISITION |
    INVESTMENT | PRODUCT_LAUNCH | REGULATORY | LEGAL | MANAGEMENT |
    EXPANSION | CAPACITY | GOVERNMENT_POLICY | COMPETITOR_EVENT |
    SUPPLIER_EVENT | CUSTOMER_EVENT | MACRO_EVENT | OTHER
    """
    __tablename__ = "events"

    # ── Classification ───────────────────────────────────────
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_clusters.id"), nullable=True
    )

    # ── Timing ───────────────────────────────────────────────
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_public_source_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # e.g. earnings date, FOMC meeting

    # ── Confidence / Impact ────────────────────────────────
    event_confidence: Mapped[float] = mapped_column(Float, default=0.5)   # 0..1
    potential_financial_impact: Mapped[Optional[str]] = mapped_column(String(10))  # LOW|MEDIUM|HIGH
    potential_market_impact: Mapped[Optional[str]] = mapped_column(String(10))
    time_horizon: Mapped[Optional[str]] = mapped_column(String(15))       # SHORT|MEDIUM|LONG
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5)

    # ── Source info ────────────────────────────────────────
    primary_source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    independent_sources_count: Mapped[int] = mapped_column(Integer, default=1)
    verification_status: Mapped[str] = mapped_column(String(30), default="SINGLE_SOURCE")

    # ── Market reaction tracking ────────────────────────────
    price_before: Mapped[Optional[float]] = mapped_column(Float)
    price_after: Mapped[Optional[float]] = mapped_column(Float)
    return_before_event: Mapped[Optional[float]] = mapped_column(Float)   # abnormal return
    return_after_event: Mapped[Optional[float]] = mapped_column(Float)
    volume_change_pct: Mapped[Optional[float]] = mapped_column(Float)
    abnormal_return: Mapped[Optional[float]] = mapped_column(Float)
    priced_in_score: Mapped[Optional[float]] = mapped_column(Float)       # 0..1
    event_surprise_score: Mapped[Optional[float]] = mapped_column(Float)  # 0..1

    # ── Earnings / expectation specific ─────────────────────
    market_expectation: Mapped[Optional[float]] = mapped_column(Float)
    analyst_consensus: Mapped[Optional[float]] = mapped_column(Float)
    previous_guidance: Mapped[Optional[float]] = mapped_column(Float)
    actual_result: Mapped[Optional[float]] = mapped_column(Float)
    expectation_verdict: Mapped[Optional[str]] = mapped_column(String(15))
    # BEAT | IN_LINE | MISS | UNCERTAIN
    market_reaction_pct: Mapped[Optional[float]] = mapped_column(Float)
    reaction_speed_ms: Mapped[Optional[float]] = mapped_column(Float)
    reaction_alignment: Mapped[Optional[str]] = mapped_column(String(30))

    # ── Description ───────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="events")


from models.company import Company       # noqa: E402
from models.news import EventCluster     # noqa: E402
