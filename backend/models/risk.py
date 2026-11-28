"""
models/risk.py — Risk events, circuit breakers, and audit logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Recorded risk or emergency event.

    Triggers: UNEXPECTED_API_BEHAVIOR | ABNORMAL_ORDER_FREQUENCY |
    DATA_CORRUPTION | STALE_PRICES | MODEL_FAILURE | EXCESSIVE_LOSSES |
    UNEXPECTED_PORTFOLIO_EXPOSURE | DUPLICATE_ORDERS | BROKER_CONNECTIVITY
    """
    __tablename__ = "risk_events"

    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="HIGH")  # LOW|MEDIUM|HIGH|CRITICAL
    description: Mapped[str] = mapped_column(Text, nullable=False)
    portfolio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, default=True)
    kill_switch_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)


class BacktestRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Backtest run record with full research report fields (spec Item 57).
    """
    __tablename__ = "backtest_runs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)

    # Data period
    data_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_sources: Mapped[Optional[list]] = mapped_column(JSONB)
    features_used: Mapped[Optional[list]] = mapped_column(JSONB)
    model_version: Mapped[Optional[str]] = mapped_column(String(100))
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Cost assumptions
    commission_pct: Mapped[float] = mapped_column(Float, default=0.03)
    slippage_pct: Mapped[float] = mapped_column(Float, default=0.05)

    # Train / val / test splits
    train_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    train_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    validation_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    validation_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    test_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    test_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Performance metrics
    total_return_pct: Mapped[Optional[float]] = mapped_column(Float)
    cagr_pct: Mapped[Optional[float]] = mapped_column(Float)
    volatility_pct: Mapped[Optional[float]] = mapped_column(Float)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(Float)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Float)
    profit_factor: Mapped[Optional[float]] = mapped_column(Float)
    win_rate_pct: Mapped[Optional[float]] = mapped_column(Float)
    expectancy: Mapped[Optional[float]] = mapped_column(Float)
    total_trades: Mapped[Optional[int]] = mapped_column(Integer)
    oos_total_return_pct: Mapped[Optional[float]] = mapped_column(Float)  # Out-of-sample
    oos_sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # Research report
    limitations: Mapped[Optional[str]] = mapped_column(Text)
    report_path: Mapped[Optional[str]] = mapped_column(String(512))
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(100))

    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # PENDING | RUNNING | COMPLETED | FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    DISCLAIMER: str = (
        "BACKTEST RESULTS DO NOT GUARANTEE FUTURE PERFORMANCE. "
        "Past performance of any strategy is not indicative of future results."
    )


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit trail.
    Every significant action is recorded here.
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "audit"}

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    request_id: Mapped[Optional[str]] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(20), default="SUCCESS")  # SUCCESS | FAILURE
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)
