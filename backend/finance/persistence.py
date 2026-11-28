"""finance/persistence.py — MongoDB-first persistence with atomic JSON fallback."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.config import get_settings
from core.logging_config import get_logger
from schemas.finance import AetherPravahState

logger = get_logger("finance.persistence")

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "finance_state.json"


class FinancePersistence:
    """Persists SME Finance state and user records across server restarts."""

    def __init__(self, json_path: Path = DEFAULT_STATE_PATH, enabled: Optional[bool] = None):
        self.json_path = json_path
        if enabled is None:
            # Keep pytest runs isolated unless a test explicitly enables persistence
            self.enabled = "PYTEST_CURRENT_TEST" not in os.environ
        else:
            self.enabled = enabled
        self._mongo_checked = False
        self._mongo_available = False

    def _get_mongo_collection(self):
        if not self.enabled:
            return None
        try:
            from pymongo import MongoClient

            settings = get_settings()
            client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=200)
            if not self._mongo_checked:
                client.admin.command("ping")
                self._mongo_available = True
                self._mongo_checked = True
            if not self._mongo_available:
                return None
            return client[settings.mongodb_db_name]["sme_finance"]
        except Exception:
            self._mongo_checked = True
            self._mongo_available = False
            return None

    @property
    def backend_name(self) -> str:
        if not self.enabled:
            return "memory"
        if self._mongo_available:
            return "mongodb"
        return "json_file"

    def save(
        self,
        state: AetherPravahState,
        current_date: date,
        users: Dict[str, Dict[str, Any]],
    ) -> None:
        if not self.enabled:
            return

        payload = {
            "current_date": current_date.isoformat(),
            "state": state.model_dump(mode="json"),
            "users": users,
        }

        col = self._get_mongo_collection()
        if col is not None:
            try:
                col.replace_one({"_id": "primary"}, {"_id": "primary", **payload}, upsert=True)
            except Exception as exc:
                logger.warning("MongoDB save failed, falling back to JSON: %s", exc)

        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.json_path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_path.replace(self.json_path)
        except Exception as exc:
            logger.warning("JSON finance state save failed: %s", exc)

    def load(
        self,
    ) -> Optional[Tuple[AetherPravahState, date, Dict[str, Dict[str, Any]]]]:
        if not self.enabled:
            return None

        raw: Optional[Dict[str, Any]] = None
        col = self._get_mongo_collection()
        if col is not None:
            try:
                doc = col.find_one({"_id": "primary"})
                if doc:
                    raw = doc
            except Exception as exc:
                logger.warning("MongoDB load failed, falling back to JSON: %s", exc)

        if raw is None and self.json_path.is_file():
            try:
                raw = json.loads(self.json_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", self.json_path, exc)
                return None

        if not raw or "state" not in raw:
            return None

        try:
            state = AetherPravahState.model_validate(raw["state"])
            cur_date = date.fromisoformat(raw.get("current_date", date.today().isoformat()))
            users = raw.get("users") or {}
            return state, cur_date, users
        except Exception as exc:
            logger.warning("Invalid saved finance state ignored: %s", exc)
            return None
