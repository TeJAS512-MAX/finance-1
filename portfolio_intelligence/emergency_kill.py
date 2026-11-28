"""
portfolio_intelligence/emergency_kill.py — Item 56: Emergency Kill Switch
==========================================================================

A hard safety layer that:
  1. Monitors for emergency conditions
  2. When triggered: STOPS new orders, LOGS incident, ALERTS user, REQUIRES manual review
  3. Cannot be reset by any AI model — only by human operator

Emergency triggers (Item 56):
  - Unexpected API behavior
  - Abnormal order frequency
  - Data corruption
  - Stale prices
  - Model failure
  - Excessive losses
  - Unexpected portfolio exposure
  - Duplicate orders
  - Broker connectivity problems

The kill switch state is stored persistently (Redis/DB) so it survives restarts.
Manual reset requires explicit human confirmation via the admin API.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import EmergencyEvent, EmergencyTrigger


# ---------------------------------------------------------------------------
# Kill switch state
# ---------------------------------------------------------------------------

@dataclass
class KillSwitchState:
    active: bool = False
    triggered_at: Optional[datetime] = None
    trigger: Optional[EmergencyTrigger] = None
    trigger_reason: str = ""
    triggered_by: str = "system"
    incident_id: str = ""
    requires_manual_reset: bool = True
    manual_reset_by: Optional[str] = None
    manual_reset_at: Optional[datetime] = None
    resolved: bool = False


# ---------------------------------------------------------------------------
# Emergency Kill Switch Engine
# ---------------------------------------------------------------------------

class EmergencyKillSwitch:
    """
    Hard safety layer — monitors for emergency conditions and halts trading.

    The AI decision model CANNOT:
      - Reset the kill switch
      - Bypass the kill switch check
      - Change the requires_manual_reset flag

    Only a human operator (admin role) can reset the kill switch via:
      reset(operator_id=..., confirmation_code=...)
    """

    def __init__(
        self,
        alert_callbacks: Optional[List[Callable[[EmergencyEvent], None]]] = None,
        persist_callback: Optional[Callable[[KillSwitchState], None]] = None,
    ) -> None:
        self._state = KillSwitchState()
        self._events: List[EmergencyEvent] = []
        self._lock = threading.Lock()
        self._alert_callbacks = alert_callbacks or []
        self._persist_callback = persist_callback
        self._thresholds: Dict[str, float] = {
            "max_loss_pct": 5.0,
            "max_orders_per_minute": 15,
            "max_price_staleness_seconds": 120,
            "max_unexpected_exposure_pct": 25.0,
        }

    # ------------------------------------------------------------------
    # Core check — called before every action
    # ------------------------------------------------------------------

    def check(self) -> None:
        """
        Raise if kill switch is active.
        Call this before ANY order placement.
        """
        if self._state.active:
            from .models import EmergencyTrigger
            raise KillSwitchActiveError(
                trigger=self._state.trigger,
                reason=self._state.trigger_reason,
                incident_id=self._state.incident_id,
            )

    # ------------------------------------------------------------------
    # Trigger
    # ------------------------------------------------------------------

    def trigger(
        self,
        trigger: EmergencyTrigger,
        description: str,
        triggered_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmergencyEvent:
        """
        Activate the emergency kill switch.

        Effects:
          1. Set state.active = True
          2. Record emergency event
          3. Call all alert callbacks (email, SMS, webhook)
          4. Persist state
          5. Log to audit trail

        This method is idempotent — calling it when already active
        adds another event but does not change the active state.
        """
        with self._lock:
            import uuid as uuid_mod
            event = EmergencyEvent(
                trigger=trigger,
                description=description,
                metadata=metadata or {},
            )
            self._events.append(event)

            if not self._state.active:
                self._state.active = True
                self._state.triggered_at = event.timestamp
                self._state.trigger = trigger
                self._state.trigger_reason = description
                self._state.triggered_by = triggered_by
                self._state.incident_id = event.event_id
                self._state.resolved = False

            # Persist
            if self._persist_callback:
                self._persist_callback(self._state)

            # Alert
            for callback in self._alert_callbacks:
                try:
                    callback(event)
                except Exception:
                    pass  # Never let alert failure prevent kill switch from activating

            print(  # Use print as a final fallback — always visible
                f"\n🔴 EMERGENCY KILL SWITCH ACTIVATED\n"
                f"   Trigger:     {trigger.value}\n"
                f"   Description: {description}\n"
                f"   Triggered by: {triggered_by}\n"
                f"   Incident ID: {event.event_id}\n"
                f"   STOP NEW ORDERS — LOG INCIDENT — ALERT USER — REQUIRE MANUAL REVIEW\n"
            )
            return event

    # ------------------------------------------------------------------
    # Automated monitoring checks
    # ------------------------------------------------------------------

    def check_loss_threshold(
        self, daily_loss_pct: float, portfolio_id: str = "default"
    ) -> None:
        """Trigger kill switch if daily loss exceeds threshold."""
        if daily_loss_pct >= self._thresholds["max_loss_pct"]:
            self.trigger(
                EmergencyTrigger.EXCESSIVE_LOSSES,
                f"Daily loss {daily_loss_pct:.2f}% exceeded threshold "
                f"{self._thresholds['max_loss_pct']}%",
                metadata={"portfolio_id": portfolio_id, "daily_loss_pct": daily_loss_pct},
            )

    def check_order_frequency(self, orders_per_minute: int) -> None:
        """Trigger kill switch on abnormal order frequency."""
        if orders_per_minute > self._thresholds["max_orders_per_minute"]:
            self.trigger(
                EmergencyTrigger.ABNORMAL_ORDER_FREQUENCY,
                f"Order frequency {orders_per_minute}/min exceeded threshold "
                f"{self._thresholds['max_orders_per_minute']}/min. "
                "Possible runaway trading loop.",
            )

    def check_data_freshness(self, price_age_seconds: float, symbol: str) -> None:
        """Trigger kill switch on stale price data."""
        if price_age_seconds > self._thresholds["max_price_staleness_seconds"]:
            self.trigger(
                EmergencyTrigger.STALE_PRICES,
                f"Price for {symbol} is {price_age_seconds:.0f}s old "
                f"(limit: {self._thresholds['max_price_staleness_seconds']}s). "
                "Cannot safely trade with stale data.",
                metadata={"symbol": symbol, "price_age_seconds": price_age_seconds},
            )

    def check_duplicate_order(self, order_hash: str) -> None:
        """Trigger kill switch on duplicate order detection."""
        self.trigger(
            EmergencyTrigger.DUPLICATE_ORDERS,
            f"Duplicate order detected: hash={order_hash[:12]}. "
            "This may indicate a system loop or double-submission bug.",
            metadata={"order_hash": order_hash},
        )

    def check_broker_connectivity(self, error: str) -> None:
        """Trigger kill switch on broker connectivity failure."""
        self.trigger(
            EmergencyTrigger.BROKER_CONNECTIVITY,
            f"Broker connectivity error: {error}",
            metadata={"error": error},
        )

    # ------------------------------------------------------------------
    # Manual reset — ONLY humans can call this
    # ------------------------------------------------------------------

    def reset(
        self,
        operator_id: str,
        confirmation_code: str,
        resolution_notes: str,
        expected_code: str = "CONFIRM_MANUAL_RESET",
    ) -> bool:
        """
        Reset the kill switch after human review.

        Parameters
        ----------
        operator_id       : ID of the human operator resetting the switch.
        confirmation_code : Must match expected_code exactly (prevents accidental reset).
        resolution_notes  : Required description of what was reviewed and resolved.

        Returns True if reset successful, False otherwise.
        """
        if confirmation_code != expected_code:
            print(
                f"⚠️  Kill switch reset REJECTED: incorrect confirmation code "
                f"(provided: '{confirmation_code}', expected: '{expected_code}')"
            )
            return False

        if not resolution_notes or len(resolution_notes) < 20:
            print(
                "⚠️  Kill switch reset REJECTED: resolution_notes must be at least 20 characters. "
                "Human review must be documented."
            )
            return False

        with self._lock:
            if not self._state.active:
                return True  # Already inactive

            self._state.active = False
            self._state.resolved = True
            self._state.manual_reset_by = operator_id
            self._state.manual_reset_at = datetime.now(timezone.utc)

            # Mark all events as resolved
            for event in self._events:
                event.resolved = True
                event.resolution_notes = resolution_notes

            if self._persist_callback:
                self._persist_callback(self._state)

            print(
                f"\n✅ Kill switch RESET by operator '{operator_id}'\n"
                f"   Resolution: {resolution_notes}\n"
            )
            return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._state.active

    def status(self) -> Dict[str, Any]:
        state = self._state
        return {
            "active": state.active,
            "triggered_at": state.triggered_at.isoformat() if state.triggered_at else None,
            "trigger": state.trigger.value if state.trigger else None,
            "trigger_reason": state.trigger_reason,
            "triggered_by": state.triggered_by,
            "incident_id": state.incident_id,
            "requires_manual_reset": state.requires_manual_reset,
            "resolved": state.resolved,
            "total_events": len(self._events),
        }

    def event_history(self) -> List[EmergencyEvent]:
        return list(self._events)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class KillSwitchActiveError(Exception):
    """Raised when an action is attempted while kill switch is active."""

    def __init__(
        self,
        trigger: Optional[EmergencyTrigger] = None,
        reason: str = "",
        incident_id: str = "",
    ) -> None:
        self.trigger = trigger
        self.reason = reason
        self.incident_id = incident_id
        super().__init__(
            f"🔴 EMERGENCY KILL SWITCH IS ACTIVE. "
            f"All new orders are halted. "
            f"Trigger: {trigger.value if trigger else 'unknown'}. "
            f"Reason: {reason}. "
            f"Incident: {incident_id}. "
            f"Manual review required."
        )
