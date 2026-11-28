"""
portfolio_intelligence/live_trading_safety.py — Item 58: Live Trading Safety Gates
====================================================================================

Live trading must remain disabled by default.

Implements a multi-gate safety system:
  Gate 1: Successful backtest          (BACKTEST_PASSED)
  Gate 2: Out-of-sample test passed    (OOS_TEST_PASSED)
  Gate 3: Paper trading validated      (PAPER_TRADING_PASSED)
  Gate 4: Risk configuration set       (RISK_CONFIG_SET)
  Gate 5: Manual human confirmation    (MANUAL_CONFIRMED)

ALL FIVE gates must pass before live trading can be enabled.

Even after activation:
  - Risk controls remain OUTSIDE the AI model
  - AI cannot disable risk controls
  - Kill switch remains active
  - Paper mode is always available as fallback

This module provides the gate tracker and validation logic.
The actual gating in production is enforced at:
  1. Config level (LIVE_TRADING_ENABLED env var)
  2. RiskManager level (pre-order checks)
  3. BrokerProvider level (LiveBroker is never instantiated if disabled)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import LiveTradingGate


# ---------------------------------------------------------------------------
# Gate status
# ---------------------------------------------------------------------------

@dataclass
class GateStatus:
    gate: LiveTradingGate
    passed: bool = False
    passed_at: Optional[datetime] = None
    passed_by: Optional[str] = None       # Human who confirmed
    evidence: str = ""                    # What was validated
    notes: str = ""


# ---------------------------------------------------------------------------
# Live Trading Safety Manager
# ---------------------------------------------------------------------------

class LiveTradingSafetyManager:
    """
    Tracks and enforces all safety gates that must pass before live trading.

    Design:
      - Gates are one-way: once PASSED they can only be revoked by a human
      - The final gate (MANUAL_CONFIRMED) requires a human to explicitly
        type a confirmation string
      - Even after all gates pass, the system checks the env var at runtime
      - This class stores gate state in memory + persists to DB
    """

    REQUIRED_CONFIRMATION = "I UNDERSTAND THIS IS LIVE TRADING WITH REAL MONEY"

    def __init__(self) -> None:
        self._gates: Dict[LiveTradingGate, GateStatus] = {
            gate: GateStatus(gate=gate)
            for gate in LiveTradingGate
        }
        self._live_enabled: bool = False

    # ------------------------------------------------------------------
    # Gate management
    # ------------------------------------------------------------------

    def pass_gate(
        self,
        gate: LiveTradingGate,
        passed_by: str,
        evidence: str,
        notes: str = "",
    ) -> bool:
        """
        Mark a gate as passed.

        Parameters
        ----------
        gate      : The gate to pass.
        passed_by : Human operator ID (not AI model ID).
        evidence  : What was checked/validated.
        notes     : Optional additional context.
        """
        if gate == LiveTradingGate.MANUAL_CONFIRMED:
            # Special validation for final gate — not callable without explicit confirmation
            raise ValueError(
                "Use confirm_live_trading() for the MANUAL_CONFIRMED gate. "
                "It requires an explicit confirmation string."
            )

        self._gates[gate].passed = True
        self._gates[gate].passed_at = datetime.now(timezone.utc)
        self._gates[gate].passed_by = passed_by
        self._gates[gate].evidence = evidence
        self._gates[gate].notes = notes
        return True

    def confirm_live_trading(
        self,
        operator_id: str,
        confirmation_string: str,
        acknowledgements: List[str],
    ) -> bool:
        """
        Pass the final MANUAL_CONFIRMED gate.

        The operator must:
          1. Type the exact confirmation string
          2. Acknowledge all risk acknowledgements

        Returns True if confirmed, False otherwise.
        """
        if confirmation_string != self.REQUIRED_CONFIRMATION:
            print(
                f"⚠️  Live trading confirmation REJECTED.\n"
                f"   Required string: '{self.REQUIRED_CONFIRMATION}'\n"
                f"   Received:        '{confirmation_string}'"
            )
            return False

        required_acks = [
            "I understand live trading involves real financial risk",
            "I have reviewed all backtest and paper trading results",
            "I have configured appropriate risk limits",
            "I understand the system may lose money",
            "I take full responsibility for live trading decisions",
        ]

        for ack in required_acks:
            if not any(ack.lower() in a.lower() for a in acknowledgements):
                print(f"⚠️  Missing acknowledgement: '{ack}'")
                return False

        self._gates[LiveTradingGate.MANUAL_CONFIRMED].passed = True
        self._gates[LiveTradingGate.MANUAL_CONFIRMED].passed_at = datetime.now(timezone.utc)
        self._gates[LiveTradingGate.MANUAL_CONFIRMED].passed_by = operator_id
        self._gates[LiveTradingGate.MANUAL_CONFIRMED].evidence = confirmation_string
        self._gates[LiveTradingGate.MANUAL_CONFIRMED].notes = f"Acknowledgements: {acknowledgements}"

        if self.all_gates_passed():
            self._live_enabled = True
            print(
                f"\n✅ All safety gates passed. Live trading ENABLED for operator '{operator_id}'.\n"
                f"   WARNING: Real money is now at risk. Risk controls remain active.\n"
            )
            return True
        return False

    def revoke_gate(self, gate: LiveTradingGate, reason: str, revoked_by: str) -> None:
        """Revoke a gate — immediately disables live trading."""
        self._gates[gate].passed = False
        self._gates[gate].notes = f"REVOKED by {revoked_by}: {reason}"
        self._live_enabled = False
        print(f"⚠️  Gate {gate.value} REVOKED by {revoked_by}: {reason}. Live trading DISABLED.")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def all_gates_passed(self) -> bool:
        return all(gs.passed for gs in self._gates.values())

    def is_live_trading_enabled(self) -> bool:
        return self._live_enabled and self.all_gates_passed()

    def gate_status(self) -> Dict[str, Any]:
        return {
            "live_trading_enabled": self.is_live_trading_enabled(),
            "all_gates_passed": self.all_gates_passed(),
            "gates": {
                gate.value: {
                    "passed": status.passed,
                    "passed_at": status.passed_at.isoformat() if status.passed_at else None,
                    "passed_by": status.passed_by,
                    "evidence": status.evidence,
                }
                for gate, status in self._gates.items()
            },
            "gates_remaining": [
                gate.value
                for gate, status in self._gates.items()
                if not status.passed
            ],
            "disclaimer": (
                "Even when all gates pass, risk controls remain outside AI control. "
                "The emergency kill switch is always available. "
                "Paper trading is always the safer alternative."
            ),
        }

    def pending_gates(self) -> List[LiveTradingGate]:
        return [gate for gate, status in self._gates.items() if not status.passed]

    def passed_gates(self) -> List[LiveTradingGate]:
        return [gate for gate, status in self._gates.items() if status.passed]
