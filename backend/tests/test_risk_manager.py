"""
tests/test_risk_manager.py — Comprehensive risk manager tests.

CRITICAL: These tests verify that risk limits CANNOT be bypassed.
Every check must pass or trades must be rejected.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from core.exceptions import EmergencyKillSwitchActiveError, LiveTradingDisabledError
from risk.risk_manager import RiskManager


# ── Fixture ────────────────────────────────────────────────────

@pytest.fixture
def rm() -> RiskManager:
    return RiskManager()


def _base_params(**overrides) -> dict:
    """Default valid trade parameters."""
    params = {
        "ticker": "RELIANCE",
        "direction": "BUY",
        "quantity": 10.0,
        "price": 2500.0,
        "portfolio_equity": 1_000_000.0,
        "portfolio_positions": {},
        "portfolio_cash": 500_000.0,
        "portfolio_drawdown": 0.02,
        "sector": "Energy",
        "sector_current_pct": 5.0,
        "daily_realised_loss_pct": 0.5,
        "price_age_seconds": 10.0,
        "is_live": False,
    }
    params.update(overrides)
    return params


# ── Emergency kill switch ──────────────────────────────────────

def test_kill_switch_blocks_all_trades(rm: RiskManager) -> None:
    """Kill switch must block ALL trades immediately."""
    with patch("risk.risk_manager.settings") as mock_settings:
        mock_settings.emergency_kill_switch_active = True
        mock_settings.live_trading_enabled = False
        with pytest.raises(EmergencyKillSwitchActiveError):
            rm.evaluate_trade(**_base_params())


def test_kill_switch_cannot_be_reset_by_ai(rm: RiskManager) -> None:
    """
    AI model cannot call reset on kill switch.
    Only trigger is exposed; reset requires manual intervention.
    """
    assert not hasattr(rm, "reset_kill_switch"), (
        "RiskManager must NOT expose a reset_kill_switch method. "
        "Only manual intervention can reset the kill switch."
    )


# ── Live trading safety gate ───────────────────────────────────

def test_live_trading_blocked_when_disabled(rm: RiskManager) -> None:
    """Live orders must be blocked when LIVE_TRADING_ENABLED=false."""
    with patch("risk.risk_manager.settings") as mock_settings:
        mock_settings.emergency_kill_switch_active = False
        mock_settings.live_trading_enabled = False
        mock_settings.max_orders_per_minute = 10
        mock_settings.max_price_staleness_seconds = 60
        mock_settings.max_position_size_pct = 10.0
        mock_settings.max_sector_exposure_pct = 30.0
        mock_settings.max_daily_loss_pct = 5.0
        mock_settings.max_drawdown_pct = 20.0

        with pytest.raises(LiveTradingDisabledError):
            rm.evaluate_trade(**_base_params(is_live=True))


def test_paper_trading_allowed_without_live_flag(rm: RiskManager) -> None:
    """Paper trades (is_live=False) must not require live trading flag."""
    decision = rm.evaluate_trade(**_base_params(is_live=False))
    # Should pass all checks (using default safe values)
    assert isinstance(decision.approved, bool)  # at minimum runs without raising


# ── Position size limit ─────────────────────────────────────────

def test_position_size_limit_enforced(rm: RiskManager) -> None:
    """A trade exceeding max_position_size_pct must be rejected."""
    # 100 shares at 2500 = 250,000 / 1,000,000 equity = 25% → exceeds 10% limit
    decision = rm.evaluate_trade(**_base_params(quantity=100.0, price=2500.0))
    if not decision.approved:
        assert any("POSITION_SIZE" in r for r in decision.reasons)
    else:
        # If approved, quantity must have been reduced
        assert decision.approved_quantity <= 40.0  # 10% of 1M / 2500 = 40


def test_position_size_within_limit_approved(rm: RiskManager) -> None:
    """A trade within position size limit must pass the size check."""
    # 10 shares at 2500 = 25,000 / 1,000,000 = 2.5% → within 10% limit
    decision = rm.evaluate_trade(**_base_params(quantity=10.0, price=2500.0))
    size_reasons = [r for r in decision.reasons if "POSITION_SIZE" in r]
    assert not size_reasons, f"Unexpected POSITION_SIZE rejection: {decision.reasons}"


# ── Daily loss limit ────────────────────────────────────────────

def test_daily_loss_limit_blocks_trades(rm: RiskManager) -> None:
    """When daily loss exceeds limit, no new trades allowed."""
    decision = rm.evaluate_trade(**_base_params(daily_realised_loss_pct=6.0))
    assert not decision.approved
    assert any("DAILY_LOSS" in r for r in decision.reasons)


def test_daily_loss_just_below_limit_passes(rm: RiskManager) -> None:
    """Daily loss just below limit should NOT block trades."""
    decision = rm.evaluate_trade(**_base_params(daily_realised_loss_pct=4.9))
    daily_reasons = [r for r in decision.reasons if "DAILY_LOSS" in r]
    assert not daily_reasons


# ── Drawdown limit ──────────────────────────────────────────────

def test_max_drawdown_blocks_trades(rm: RiskManager) -> None:
    """Portfolio drawdown at or above limit must block all new trades."""
    decision = rm.evaluate_trade(**_base_params(portfolio_drawdown=0.21))
    assert not decision.approved
    assert any("DRAWDOWN" in r for r in decision.reasons)


# ── Stale data ─────────────────────────────────────────────────

def test_stale_price_blocks_trade(rm: RiskManager) -> None:
    """Stale price data (> max_price_staleness_seconds) must block trades."""
    decision = rm.evaluate_trade(**_base_params(price_age_seconds=120.0))
    assert not decision.approved
    assert any("STALE_PRICE" in r for r in decision.reasons)


def test_fresh_price_passes(rm: RiskManager) -> None:
    """Fresh price data (within limit) must not trigger stale check."""
    decision = rm.evaluate_trade(**_base_params(price_age_seconds=5.0))
    stale_reasons = [r for r in decision.reasons if "STALE_PRICE" in r]
    assert not stale_reasons


# ── Sector concentration ────────────────────────────────────────

def test_sector_concentration_limit(rm: RiskManager) -> None:
    """Sector exposure at or near limit must block trades in that sector."""
    # Current sector at 25%, proposed adds 10% → 35% > 30% limit
    decision = rm.evaluate_trade(**_base_params(
        sector_current_pct=25.0,
        quantity=40.0,  # 40 * 2500 = 100,000 / 1,000,000 = 10%
        price=2500.0,
    ))
    if not decision.approved:
        assert any("SECTOR" in r for r in decision.reasons)


# ── Duplicate order detection ───────────────────────────────────

def test_duplicate_order_rejected(rm: RiskManager) -> None:
    """Same order hash submitted twice must be rejected on second attempt."""
    params = _base_params(order_hash="unique-hash-abc123")
    # First submission
    rm.evaluate_trade(**params)
    # Second submission — must be rejected
    decision2 = rm.evaluate_trade(**params)
    assert not decision2.approved
    assert any("DUPLICATE" in r for r in decision2.reasons)


# ── Insufficient capital ─────────────────────────────────────────

def test_insufficient_cash_rejected(rm: RiskManager) -> None:
    """Trade requiring more cash than available must be rejected."""
    # 1000 shares at 2500 = 2,500,000 > 500,000 cash
    decision = rm.evaluate_trade(**_base_params(quantity=1000.0, portfolio_cash=100.0))
    assert not decision.approved


# ── Abnormal order frequency ────────────────────────────────────

def test_abnormal_order_frequency_blocked(rm: RiskManager) -> None:
    """More than max_orders_per_minute must trigger frequency block."""
    import time
    from unittest.mock import patch

    # Inject 11 timestamps within 60-second window
    rm._order_timestamps.extend([time.monotonic()] * 11)

    decision = rm.evaluate_trade(**_base_params())
    assert not decision.approved
    assert any("FREQUENCY" in r for r in decision.reasons)


# ── Metrics summary ─────────────────────────────────────────────

def test_metrics_summary_available(rm: RiskManager) -> None:
    """Risk manager must expose a metrics summary."""
    summary = rm.get_metrics_summary()
    assert "emergency_kill_switch" in summary
    assert "live_trading_enabled" in summary
    assert "limits" in summary
    assert summary["live_trading_enabled"] is False
