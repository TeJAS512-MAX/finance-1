import json
import uuid
import hashlib
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "events_db.json")

class EventRadar:
    """
    Phase 3: Information Layer.
    Scans and stores fundamental events (news, earnings, corporate actions)
    for symbols. Persists to disk and tracks provenance.
    """
    def __init__(self):
        self.events_db: List[Dict[str, Any]] = []
        self._load_db()
        
    def _load_db(self):
        if os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, "r") as f:
                    self.events_db = json.load(f)
            except:
                self.events_db = []
                
    def _save_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with open(DB_PATH, "w") as f:
            json.dump(self.events_db, f, indent=4)
            
    def _generate_hash(self, symbol: str, headline: str, published_at: str) -> str:
        content = f"{symbol}|{headline}|{published_at}"
        return hashlib.sha256(content.encode()).hexdigest()

    def add_event(self, symbol: str, event_type: str, source: str, source_url: str, headline: str, 
                  published_at: str, credibility: float = 0.95, is_simulated: bool = False) -> Optional[Dict[str, Any]]:
        """
        Adds a new event if it doesn't already exist (deduplicated by hash).
        """
        content_hash = self._generate_hash(symbol, headline, published_at)
        
        # Deduplication check
        if any(e["content_hash"] == content_hash for e in self.events_db):
            return None
            
        event = {
            "event_id": str(uuid.uuid4()),
            "symbol": symbol,
            "event_type": event_type,
            "headline": headline,
            "published_at": published_at,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "source_url": source_url,
            "source_type": "NEWS" if "news" in source.lower() else "FILING",
            "credibility": credibility,
            "is_simulated": is_simulated,
            "content_hash": content_hash,
            # Point-in-Time Tracking
            "available_at": None,
            "availability_type": "UNKNOWN",
            # AI fields populated later by AI Debate
            "financial_impact": "UNKNOWN",
            "expected_direction": "UNKNOWN",
            "expectation_gap": "UNKNOWN",
            "priced_in": "UNKNOWN",
            "market_reaction": None,
            "causal_chain": [],
            "status": "AWAITING_ANALYSIS"
        }
        
        self.events_db.append(event)
        self._save_db()
        return event

    def fetch_recent_events(self, symbol: str, include_simulated: bool = False) -> List[Dict[str, Any]]:
        """
        Returns events for a symbol sorted newest-first.
        """
        events = [
            e for e in self.events_db 
            if e["symbol"] == symbol and (include_simulated or not e.get("is_simulated", False))
        ]
        # Sort newest first so events[0] is always the most recent catalyst
        events.sort(key=lambda e: e.get("published_at", ""), reverse=True)
        return events
        
    def fetch_pit_events(self, symbol: str, knowledge_cutoff: str, include_simulated: bool = False) -> List[Dict[str, Any]]:
        """
        STRICT POINT-IN-TIME (PIT) FETCH
        Filters events ensuring their 'available_at' timestamp is strictly <= knowledge_cutoff.
        This represents the data-access layer preventing lookahead bias.
        """
        dt_cutoff = datetime.fromisoformat(knowledge_cutoff)
        
        valid_events = []
        for e in self.events_db:
            if e["symbol"] != symbol:
                continue
            if not include_simulated and e.get("is_simulated", False):
                continue
            
            avail_str = e.get("available_at")
            if not avail_str:
                continue # Unverified events are invisible to PIT
                
            dt_avail = datetime.fromisoformat(avail_str)
            if dt_avail <= dt_cutoff:
                valid_events.append(e)
                
        return valid_events
        
    def inject_simulated_catalysts_for_dev(self):
        """
        Development only: injects mock catalysts.
        These are strictly flagged as is_simulated=True.
        """
        now = datetime.now(timezone.utc).isoformat()
        self.add_event(
            symbol="RELIANCE", event_type="corporate_announcement", source="BSE_Filing", source_url="mock://bse",
            headline="Reliance signs major $5B telecom expansion deal in rural India", published_at=now, is_simulated=True
        )
        self.add_event(
            symbol="HDFCBANK", event_type="earnings_release", source="MoneyControl", source_url="mock://moneycontrol",
            headline="HDFC Bank Q2 net profit misses estimates, NIM contracts by 10 bps", published_at=now, is_simulated=True
        )

    def get_unprocessed_events(self) -> List[Dict[str, Any]]:
        return [e for e in self.events_db if e["status"] == "AWAITING_ANALYSIS"]

    def update_event(self, event_id: str, updates: Dict[str, Any]):
        for e in self.events_db:
            if e["event_id"] == event_id:
                e.update(updates)
                self._save_db()
                break

event_radar = EventRadar()
