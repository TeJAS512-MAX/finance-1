"""
models/company.py — Company, Symbol, and Exchange ORM models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Exchange(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stock exchange (NSE, BSE, NYSE, etc.)."""
    __tablename__ = "exchanges"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    trading_hours_start: Mapped[Optional[str]] = mapped_column(String(10))   # "09:15"
    trading_hours_end: Mapped[Optional[str]] = mapped_column(String(10))     # "15:30"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    symbols: Mapped[List["Symbol"]] = relationship("Symbol", back_populates="exchange")


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Master company record — exchange-agnostic."""
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(50), default="India")
    headquarters: Mapped[Optional[str]] = mapped_column(String(255))
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    website: Mapped[Optional[str]] = mapped_column(String(512))
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    symbols: Mapped[List["Symbol"]] = relationship("Symbol", back_populates="company")
    financials: Mapped[List["Financial"]] = relationship("Financial", back_populates="company")
    news_items: Mapped[List["NewsItem"]] = relationship("NewsItem", back_populates="company")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="company")
    relationships_as_source: Mapped[List["CompanyRelationship"]] = relationship(
        "CompanyRelationship",
        foreign_keys="CompanyRelationship.source_company_id",
        back_populates="source_company",
    )
    relationships_as_target: Mapped[List["CompanyRelationship"]] = relationship(
        "CompanyRelationship",
        foreign_keys="CompanyRelationship.target_company_id",
        back_populates="target_company",
    )


class Symbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Ticker symbol on a specific exchange."""
    __tablename__ = "symbols"
    __table_args__ = (
        UniqueConstraint("ticker", "exchange_id", name="uq_ticker_exchange"),
    )

    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False
    )
    isin: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[float] = mapped_column(Float, default=0.05)
    market_cap: Mapped[Optional[float]] = mapped_column(Float)
    float_shares: Mapped[Optional[float]] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_price: Mapped[Optional[float]] = mapped_column(Float)
    last_price_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship("Company", back_populates="symbols")
    exchange: Mapped["Exchange"] = relationship("Exchange", back_populates="symbols")
    prices: Mapped[List["Price"]] = relationship("Price", back_populates="symbol")


class CompanyRelationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Knowledge graph edge between two companies.

    Every edge has a type, confidence, source, date, and evidence.
    Inferred relationships are clearly flagged as such.
    """
    __tablename__ = "company_relationships"

    source_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    target_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SUPPLIES_TO, CUSTOMER_OF, COMPETES_WITH, etc.
    confidence: Mapped[float] = mapped_column(Float, nullable=False)   # 0..1
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    evidence: Mapped[Optional[str]] = mapped_column(Text)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    source_company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[source_company_id],
        back_populates="relationships_as_source",
    )
    target_company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[target_company_id],
        back_populates="relationships_as_target",
    )


# ── Import guard for circular refs ───────────────────────────
from models.price import Price           # noqa: E402  (circular-safe at bottom)
from models.fundamental import Financial # noqa: E402
from models.news import NewsItem         # noqa: E402
from models.event import Event           # noqa: E402
