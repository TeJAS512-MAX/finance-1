"""
models/news.py — News, sources, deduplication clusters, and embeddings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NewsSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Source credibility registry.
    Reputation is updated dynamically over time.
    """
    __tablename__ = "news_sources"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="India")
    language: Mapped[str] = mapped_column(String(10), default="en")
    source_type: Mapped[str] = mapped_column(String(50))
    # source_type: EXCHANGE | REGULATOR | NEWS_AGENCY | FINANCIAL_NEWS | BLOG | SOCIAL

    # Credibility metrics (updated dynamically)
    credibility_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0..1
    historical_accuracy: Mapped[float] = mapped_column(Float, default=0.5)
    originality_score: Mapped[float] = mapped_column(Float, default=0.5)
    correction_rate: Mapped[float] = mapped_column(Float, default=0.0)
    confirmation_rate: Mapped[float] = mapped_column(Float, default=0.0)
    duplicate_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_articles: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_scoops: Mapped[int] = mapped_column(Integer, default=0)
    is_primary_source: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem", back_populates="source")


class NewsItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A single news article or disclosure.

    Contains every required metadata field from the spec:
    source, source_url, publisher, published_at, retrieved_at,
    company, event_type, text/content, language, credibility_score,
    verification_status, duplicate_group, embedding, sentiment, impact_score.
    """
    __tablename__ = "news_items"

    # ── Provenance ───────────────────────────────────────────
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_sources.id"), nullable=True, index=True
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    original_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # original_published_at = timestamp of ORIGINAL article when this is a republication

    # ── Content ──────────────────────────────────────────────
    headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    event_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    # event_type: EARNINGS | CONTRACT | TENDER | PARTNERSHIP | etc.

    # ── Company linkage ───────────────────────────────────────
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )
    mentioned_companies: Mapped[Optional[list]] = mapped_column(ARRAY(String))

    # ── Quality / Verification ───────────────────────────────
    credibility_score: Mapped[float] = mapped_column(Float, default=0.5)
    verification_status: Mapped[str] = mapped_column(
        String(30), default="UNVERIFIED_RUMOUR"
    )
    # VERIFIED | MULTI_SOURCE_CONFIRMED | SINGLE_SOURCE |
    # UNVERIFIED_RUMOUR | CONTRADICTED | RETRACTED | STALE
    information_type: Mapped[str] = mapped_column(String(30), default="UNVERIFIED_PUBLIC_RUMOUR")
    # VERIFIED_PUBLIC | UNVERIFIED_PUBLIC_RUMOUR | ANALYST_OPINION |
    # AI_INFERENCE | HISTORICAL | REAL_TIME_MARKET

    # ── Deduplication ────────────────────────────────────────
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_clusters.id"), nullable=True, index=True
    )
    is_original: Mapped[bool] = mapped_column(Boolean, default=True)
    # False = this is a republication of another article
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # ── AI / ML outputs ──────────────────────────────────────
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)   # -1..+1
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20))
    impact_score: Mapped[Optional[float]] = mapped_column(Float)       # 0..1
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)    # 0..1 (decays over time)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))    # pgvector

    # ── Early signal tracking ─────────────────────────────────
    first_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    early_signal_score: Mapped[Optional[float]] = mapped_column(Float)

    # ── Metadata ─────────────────────────────────────────────
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    source: Mapped[Optional["NewsSource"]] = relationship("NewsSource", back_populates="news_items")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="news_items")
    cluster: Mapped[Optional["EventCluster"]] = relationship("EventCluster", back_populates="news_items")


class EventCluster(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Deduplication cluster: groups multiple articles about the same event.

    10 articles, 3 original sources → 1 EventCluster.
    """
    __tablename__ = "event_clusters"

    event_type: Mapped[Optional[str]] = mapped_column(String(50))
    canonical_headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_articles: Mapped[int] = mapped_column(Integer, default=1)
    independent_sources: Mapped[int] = mapped_column(Integer, default=1)
    # NOTE: independent_sources ≠ total_articles (many sites republish the same story)
    verification_status: Mapped[str] = mapped_column(String(30), default="SINGLE_SOURCE")
    cluster_embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))

    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem", back_populates="cluster")


from models.company import Company  # noqa: E402
