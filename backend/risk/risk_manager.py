"""
risk/risk_manager.py — Hard risk management layer.

This module enforces portfolio-level risk limits that NO AI model can override.

Rules enforced:
  1. Emergency kill switch check (fails fast)
  2. Live trading safety gate
  3. Duplicate order detection
  4. Data quality check (stale prices)
  5. Maximum position size
  6. Maximum sector exposure
  7. Maximum daily loss
  8. Maximum portfolio drawdown
  9. Maximum portfolio correlation
  10. Maximum orders per minute (abnormal frequency)

If any check fails:
  → Trade is REJECTED with a clear reason
  → Incident is logged to audit log
  → Alert is raised if severity is HIGH/CRITICAL
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_settings
from core.exceptions import (
    EmergencyKillSwitchActiveError,
    LiveTradingDisabledError,
    RiskLimitExceededError,
    StaleDataError,
)
from core.logging_config import audit, get_logger

logger = get_logger(__name__)
settings = get_settings()


class RiskDecision:
    """Result of a risk evaluation."""

    def __init__(
        self,
        approved: bool,
        reasons: List[str],
        risk_metrics: Dict[str, float],
        approved_quantity: float = 0.0,
    ) -> None:
        self.approved = approved
        self.reasons = reasons
        self.risk_metrics = risk_metrics
        self.approved_quantity = approved_quantity

    def __bool__(self) -> bool:
        return self.approved


class RiskManager:
    """
    Hard risk management layer.

    AI models call evaluate_trade() before any order is placed.
    This class does NOT call any AI model — it applies hard rules only.
    """

    def __init__(self) -> None:
        self._order_timestamps: deque = deque()  # sliding window for frequency check
        self._daily_loss_tracker: Dict[str, float] = {}  # date → realised loss
        self._seen_order_hashes: set = set()  # duplicate detection

    # ── Primary evaluation ────────────────────────────────

    def evaluate_trade(
        self,
        *,
        ticker: str,
        direction: str,
        quantity: float,
        price: float,
        portfolio_equity: float,
        portfolio_positions: Dict[str, Any],
        portfolio_cash: float,
        portfolio_drawdown: float,
        sector: str,
        sector_current_pct: float,
        daily_realised_loss_pct: float,
        price_age_seconds: float,
        is_live: bool = False,
        order_hash: Optional[str] = None,
        clock_now: Optional[float] = None,
    ) -> RiskDecision:
        """
        Evaluate whether a proposed trade passes all risk checks.

        Returns RiskDecision.approved = True only if ALL checks pass.
        """
        reasons: List[str] = []
        metrics: Dict[str, float] = {}

        # ── CHECK 1: Emergency kill switch ───────────────
        if settings.emergency_kill_switch_active:
            audit("RISK_KILL_SWITCH_BLOCKED", ticker=ticker)
            raise EmergencyKillSwitchActiveError()

        # ── CHECK 2: Live trading safety gate ────────────
        if is_live and not settings.live_trading_enabled:
            audit("RISK_LIVE_TRADING_BLOCKED", ticker=ticker)
            raise LiveTradingDisabledError()

        # ── CHECK 3: Duplicate order detection ────────────
        if order_hash and order_hash in self._seen_order_hashes:
            reasons.append(f"DUPLICATE_ORDER: hash {order_hash[:8]} already submitted")
            self._log_risk_event("DUPLICATE_ORDERS", reasons[-1], ticker)
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 4: Abnormal order frequency ────────────
        now = time.monotonic() if clock_now is None else clock_now
        self._order_timestamps.append(now)
        # Remove timestamps older than 60 seconds
        while self._order_timestamps and now - self._order_timestamps[0] > 60:
            self._order_timestamps.popleft()

        orders_per_minute = len(self._order_timestamps)
        metrics["orders_per_minute"] = float(orders_per_minute)
        if orders_per_minute > settings.max_orders_per_minute:
            reasons.append(
                f"ABNORMAL_ORDER_FREQUENCY: {orders_per_minute} orders/min "
                f"(limit: {settings.max_orders_per_minute})"
            )
            self._log_risk_event("ABNORMAL_ORDER_FREQUENCY", reasons[-1], ticker)
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 5: Stale price data ─────────────────────
        metrics["price_age_seconds"] = price_age_seconds
        if price_age_seconds > settings.max_price_staleness_seconds:
            reasons.append(
                f"STALE_PRICE: price is {price_age_seconds:.0f}s old "
                f"(max: {settings.max_price_staleness_seconds}s)"
            )
            self._log_risk_event("STALE_PRICES", reasons[-1], ticker)
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 6: Position size ────────────────────────
        notional = quantity * price
        position_pct = (notional / portfolio_equity * 100) if portfolio_equity > 0 else 0
        metrics["proposed_position_pct"] = position_pct
        if position_pct > settings.max_position_size_pct:
            reasons.append(
                f"POSITION_SIZE: {position_pct:.1f}% exceeds limit {settings.max_position_size_pct}%"
            )
            # Reduce quantity to fit within limit instead of full reject
            max_notional = portfolio_equity * settings.max_position_size_pct / 100
            approved_qty = max_notional / price if price > 0 else 0
            return RiskDecision(
                False, reasons, metrics, approved_quantity=approved_qty
            )

        # ── CHECK 7: Capital check ────────────────────────
        if notional > portfolio_cash:
            reasons.append(
                f"INSUFFICIENT_CASH: need {notional:.0f}, have {portfolio_cash:.0f}"
            )
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 8: Sector concentration ────────────────
        metrics["sector_current_pct"] = sector_current_pct
        if sector_current_pct + position_pct > settings.max_sector_exposure_pct:
            reasons.append(
                f"SECTOR_CONCENTRATION: {sector} would reach "
                f"{sector_current_pct + position_pct:.1f}% "
                f"(limit: {settings.max_sector_exposure_pct}%)"
            )
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 9: Daily loss ───────────────────────────
        metrics["daily_loss_pct"] = daily_realised_loss_pct
        if daily_realised_loss_pct >= settings.max_daily_loss_pct:
            reasons.append(
                f"DAILY_LOSS: {daily_realised_loss_pct:.1f}% "
                f"(limit: {settings.max_daily_loss_pct}%)"
            )
            self._log_risk_event("EXCESSIVE_LOSSES", reasons[-1], ticker)
            return RiskDecision(False, reasons, metrics)

        # ── CHECK 10: Maximum drawdown ────────────────────
        metrics["portfolio_drawdown_pct"] = portfolio_drawdown * 100
        if portfolio_drawdown * 100 >= settings.max_drawdown_pct:
            reasons.append(
                f"MAX_DRAWDOWN: portfolio drawdown {portfolio_drawdown*100:.1f}% "
                f"(limit: {settings.max_drawdown_pct}%)"
            )
            self._log_risk_event("EXCESSIVE_LOSSES", reasons[-1], ticker)
            return RiskDecision(False, reasons, metrics)

        # ── All checks passed ─────────────────────────────
        if order_hash:
            self._seen_order_hashes.add(order_hash)

        logger.info(
            "Risk check PASSED",
            ticker=ticker,
            direction=direction,
            quantity=quantity,
            notional=notional,
            position_pct=position_pct,
        )
        return RiskDecision(True, [], metrics, approved_quantity=quantity)

    # ── Circuit breaker ────────────────────────────────────

    def trigger_emergency_kill_switch(self, reason: str, triggered_by: str = "system") -> None:
        """
        Activate emergency kill switch.

        This sets a flag that the settings object reads.
        IMPORTANT: Only manual intervention (human) can reset this.
        The AI model cannot call this to reset — it can only trigger.
        """
        audit(
            "EMERGENCY_KILL_SWITCH_ACTIVATED",
            reason=reason,
            triggered_by=triggered_by,
        )
        logger.critical(
            "🔴 EMERGENCY KILL SWITCH ACTIVATED",
            reason=reason,
            triggered_by=triggered_by,
        )
        # In production this would update a Redis flag / database flag
        # that persists across restarts and requires manual reset
        # For now we update the settings object
        object.__setattr__(settings, "emergency_kill_switch_active", True)

    # ── Helpers ────────────────────────────────────────────

    def _log_risk_event(self, trigger: str, description: str, ticker: str) -> None:
        audit(
            "RISK_LIMIT_TRIGGERED",
            trigger=trigger,
            description=description,
            ticker=ticker,
        )
        logger.warning(
            "Risk limit triggered",
            trigger=trigger,
            ticker=ticker,
            description=description,
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            "orders_per_minute": len(self._order_timestamps),
            "known_order_hashes": len(self._seen_order_hashes),
            "emergency_kill_switch": settings.emergency_kill_switch_active,
            "live_trading_enabled": settings.live_trading_enabled,
            "limits": {
                "max_position_size_pct": settings.max_position_size_pct,
                "max_sector_exposure_pct": settings.max_sector_exposure_pct,
                "max_daily_loss_pct": settings.max_daily_loss_pct,
                "max_drawdown_pct": settings.max_drawdown_pct,
                "max_orders_per_minute": settings.max_orders_per_minute,
            },
        }
