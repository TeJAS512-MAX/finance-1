"""
portfolio_intelligence/catalyst_calendar.py — Catalyst Calendar
================================================================================

Tracks known upcoming catalysts (earnings, regulatory decisions, macro events).
Prevents trading immediately before highly uncertain binary events unless
the strategy explicitly calls for event-driven volatility exposure.

Also reduces allocation if an event is imminent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .models import MarketRegime


@dataclass
class Catalyst:
    symbol: str
    event_type: str        # 'EARNINGS', 'FDA_APPROVAL', 'MACRO', 'AGM'
    expected_date: datetime
    is_binary: bool        # True if it's a pass/fail event (e.g., FDA)
    volatility_multiplier: float
    description: str


class CatalystCalendar:
    """Maintains a calendar of upcoming market-moving events."""

    def __init__(self) -> None:
        self._events: List[Catalyst] = []

    def add_catalyst(self, catalyst: Catalyst) -> None:
        """Register an upcoming catalyst."""
        self._events.append(catalyst)

    def get_upcoming(
        self, symbol: str, horizon_days: int = 14
    ) -> List[Catalyst]:
        """Get upcoming events for a symbol within horizon_days."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=horizon_days)
        return [
            e for e in self._events
            if e.symbol == symbol and now <= e.expected_date <= cutoff
        ]

    def check_trade_safety(
        self, symbol: str, proposed_holding_period_days: int
    ) -> Dict[str, Any]:
        """
        Check if it's safe to enter a trade given upcoming events.
        If a binary event falls within the holding period, trading might be restricted.
        """
        upcoming = self.get_upcoming(symbol, proposed_holding_period_days)
        
        binary_events = [e for e in upcoming if e.is_binary]
        imminent_events = [e for e in upcoming if (e.expected_date - datetime.now(timezone.utc)).days < 3]

        safety_score = 1.0
        warnings = []

        if binary_events:
            safety_score *= 0.1  # Heavy penalty for holding through binary event
            warnings.append(
                f"BINARY EVENT RISK: Holding through binary event(s) "
                f"{[e.event_type for e in binary_events]}. Extreme volatility risk."
            )

        if imminent_events:
            safety_score *= 0.5
            warnings.append(
                f"IMMINENT EVENT: Event(s) within 3 days "
                f"{[e.event_type for e in imminent_events]}."
            )

        return {
            "is_safe": safety_score > 0.3,
            "safety_score": safety_score,
            "upcoming_catalysts": upcoming,
            "warnings": warnings,
        }
