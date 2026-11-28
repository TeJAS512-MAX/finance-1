"""
tests/test_live_trading_safety.py — CRITICAL safety tests.

These tests verify that live trading CANNOT be activated accidentally.
This test file must ALWAYS pass before any deployment.

Per spec Item 58:
  Live trading must remain disabled by default.
  Require: successful backtest, OOS test, paper trading, risk config,
           manual confirmation before enabling live broker.
  Risk controls must remain outside AI and cannot be disabled by AI.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch


# ── Core safety: LIVE_TRADING_ENABLED must default to False ────

def test_live_trading_disabled_by_default() -> None:
    """
    CRITICAL: LIVE_TRADING_ENABLED must default to False.
    If this test fails, a production deployment could accidentally
    submit real orders.
    """
    # Clear any env override to test the true default
    env_backup = os.environ.pop("LIVE_TRADING_ENABLED", None)
    try:
        from core.config import Settings
        # Create settings WITHOUT any .env file influence
        s = Settings(
            SECRET_KEY="a" * 33,
            JWT_SECRET_KEY="b" * 33,
            DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
        )
        assert s.live_trading_enabled is False, (
            "LIVE_TRADING_ENABLED must default to False. "
            "This is a critical safety requirement."
        )
    finally:
        if env_backup is not None:
            os.environ["LIVE_TRADING_ENABLED"] = env_backup


def test_emergency_kill_switch_disabled_by_default() -> None:
    """Emergency kill switch must default to False (inactive)."""
    from core.config import Settings
    s = Settings(
        SECRET_KEY="a" * 33,
        JWT_SECRET_KEY="b" * 33,
        DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
    )
    assert s.emergency_kill_switch_active is False


# ── PaperBroker cannot submit real orders ──────────────────────

def test_paper_broker_is_paper_always_true() -> None:
    """PaperBroker.is_paper must always return True."""
    from trading.paper_broker import PaperBroker
    broker = PaperBroker(initial_capital=100_000.0)
    assert broker.is_paper is True


@pytest.mark.asyncio
async def test_paper_broker_has_no_real_exchange_connection() -> None:
    """PaperBroker must not have any attribute that connects to a real exchange."""
    from trading.paper_broker import PaperBroker
    broker = PaperBroker()
    # These attributes would indicate a live broker connection
    forbidden_attrs = [
        "api_key", "api_secret", "kite", "upstox", "fyers",
        "zerodha", "live_session", "broker_session",
    ]
    for attr in forbidden_attrs:
        assert not hasattr(broker, attr), (
            f"PaperBroker must not have '{attr}' — this suggests a real broker connection."
        )


@pytest.mark.asyncio
async def test_paper_broker_place_order_does_not_call_external_api() -> None:
    """PaperBroker.place_order must not make any HTTP calls."""
    import httpx
    from trading.paper_broker import PaperBroker

    broker = PaperBroker(initial_capital=1_000_000.0)
    # Patch httpx to detect any outbound calls
    original_get = httpx.get
    original_post = httpx.post
    calls = []

    def mock_get(*a, **kw):
        calls.append(("GET", a, kw))
        raise AssertionError("PaperBroker made an HTTP GET call!")

    def mock_post(*a, **kw):
        calls.append(("POST", a, kw))
        raise AssertionError("PaperBroker made an HTTP POST call!")

    httpx.get = mock_get
    httpx.post = mock_post
    try:
        result = await broker.place_order(
            ticker="RELIANCE",
            direction="BUY",
            quantity=1.0,
            order_type="MARKET",
            price=2500.0,
        )
        assert result["is_paper"] is True
    finally:
        httpx.get = original_get
        httpx.post = original_post

    assert not calls, f"PaperBroker made unexpected HTTP calls: {calls}"


# ── Risk manager blocks live trades when disabled ──────────────

def test_risk_manager_blocks_live_orders_when_disabled() -> None:
    """RiskManager must raise LiveTradingDisabledError for live orders."""
    from core.exceptions import LiveTradingDisabledError
    from risk.risk_manager import RiskManager

    rm = RiskManager()
    with patch("risk.risk_manager.settings") as mock_s:
        mock_s.emergency_kill_switch_active = False
        mock_s.live_trading_enabled = False
        mock_s.max_orders_per_minute = 10
        mock_s.max_price_staleness_seconds = 60
        mock_s.max_position_size_pct = 10.0
        mock_s.max_sector_exposure_pct = 30.0
        mock_s.max_daily_loss_pct = 5.0
        mock_s.max_drawdown_pct = 20.0

        with pytest.raises(LiveTradingDisabledError):
            rm.evaluate_trade(
                ticker="RELIANCE", direction="BUY", quantity=1.0,
                price=2500.0, portfolio_equity=1_000_000.0,
                portfolio_positions={}, portfolio_cash=500_000.0,
                portfolio_drawdown=0.01, sector="Energy",
                sector_current_pct=5.0, daily_realised_loss_pct=0.0,
                price_age_seconds=5.0, is_live=True,
            )


# ── API: orders endpoint cannot submit live orders ─────────────

@pytest.mark.asyncio
async def test_orders_api_is_paper_only(client) -> None:
    """The orders API must indicate paper-only mode."""
    response = await client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    # Must indicate paper only
    assert "paper" in str(data).lower() or "not yet implemented" in str(data).lower()


# ── Config safety: risk limits cannot be set to 0 ──────────────

def test_risk_limits_have_minimum_bounds() -> None:
    """Risk limits must have minimum validation to prevent accidental 0-config."""
    from core.config import Settings
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        Settings(
            SECRET_KEY="a" * 33,
            JWT_SECRET_KEY="b" * 33,
            DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
            max_portfolio_risk_pct=0.0,  # Below minimum of 0.1
        )


# ── No live broker code reachable from paper path ─────────────

def test_paper_broker_provider_name() -> None:
    """PaperBroker.provider_name must clearly identify it as paper."""
    from trading.paper_broker import PaperBroker
    broker = PaperBroker()
    assert "paper" in broker.provider_name.lower()


@pytest.mark.asyncio
async def test_live_broker_refuses_orders_and_cancels_when_live_disabled(monkeypatch) -> None:
    """Defense-in-depth: LiveBroker itself refuses order placement/cancellation if live_trading_enabled is False."""
    from types import SimpleNamespace
    from trading import live_broker as lb_mod

    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "dummy-token")
    monkeypatch.setattr(
        lb_mod,
        "get_settings",
        lambda: SimpleNamespace(live_trading_enabled=False, emergency_kill_switch_active=False),
    )
    broker = lb_mod.LiveBroker(api_key="k", api_secret="s", redirect_uri="https://127.0.0.1")
    res = await broker.place_order(ticker="NSE_EQ|INE002A01018", direction="BUY", quantity=1, order_type="MARKET", price=100.0)
    assert res["status"] == "REJECTED"
    assert res["reason"] == "LIVE_TRADING_DISABLED"
    assert await broker.cancel_order("ORD123") is False


@pytest.mark.asyncio
async def test_readiness_endpoint_reports_honest_trust_gates(client) -> None:
    """GET /api/v1/bot/readiness exposes structured paper and live-capital checks."""
    resp = await client.get("/api/v1/bot/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "paper_ready" in body
    assert "live_capital_ready" in body
    assert body["live_trading_enabled"] is False
    assert isinstance(body["blocking_reasons"], list)
    assert "checks" in body
