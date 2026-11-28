"""
models/trading.py — Orders, Fills, Positions, Portfolio, and Trade Journal.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Portfolio(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Virtual or live portfolio."""
    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="paper")  # paper | live
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Snapshot metrics (updated daily)
    current_cash: Mapped[float] = mapped_column(Float)
    total_equity: Mapped[Optional[float]] = mapped_column(Float)
    total_unrealised_pnl: Mapped[Optional[float]] = mapped_column(Float)
    total_realised_pnl: Mapped[Optional[float]] = mapped_column(Float)
    peak_equity: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float)
    total_return_pct: Mapped[Optional[float]] = mapped_column(Float)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="portfolio")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio")


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An order (paper or live)."""
    __tablename__ = "orders"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True
    )
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False, index=True
    )
    thesis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trade_theses.id"), nullable=True
    )

    order_type: Mapped[str] = mapped_column(String(20))  # MARKET | LIMIT | STOP
    direction: Mapped[str] = mapped_column(String(10))   # BUY | SELL
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    limit_price: Mapped[Optional[float]] = mapped_column(Float)
    stop_price: Mapped[Optional[float]] = mapped_column(Float)
    requested_price: Mapped[Optional[float]] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # PENDING | SUBMITTED | PARTIAL | FILLED | CANCELLED | REJECTED
    filled_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_fill_price: Mapped[Optional[float]] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    # is_paper MUST be True unless LIVE_TRADING_ENABLED=true AND manual confirmation given
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    # Only set for live orders
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(512))
    strategy: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="orders")


class Position(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Current open position in a portfolio."""
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol_id", name="uq_position_portfolio_symbol"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True
    )
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(10))  # LONG | SHORT
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Float)
    market_value: Mapped[Optional[float]] = mapped_column(Float)
    unrealised_pnl: Mapped[Optional[float]] = mapped_column(Float)
    unrealised_pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    realised_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_commission: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk fields
    stop_loss_price: Mapped[Optional[float]] = mapped_column(Float)
    take_profit_price: Mapped[Optional[float]] = mapped_column(Float)
    thesis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trade_theses.id"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")


class TradeThesis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Full AI-generated trade thesis.

    Structured according to spec Item 17.
    """
    __tablename__ = "trade_theses"

    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(10))  # LONG | SHORT | NO_TRADE
    signal: Mapped[str] = mapped_column(String(20))     # BUY | SELL | NO_TRADE

    catalyst_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=True
    )
    catalyst_description: Mapped[Optional[str]] = mapped_column(Text)

    # Evidence (list of source URLs / summaries)
    evidence: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    event_status: Mapped[str] = mapped_column(String(30))
    # VERIFIED | MULTI_SOURCE | UNVERIFIED | CONTRADICTED

    # Analysis fields
    financial_impact: Mapped[Optional[str]] = mapped_column(Text)
    technical_context: Mapped[Optional[str]] = mapped_column(Text)
    market_regime: Mapped[Optional[str]] = mapped_column(String(30))
    priced_in_assessment: Mapped[Optional[str]] = mapped_column(Text)
    bull_case: Mapped[Optional[str]] = mapped_column(Text)
    bear_case: Mapped[Optional[str]] = mapped_column(Text)
    key_risks: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    invalidation_conditions: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    time_horizon: Mapped[Optional[str]] = mapped_column(String(20))  # INTRADAY|SHORT|MEDIUM|LONG
    confidence: Mapped[int] = mapped_column(Integer)    # 0..100

    # Model outputs
    model_agreement_score: Mapped[Optional[float]] = mapped_column(Float)
    source_quality: Mapped[Optional[str]] = mapped_column(String(30))
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text)
    expected_financial_impact: Mapped[Optional[str]] = mapped_column(Text)
    market_reaction_assessment: Mapped[Optional[str]] = mapped_column(Text)
    already_priced_in: Mapped[Optional[str]] = mapped_column(Text)
    fundamental_context: Mapped[Optional[str]] = mapped_column(Text)

    # Outcome tracking (filled after position closes)
    actual_return_pct: Mapped[Optional[float]] = mapped_column(Float)
    thesis_was_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    invalidation_triggered: Mapped[Optional[str]] = mapped_column(String(255))
    thesis_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    # ACTIVE | CLOSED | INVALIDATED | EXPIRED

    generated_by_model: Mapped[str] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_llm_output: Mapped[Optional[dict]] = mapped_column(JSONB)


class TradeJournalEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AI-generated trade journal entry per spec Item 25.

    Records WHY ENTERED, WHAT HAPPENED, WHAT WAS WRONG, LESSON.
    """
    __tablename__ = "trade_journal"

    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False, index=True
    )
    thesis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trade_theses.id"), nullable=True
    )

    why_entered: Mapped[Optional[str]] = mapped_column(Text)
    what_information_caused_entry: Mapped[Optional[str]] = mapped_column(Text)
    what_ai_expected: Mapped[Optional[str]] = mapped_column(Text)
    what_actually_happened: Mapped[Optional[str]] = mapped_column(Text)
    what_changed: Mapped[Optional[str]] = mapped_column(Text)
    why_exited: Mapped[Optional[str]] = mapped_column(Text)
    what_was_wrong: Mapped[Optional[str]] = mapped_column(Text)
    what_was_right: Mapped[Optional[str]] = mapped_column(Text)
    lesson: Mapped[Optional[str]] = mapped_column(Text)
    market_regime_at_entry: Mapped[Optional[str]] = mapped_column(String(30))
    market_regime_at_exit: Mapped[Optional[str]] = mapped_column(String(30))
    entry_confidence: Mapped[Optional[int]] = mapped_column(Integer)
    realised_pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    holding_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Counterfactual analysis
    counterfactual_result: Mapped[Optional[str]] = mapped_column(Text)
    # "What if system had not traded?"
    counterfactual_no_trade_outcome_pct: Mapped[Optional[float]] = mapped_column(Float)
    what_evidence_would_change_decision: Mapped[Optional[str]] = mapped_column(Text)


from models.user import User            # noqa: E402
