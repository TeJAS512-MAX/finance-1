"""
information_decay.py — Item 51: Information Decay Model
=========================================================

Every information event has a time-decay component.  Relevance decreases
continuously based on:

  * Age of the information
  * Whether the market has already reacted (price discovery completed)
  * Arrival of newer contradictory information
  * Whether the event is materially important (slows decay)
  * Publication vs. confirmation lag

Formula
-------
  relevance(t) = base_decay(t) * contradiction_factor * confirmation_bonus

  base_decay(t) = exp(-lambda * age_hours)
                  where lambda is tuned per event_type

  contradiction_factor = product(1 - severity_i) for each contradiction
  confirmation_bonus   = 1.2 if confirmed (capped at 1.0 combined)
  material_floor       = 0.05  (material events never fully decay)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Optional

from .models import InformationEvent


# ---------------------------------------------------------------------------
# Decay half-life by event type (hours)
# ---------------------------------------------------------------------------
DEFAULT_HALF_LIVES: Dict[str, float] = {
    "earnings":         72.0,   # 3 days
    "guidance":         96.0,   # 4 days
    "contract":         48.0,
    "macro":            24.0,
    "news":              6.0,
    "rumour":            2.0,
    "analyst_upgrade":  48.0,
    "analyst_downgrade": 48.0,
    "regulatory":       120.0,
    "default":          12.0,
}

MATERIAL_FLOOR = 0.05          # material events never decay below 5 % relevance
CONFIRMATION_BONUS = 0.20      # +20 % relevance when officially confirmed


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class InformationDecayEngine:
    """
    Calculates and updates relevance scores for InformationEvent objects.

    Usage
    -----
    engine = InformationDecayEngine()
    engine.register(event)
    current_relevance = engine.get_relevance(event.event_id)
    engine.apply_contradiction(primary_id, contradicting_id, severity=0.8)
    """

    def __init__(self, half_lives: Optional[Dict[str, float]] = None) -> None:
        self._half_lives = half_lives or DEFAULT_HALF_LIVES
        self._events: Dict[str, InformationEvent] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, event: InformationEvent) -> None:
        """Register a new information event and set its initial relevance."""
        event.relevance_score = 1.0
        self._events[event.event_id] = event

    def get_event(self, event_id: str) -> Optional[InformationEvent]:
        return self._events.get(event_id)

    # ------------------------------------------------------------------
    # Relevance calculation
    # ------------------------------------------------------------------

    def get_relevance(
        self,
        event_id: str,
        as_of: Optional[datetime] = None,
    ) -> float:
        """
        Return the current relevance score [0, 1] for an event.

        Parameters
        ----------
        event_id : str
        as_of    : datetime (UTC); defaults to now
        """
        event = self._events.get(event_id)
        if event is None:
            return 0.0

        as_of = as_of or datetime.now(timezone.utc)
        pub_time = _ensure_utc(event.publication_time)
        age_hours = max(0.0, (as_of - pub_time).total_seconds() / 3600.0)

        # 1. Exponential base decay
        half_life = self._half_lives.get(
            event.event_type, self._half_lives["default"]
        )
        lam = math.log(2) / half_life
        base_score = math.exp(-lam * age_hours)

        # 2. Confirmation bonus (slight slow-down of decay)
        if event.confirmation_time is not None:
            conf_time = _ensure_utc(event.confirmation_time)
            if as_of >= conf_time:
                base_score = min(1.0, base_score * (1 + CONFIRMATION_BONUS))

        # 3. Contradiction penalty (each contradiction reduces by severity)
        contradiction_factor = 1.0
        for contra_id in event.contradicted_by:
            contra = self._events.get(contra_id)
            if contra is not None:
                # Use contradiction severity stored in metadata (default 0.5)
                severity = float(contra.metadata.get("contradiction_severity", 0.5))
                contradiction_factor *= (1.0 - severity)

        score = base_score * contradiction_factor

        # 4. Material floor — material events retain minimum relevance
        if event.is_materially_important:
            score = max(score, MATERIAL_FLOOR)

        # 5. Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        # Persist latest score
        event.relevance_score = score
        return score

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def apply_contradiction(
        self,
        primary_event_id: str,
        contradicting_event_id: str,
        severity: float = 0.5,
    ) -> None:
        """
        Record that contradicting_event_id undermines primary_event_id.

        Parameters
        ----------
        severity : float [0, 1]
            0 = no effect, 1 = complete invalidation
        """
        primary = self._events.get(primary_event_id)
        contra  = self._events.get(contradicting_event_id)
        if primary is None or contra is None:
            return
        contra.metadata["contradiction_severity"] = max(0.0, min(1.0, severity))
        if contradicting_event_id not in primary.contradicted_by:
            primary.contradicted_by.append(contradicting_event_id)

    def confirm_event(self, event_id: str, confirmed_at: Optional[datetime] = None) -> None:
        """Mark an event as officially confirmed, boosting its relevance slightly."""
        event = self._events.get(event_id)
        if event:
            event.confirmation_time = confirmed_at or datetime.now(timezone.utc)

    def mark_material(self, event_id: str, is_material: bool = True) -> None:
        """Override the material-importance flag."""
        event = self._events.get(event_id)
        if event:
            event.is_materially_important = is_material

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def refresh_all(self, as_of: Optional[datetime] = None) -> Dict[str, float]:
        """Recalculate and return relevance for all registered events."""
        return {eid: self.get_relevance(eid, as_of) for eid in self._events}

    def active_events(
        self,
        min_relevance: float = 0.10,
        as_of: Optional[datetime] = None,
    ) -> list[InformationEvent]:
        """Return events whose current relevance ≥ min_relevance."""
        result = []
        for eid, event in self._events.items():
            if self.get_relevance(eid, as_of) >= min_relevance:
                result.append(event)
        return sorted(result, key=lambda e: e.relevance_score, reverse=True)

    def summary(self, as_of: Optional[datetime] = None) -> list[dict]:
        """Return a human-readable summary table of all events."""
        rows = []
        for eid, event in self._events.items():
            rel = self.get_relevance(eid, as_of)
            rows.append({
                "event_id":    eid[:8],
                "type":        event.event_type,
                "symbol":      event.symbol or "—",
                "headline":    event.headline[:60],
                "relevance":   round(rel, 4),
                "material":    event.is_materially_important,
                "contradictions": len(event.contradicted_by),
            })
        return sorted(rows, key=lambda r: r["relevance"], reverse=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _ensure_utc(dt: datetime) -> datetime:
    """Return dt with UTC timezone, attaching UTC if naïve."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
