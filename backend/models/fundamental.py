"""
models/fundamental.py — Financial statements and fundamental data.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import (
    Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Financial(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Quarterly / Annual financial statement data.

    Stores income statement, balance sheet, and cash flow line items.
    All amounts in reporting currency (default INR crores for Indian companies).
    """
    __tablename__ = "financials"
    __table_args__ = (
        UniqueConstraint("company_id", "period", "period_type", "statement_type",
                         name="uq_financial_period"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)  # Quarter or Year end date
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)  # Q | A (quarterly/annual)
    statement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # INCOME | BALANCE_SHEET | CASH_FLOW | RATIOS
    fiscal_year: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    unit: Mapped[str] = mapped_column(String(20), default="crores")  # crores | millions | billions
    source: Mapped[str] = mapped_column(String(100))
    is_audited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_restated: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Income Statement ──────────────────────────────────────
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    gross_profit: Mapped[Optional[float]] = mapped_column(Float)
    ebitda: Mapped[Optional[float]] = mapped_column(Float)
    ebit: Mapped[Optional[float]] = mapped_column(Float)
    net_income: Mapped[Optional[float]] = mapped_column(Float)
    eps: Mapped[Optional[float]] = mapped_column(Float)
    eps_diluted: Mapped[Optional[float]] = mapped_column(Float)
    gross_margin: Mapped[Optional[float]] = mapped_column(Float)
    ebitda_margin: Mapped[Optional[float]] = mapped_column(Float)
    net_margin: Mapped[Optional[float]] = mapped_column(Float)

    # ── Balance Sheet ─────────────────────────────────────────
    total_assets: Mapped[Optional[float]] = mapped_column(Float)
    total_equity: Mapped[Optional[float]] = mapped_column(Float)
    total_debt: Mapped[Optional[float]] = mapped_column(Float)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Float)
    net_debt: Mapped[Optional[float]] = mapped_column(Float)
    current_ratio: Mapped[Optional[float]] = mapped_column(Float)
    debt_to_equity: Mapped[Optional[float]] = mapped_column(Float)

    # ── Cash Flow ─────────────────────────────────────────────
    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    capex: Mapped[Optional[float]] = mapped_column(Float)
    free_cash_flow: Mapped[Optional[float]] = mapped_column(Float)
    cash_conversion: Mapped[Optional[float]] = mapped_column(Float)

    # ── Valuation Ratios ──────────────────────────────────────
    pe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    pb_ratio: Mapped[Optional[float]] = mapped_column(Float)
    ps_ratio: Mapped[Optional[float]] = mapped_column(Float)
    ev_ebitda: Mapped[Optional[float]] = mapped_column(Float)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    roce: Mapped[Optional[float]] = mapped_column(Float)
    roa: Mapped[Optional[float]] = mapped_column(Float)

    # ── Growth ────────────────────────────────────────────────
    revenue_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    earnings_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)

    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    company: Mapped["Company"] = relationship("Company", back_populates="financials")


class Guidance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company management guidance for future periods."""
    __tablename__ = "guidance"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)  # "Revenue", "EPS"
    guidance_type: Mapped[str] = mapped_column(String(20))  # POINT | RANGE | QUALITATIVE
    low_value: Mapped[Optional[float]] = mapped_column(Float)
    high_value: Mapped[Optional[float]] = mapped_column(Float)
    midpoint_value: Mapped[Optional[float]] = mapped_column(Float)
    qualitative: Mapped[Optional[str]] = mapped_column(String(255))
    period: Mapped[str] = mapped_column(String(20))  # "Q3FY25", "FY2026"
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))


from models.company import Company  # noqa: E402
