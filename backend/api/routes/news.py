"""Read-only market news feed for the dashboard."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter()
EVENTS_PATH = Path(__file__).parents[2] / "data" / "events_db.json"


@router.get("", summary="List recent market news")
async def list_news(limit: int = Query(default=10, ge=1, le=100)):
    """Return recent persisted public-news events in the dashboard shape."""
    try:
        events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        events = []

    events = sorted(
        (event for event in events if event.get("headline")),
        key=lambda event: event.get("published_at", ""),
        reverse=True,
    )
    items = [
        {
            "id": event.get("event_id"),
            "headline": event.get("headline"),
            "publisher": event.get("source", "Unknown"),
            "published_at": event.get("published_at"),
            "event_type": event.get("event_type", "UNKNOWN"),
            "verification_status": event.get("status", "UNVERIFIED"),
            "information_type": event.get("source_type", "PUBLIC_NEWS"),
            "credibility_score": event.get("credibility", 0.0),
            "sentiment_label": event.get("sentiment_label", "UNKNOWN"),
            "impact_score": event.get("impact_score", 0.0),
        }
        for event in events[:limit]
    ]
    return {"items": items, "count": len(items)}