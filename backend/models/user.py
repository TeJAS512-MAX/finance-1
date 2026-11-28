"""
models/user.py — User accounts and alerts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Application user."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    # viewer | analyst | trader | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB)


class Alert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """System alert sent to users."""
    __tablename__ = "alerts"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # None = broadcast to all
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # NEW_HIGH_IMPACT_EVENT | MULTI_SOURCE_CONFIRMATION | MAJOR_CONTRADICTION |
    # PRICE_ANOMALY | VOLUME_ANOMALY | THESIS_INVALIDATION | RISK_LIMIT_REACHED |
    # PORTFOLIO_DRAWDOWN | SYSTEM_FAILURE
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    channels: Mapped[Optional[list]] = mapped_column(JSONB)  # ["email", "browser"]
    reference_id: Mapped[Optional[str]] = mapped_column(String(100))
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
