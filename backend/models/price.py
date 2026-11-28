"""
models/price.py — OHLCV price history and corporate actions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float,
    ForeignKey, Integer, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Price(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily OHLCV price bar."""
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("symbol_id", "date", "timeframe", name="uq_price_symbol_date_tf"),
    )

    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1D")  # 1D, 1H, 15m
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_close: Mapped[float] = mapped_column(Float, nullable=True)
    vwap: Mapped[float] = mapped_column(Float, nullable=True)
    trades: Mapped[int] = mapped_column(Integer, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), default="yfinance")
    is_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)

    symbol: Mapped["Symbol"] = relationship("Symbol", back_populates="prices")


class CorporateAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Dividends, splits, bonus issues, rights, etc."""
    __tablename__ = "corporate_actions"

    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # action_type: DIVIDEND | SPLIT | BONUS | RIGHTS | MERGER
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)   # Dividend amount or ratio
    ratio: Mapped[float] = mapped_column(Float, nullable=True)    # Split ratio
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    announcement_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=True)


class IndexConstituent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Index membership (e.g., Nifty 50, Sensex)."""
    __tablename__ = "index_constituents"

    index_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, nullable=True)
    added_date: Mapped[date] = mapped_column(Date, nullable=True)
    removed_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


from models.company import Symbol  # noqa: E402
