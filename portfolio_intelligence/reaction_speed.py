"""
portfolio_intelligence/reaction_speed.py — Event Reaction Speed Measurement
================================================================================

Measures the latency between an event's publication time and the system's
reaction (trade generated or decision made).

Crucial for alpha decay analysis: if the system takes 5 minutes to react to a
news headline, the alpha might already be entirely priced in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class ReactionMetric:
    event_id: str
    symbol: str
    publication_time: datetime
    ingestion_time: datetime
    decision_time: datetime
    execution_time: Optional[datetime] = None

    @property
    def system_latency_ms(self) -> float:
        """Time from ingestion to decision."""
        return (self.decision_time - self.ingestion_time).total_seconds() * 1000.0

    @property
    def total_latency_ms(self) -> float:
        """Time from publication to execution (or decision if no execution)."""
        end_time = self.execution_time or self.decision_time
        return (end_time - self.publication_time).total_seconds() * 1000.0


class ReactionSpeedEngine:
    """Tracks and analyses the latency of the system's reaction to events."""

    def __init__(self) -> None:
        self._metrics: List[ReactionMetric] = []

    def record(self, metric: ReactionMetric) -> None:
        """Record a new reaction latency metric."""
        self._metrics.append(metric)

    def summary(self) -> Dict[str, float]:
        """Aggregate reaction speed statistics."""
        if not self._metrics:
            return {}

        sys_latencies = [m.system_latency_ms for m in self._metrics]
        tot_latencies = [m.total_latency_ms for m in self._metrics]

        return {
            "avg_system_latency_ms": sum(sys_latencies) / len(sys_latencies),
            "max_system_latency_ms": max(sys_latencies),
            "avg_total_latency_ms": sum(tot_latencies) / len(tot_latencies),
            "max_total_latency_ms": max(tot_latencies),
            "events_tracked": len(self._metrics),
        }
