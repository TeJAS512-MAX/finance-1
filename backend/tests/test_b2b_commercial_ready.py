"""
tests/test_b2b_commercial_ready.py — Commercial readiness integration tests.

Covers:
  1. INSTRUMENT_KEYS expansion (66 stocks) and SYMBOL_SECTORS parity
  2. B2B auth: api_auth_enabled=False → open; api_auth_enabled=True → 401/403/200
  3. /api/v1/auth/token endpoint: invalid key → 401; valid key → JWT
  4. Prospective swing paper ledger: record → resolve → aggregate stats
  5. Swing AI schema version bump (v3) and 28-orthogonal feature columns
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── 1. INSTRUMENT_KEYS & SYMBOL_SECTORS Parity ───────────────────────────────

def test_instrument_keys_has_66_or_more_stocks():
    from services.providers.upstox_market_data import INSTRUMENT_KEYS
    assert len(INSTRUMENT_KEYS) >= 66, f"Expected >=66 instrument keys, got {len(INSTRUMENT_KEYS)}"


def test_instrument_keys_has_eternal_and_zomato():
    """ETERNAL is the renamed ZOMATO ticker; both should be present for backwards compat."""
    from services.providers.upstox_market_data import INSTRUMENT_KEYS
    assert "ETERNAL" in INSTRUMENT_KEYS, "ETERNAL (renamed ZOMATO) must be present"
    assert "ZOMATO" in INSTRUMENT_KEYS, "ZOMATO kept for backwards compatibility"
    # Both point to the same ISIN
    assert INSTRUMENT_KEYS["ETERNAL"] == INSTRUMENT_KEYS["ZOMATO"] == "NSE_EQ|INE758T01015"


def test_instrument_keys_has_next50_stocks():
    from services.providers.upstox_market_data import INSTRUMENT_KEYS
    next50 = ["HAL", "SIEMENS", "ABB", "BHEL", "EICHERMOT", "BAJAJ-AUTO",
               "HEROMOTOCO", "TVSMOTOR", "DIVISLAB", "APOLLOHOSP", "TORNTPHARM",
               "LUPIN", "PERSISTENT", "COFORGE", "BRITANNIA", "GODREJCP",
               "DABUR", "VBL", "COLPAL", "CHOLAFIN", "SHRIRAMFIN", "BANKBARODA",
               "PNB", "INDIGO", "DLF", "PIDILITIND", "HAVELLS", "TATAPOWER", "GAIL"]
    missing = [s for s in next50 if s not in INSTRUMENT_KEYS]
    assert not missing, f"Missing Next-50 instrument keys: {missing}"


def test_instrument_keys_all_valid_format():
    from services.providers.upstox_market_data import INSTRUMENT_KEYS
    for sym, key in INSTRUMENT_KEYS.items():
        assert key.startswith("NSE_EQ|INE"), f"{sym} has invalid key format: {key}"


def test_symbol_sectors_covers_all_instrument_keys():
    from services.providers.upstox_market_data import INSTRUMENT_KEYS
    from trading.bot_engine import SYMBOL_SECTORS
    # Every instrument key symbol should have a sector mapping
    missing = [s for s in INSTRUMENT_KEYS if s not in SYMBOL_SECTORS and s != "ZOMATO"]
    assert not missing, f"SYMBOL_SECTORS missing sectors for: {missing}"


# ── 2. Swing AI Schema & Feature Columns ─────────────────────────────────────

def test_swing_schema_version_is_3():
    from intelligence.swing_alpha import SWING_SCHEMA_VERSION
    assert SWING_SCHEMA_VERSION == 3, f"Expected SWING_SCHEMA_VERSION=3, got {SWING_SCHEMA_VERSION}"


def test_swing_feature_columns_no_collinear_excess():
    from intelligence.swing_alpha import SWING_FEATURE_COLUMNS
    collinear = [c for c in SWING_FEATURE_COLUMNS if c.startswith("excess_")]
    assert not collinear, f"Collinear excess_* features must be removed: {collinear}"


def test_swing_feature_columns_has_28_features():
    from intelligence.swing_alpha import SWING_FEATURE_COLUMNS
    assert len(SWING_FEATURE_COLUMNS) == 28, f"Expected 28 orthogonal features, got {len(SWING_FEATURE_COLUMNS)}"


# ── 3. B2B Auth: Open in Dev, Enforced in Prod ───────────────────────────────

@pytest.fixture()
def open_client() -> Generator:
    """Standard test client — api_auth_enabled=False (default dev mode)."""
    from main import app
    with TestClient(app) as c:
        yield c


def test_signals_open_when_auth_disabled(open_client):
    """With api_auth_enabled=False, /api/v1/signals is open (no auth header needed)."""
    resp = open_client.get("/api/v1/signals")
    assert resp.status_code in (200, 500), f"Expected open access, got {resp.status_code}: {resp.text}"


def test_auth_token_endpoint_no_keys_configured(open_client):
    """With no b2b_api_keys configured, /api/v1/auth/token returns 503."""
    resp = open_client.post("/api/v1/auth/token", json={"api_key": "anything"})
    assert resp.status_code == 503


# ── 4. /api/v1/auth/token with Configured B2B Keys ───────────────────────────

@pytest.fixture()
def auth_client():
    """Client with api_auth_enabled=True and a configured test API key."""
    from main import app
    from core.config import get_settings, Settings

    # Monkeypatch settings to inject test keys
    test_key = "testkey_b2b_01"
    with patch("core.security.settings") as mock_sec_settings:
        mock_sec_settings.jwt_secret_key.get_secret_value.return_value = "test_jwt_secret_key_32chars_padded"
        mock_sec_settings.jwt_algorithm = "HS256"
        mock_sec_settings.jwt_access_token_expire_minutes = 30
        mock_sec_settings.bcrypt_rounds = 10
        with patch("api.routes.auth.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.b2b_api_keys = f"{test_key}:trader"
            mock_settings.jwt_access_token_expire_minutes = 30
            mock_get.return_value = mock_settings
            with TestClient(app) as c:
                yield c, test_key


def test_auth_token_valid_key(auth_client):
    client, key = auth_client
    resp = client.post("/api/v1/auth/token", json={"api_key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "trader"
    assert data["token_type"] == "bearer"


def test_auth_token_invalid_key(auth_client):
    client, _ = auth_client
    resp = client.post("/api/v1/auth/token", json={"api_key": "wrong_key_xyz"})
    assert resp.status_code == 401


# ── 5. Prospective Swing Paper Ledger ─────────────────────────────────────────

@pytest.fixture()
def temp_ledger(tmp_path, monkeypatch):
    """Redirect ledger writes to a temporary file."""
    ledger_file = tmp_path / "swing_paper_ledger.json"
    import intelligence.swing_alpha as sa
    monkeypatch.setattr(sa, "SWING_PAPER_LEDGER_PATH", ledger_file)
    return ledger_file


def test_record_swing_paper_tranche_creates_ledger(temp_ledger):
    from intelligence.swing_alpha import record_swing_paper_tranche

    recs = [
        {"symbol": "RELIANCE", "sector": "Energy", "last_close": 2800.0,
         "predicted_15d_net_pct": 3.5, "suggested_qty": 10, "suggested_budget_inr": 28000.0},
        {"symbol": "TCS", "sector": "IT", "last_close": 3500.0,
         "predicted_15d_net_pct": 2.1, "suggested_qty": 5, "suggested_budget_inr": 17500.0},
    ]
    tranche = record_swing_paper_tranche(recs, "2026-11-28", 100000.0)

    assert tranche["status"] == "open"
    assert len(tranche["positions"]) == 2
    assert tranche["positions"][0]["symbol"] == "RELIANCE"
    assert temp_ledger.exists()

    ledger = json.loads(temp_ledger.read_text())
    assert len(ledger["tranches"]) == 1


def test_resolve_swing_paper_tranche_calculates_pnl(temp_ledger):
    from intelligence.swing_alpha import record_swing_paper_tranche, resolve_swing_paper_tranche

    recs = [
        {"symbol": "RELIANCE", "sector": "Energy", "last_close": 2800.0,
         "predicted_15d_net_pct": 3.5, "suggested_qty": 10, "suggested_budget_inr": 28000.0},
        {"symbol": "TCS", "sector": "IT", "last_close": 3500.0,
         "predicted_15d_net_pct": 2.1, "suggested_qty": 5, "suggested_budget_inr": 17500.0},
    ]
    tranche = record_swing_paper_tranche(recs, "2026-11-28", 100000.0)
    tid = tranche["tranche_id"]

    resolved = resolve_swing_paper_tranche(tid, {"RELIANCE": 2900.0, "TCS": 3400.0})

    assert resolved["status"] == "resolved"
    summary = resolved["summary"]
    assert summary["positions_resolved"] == 2
    # RELIANCE: (2900-2800)/2800*100 - 0.32 = 3.571 - 0.32 = 3.251% → WIN
    # TCS: (3400-3500)/3500*100 - 0.32 = -2.857 - 0.32 = -3.177% → LOSS
    assert summary["wins"] == 1
    assert summary["profit_factor"] > 0


def test_get_swing_paper_ledger_stats_aggregate(temp_ledger):
    from intelligence.swing_alpha import (
        get_swing_paper_ledger_stats,
        record_swing_paper_tranche,
        resolve_swing_paper_tranche,
    )

    recs = [
        {"symbol": "INFY", "sector": "IT", "last_close": 1800.0,
         "predicted_15d_net_pct": 4.0, "suggested_qty": 15, "suggested_budget_inr": 27000.0},
    ]
    tranche = record_swing_paper_tranche(recs, "2026-11-27", 100000.0)
    resolve_swing_paper_tranche(tranche["tranche_id"], {"INFY": 1900.0})

    stats = get_swing_paper_ledger_stats()
    agg = stats["aggregate"]
    assert agg["resolved_tranches"] == 1
    assert agg["total_positions_resolved"] == 1
    assert agg["win_rate_pct"] == 100.0
    assert agg["net_pnl_inr"] > 0


# ── 6. Bot Ledger Endpoints ────────────────────────────────────────────────────

def test_bot_swing_ledger_endpoint_returns_200(open_client):
    resp = open_client.get("/api/v1/bot/swing/ledger")
    assert resp.status_code == 200
    data = resp.json()
    assert "ledger" in data
    assert "aggregate" in data


def test_bot_swing_paper_scan_with_record_param(open_client):
    """paper-scan with record=true should return ledger_tranche field."""
    with patch("intelligence.swing_alpha.score_latest_swing_universe") as mock_score:
        mock_score.return_value = {
            "status": "ok",
            "as_of": "2026-11-28T00:00:00+00:00",
            "recommendations": [],
            "all_ranked": [],
            "capital": 100000.0,
            "tranche_slot_pct": 5.0,
            "nifty_above_sma200": True,
            "nifty_above_sma50": True,
            "stale_days": 0,
            "data_source": "cache",
        }
        resp = open_client.post("/api/v1/bot/swing/paper-scan?record=true")
    assert resp.status_code == 200
    data = resp.json()
    assert "ledger_tranche" in data


# ── 7. Route-Level B2B RBAC Enforcement & Upstox Helpers ─────────────────────

def test_has_permission_wildcard_does_not_leak_paper_trade():
    from core.security import has_permission

    assert has_permission("viewer", "read:signals") is True
    assert has_permission("viewer", "paper_trade") is False
    assert has_permission("analyst", "read:portfolio") is True
    assert has_permission("analyst", "paper_trade") is False
    assert has_permission("analyst", "admin") is False
    assert has_permission("trader", "paper_trade") is True
    assert has_permission("trader", "admin") is False
    assert has_permission("admin", "admin") is True


def test_b2b_auth_enforced_when_enabled():
    from main import app

    mock_settings = MagicMock()
    mock_settings.api_auth_enabled = True
    mock_settings.is_production = False
    mock_settings.b2b_api_keys = "vkey_001:viewer,tkey_001:trader,akey_001:admin"
    mock_settings.jwt_access_token_expire_minutes = 30

    with (
        patch("api.deps.get_settings", return_value=mock_settings),
        patch("api.routes.auth.get_settings", return_value=mock_settings),
        patch("core.security.settings") as mock_sec_settings,
        patch("intelligence.swing_alpha.score_latest_swing_universe") as mock_score,
    ):
        mock_sec_settings.jwt_secret_key.get_secret_value.return_value = "test_jwt_secret_key_32chars_padded"
        mock_sec_settings.jwt_algorithm = "HS256"
        mock_sec_settings.jwt_access_token_expire_minutes = 30
        mock_sec_settings.bcrypt_rounds = 10
        mock_score.return_value = {
            "status": "ok",
            "as_of": "2026-11-27T00:00:00+05:30",
            "recommendations": [],
            "all_ranked": [],
            "capital": 50000.0,
            "tranche_slot_pct": 3.33,
            "nifty_above_sma200": True,
            "nifty_above_sma50": True,
            "stale_days": 0,
            "data_source": "cache",
        }
        with TestClient(app) as client:
            # 1) Unauthenticated request blocked with 401
            assert client.get("/api/v1/signals/swing").status_code == 401
            assert client.get("/api/v1/bot/status").status_code == 401
            # 2) Viewer can read signals via X-API-Key, blocked on paper_trade (403)
            assert client.get("/api/v1/signals/swing", headers={"X-API-Key": "vkey_001"}).status_code == 200
            assert client.post("/api/v1/bot/swing/paper-scan", headers={"X-API-Key": "vkey_001"}).status_code == 403
            assert client.post("/api/v1/token/update", json={"analytics_token": "x"}, headers={"X-API-Key": "vkey_001"}).status_code == 403
            # 3) Trader exchanges API key -> JWT -> allowed on paper-scan, blocked on admin token/update (403)
            tok_resp = client.post("/api/v1/auth/token", json={"api_key": "tkey_001"})
            assert tok_resp.status_code == 200
            trader_jwt = tok_resp.json()["access_token"]
            assert client.post("/api/v1/bot/swing/paper-scan", headers={"Authorization": f"Bearer {trader_jwt}"}).status_code == 200
            assert client.post("/api/v1/token/update", json={"analytics_token": "x"}, headers={"Authorization": f"Bearer {trader_jwt}"}).status_code == 403


def test_token_oauth_url_returns_default_redirect(open_client, monkeypatch):
    monkeypatch.setenv("UPSTOX_API_KEY", "demo-client-id")
    monkeypatch.setenv("UPSTOX_REDIRECT_URI", "https://127.0.0.1")
    resp = open_client.get("/api/v1/token/oauth-url")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key_set"] is True
    assert body["redirect_uri"] == "https://127.0.0.1"
    assert "client_id=demo-client-id" in body["oauth_url"]


@pytest.mark.asyncio
async def test_live_quote_uses_analytics_token_when_daily_token_expired(monkeypatch):
    import base64
    from contextlib import asynccontextmanager
    from services.providers import upstox_market_data as mod

    expired_payload = base64.urlsafe_b64encode(b'{"exp":1000000000}').decode().rstrip("=")
    expired_jwt = f"hdr.{expired_payload}.sig"
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", expired_jwt)
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "valid-analytics-token")

    seen_auth = []

    class Resp:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "status": "success",
                "data": {
                    "NSE_EQ:RELIANCE": {
                        "last_price": 0.0,
                        "ohlc": {"open": 1390.0, "high": 1400.0, "low": 1380.0, "close": 1382.6},
                        "volume": 1000,
                    }
                },
            }

    class Client:
        async def get(self, url, headers, params):
            seen_auth.append(headers["Authorization"])
            return Resp()

    @asynccontextmanager
    async def fake_client(timeout):
        yield Client()

    monkeypatch.setattr(mod.httpx, "AsyncClient", fake_client)
    quote = await mod.get_live_quote("RELIANCE")
    assert seen_auth == ["Bearer valid-analytics-token"]
    assert quote["ltp"] == 1382.6

