"""Tests for 15-day CNC swing alpha engine, token JWT expiry checks, and CNC product routing."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _make_jwt(exp_ts: float) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    payload_bytes = json.dumps({"sub": "user", "exp": int(exp_ts)}).encode("utf-8")
    payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    return f"{header}.{payload}." + ("sig" * 12)


def _make_synthetic_daily_universe(n_days: int = 920) -> dict[str, list[dict]]:
    rng = np.random.default_rng(7)
    dates = []
    from datetime import date, timedelta

    cur = date(2023, 1, 2)
    while len(dates) < n_days:
        if cur.weekday() < 5:
            dates.append(f"{cur.isoformat()}T00:00:00+05:30")
        cur += timedelta(days=1)

    mkt_ret = rng.normal(0.0004, 0.008, size=n_days)
    mkt_close = 20000.0 * np.cumprod(1.0 + mkt_ret)
    data: dict[str, list[dict]] = {
        "NIFTY50": [
            {
                "timestamp": dates[i],
                "open": float(mkt_close[i] * 0.999),
                "high": float(mkt_close[i] * 1.005),
                "low": float(mkt_close[i] * 0.995),
                "close": float(mkt_close[i]),
                "volume": 1000000,
            }
            for i in range(n_days)
        ]
    }
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC", "LT"]
    for s_idx, sym in enumerate(symbols):
        drift = 0.0002 * ((s_idx % 3) + 1)
        rets = rng.normal(drift, 0.013, size=n_days) + 0.5 * mkt_ret
        closes = (1000.0 + s_idx * 250.0) * np.cumprod(1.0 + rets)
        data[sym] = [
            {
                "timestamp": dates[i],
                "open": float(closes[i] * (1.0 + rng.normal(0, 0.002))),
                "high": float(closes[i] * 1.012),
                "low": float(closes[i] * 0.988),
                "close": float(closes[i]),
                "volume": int(500000 + s_idx * 10000 + rng.integers(0, 50000)),
            }
            for i in range(n_days)
        ]
    return data


def test_swing_alpha_trains_evaluates_and_respects_sector_cap(monkeypatch, tmp_path: Path) -> None:
    from intelligence import swing_alpha as sa

    monkeypatch.setattr(sa, "SWING_MODEL_PATH", tmp_path / "swing_15d_candidate.joblib")
    monkeypatch.setattr(sa, "SWING_REPORT_PATH", tmp_path / "swing_15d_report.json")

    hist = _make_synthetic_daily_universe(1050)
    report = sa.train_and_evaluate_swing_alpha(
        hist,
        initial_capital=50_000.0,
        holdout_sessions=120,
        save_artifacts=True,
    )

    assert len(report["dev_folds"]) == 5
    assert "blind_holdout" in report
    assert report["strategy_rules"]["product"] == "D"
    assert sa.SWING_MODEL_PATH.is_file()
    assert sa.SWING_REPORT_PATH.is_file()

    scored = sa.score_latest_swing_universe(hist, capital=50_000.0)
    assert scored["status"] == "ok"
    assert len(scored["all_ranked"]) == 8
    sector_counts: dict[str, int] = {}
    for rec in scored["recommendations"]:
        sector_counts[rec["sector"]] = sector_counts.get(rec["sector"], 0) + 1
        assert rec["predicted_15d_gross_pct"] > sa.SWING_DELIVERY_RT_COST_PCT
        assert rec["product"] == "D"
    assert all(c <= sa.SWING_MAX_PER_SECTOR for c in sector_counts.values())


@pytest.mark.asyncio
async def test_token_status_and_update_detect_jwt_expiry(monkeypatch, client) -> None:
    from api.routes import token as token_mod

    expired_jwt = _make_jwt(time.time() - 3600)
    valid_jwt = _make_jwt(time.time() + 7200)
    analytics_jwt = _make_jwt(time.time() + 86400 * 30)

    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", expired_jwt)
    monkeypatch.delenv("UPSTOX_ANALYTICS_TOKEN", raising=False)

    res = await client.get("/api/v1/token/status")
    assert res.status_code == 200
    body = res.json()
    assert body["token_set"] is True
    assert body["token_valid"] is False
    assert body["token_expired"] is True
    assert body["analytics_token_valid"] is False

    saved_env: dict[str, str] = {}
    monkeypatch.setattr(token_mod, "_update_env_var", lambda k, v: saved_env.__setitem__(k, v))

    bad_upd = await client.post("/api/v1/token/update", json={"access_token": expired_jwt})
    assert bad_upd.status_code == 200
    assert bad_upd.json()["success"] is False
    assert "expired" in bad_upd.json()["error"].lower()

    ok_upd = await client.post(
        "/api/v1/token/update",
        json={"access_token": valid_jwt, "analytics_token": analytics_jwt},
    )
    assert ok_upd.status_code == 200
    assert ok_upd.json()["success"] is True
    assert saved_env["UPSTOX_ACCESS_TOKEN"] == valid_jwt
    assert saved_env["UPSTOX_ANALYTICS_TOKEN"] == analytics_jwt

    res2 = await client.get("/api/v1/token/status")
    b2 = res2.json()
    assert b2["token_valid"] is True
    assert b2["token_expired"] is False
    assert b2["analytics_token_valid"] is True


@pytest.mark.asyncio
async def test_swing_signals_and_paper_scan_endpoints(monkeypatch, client) -> None:
    from api.routes import bot as bot_mod
    from intelligence import swing_alpha as sa
    from trading.paper_broker import PaperBroker

    fake_scored = {
        "status": "ok",
        "data_source": "cached_upstox_daily",
        "as_of": "2026-11-27T00:00:00+05:30",
        "stale_days": 1,
        "nifty_above_sma200": True,
        "nifty_above_sma50": True,
        "capital": 50000.0,
        "tranche_slot_pct": 3.33,
        "recommendations": [
            {
                "rank": 1,
                "symbol": "INFY",
                "sector": "IT",
                "direction": "LONG",
                "product": "D",
                "horizon_sessions": 15,
                "last_close": 1500.0,
                "predicted_15d_gross_pct": 2.1,
                "predicted_15d_net_pct": 1.78,
                "suggested_tranche_pct": 3.33,
                "suggested_budget_inr": 1665.0,
                "suggested_qty": 1,
            }
        ],
        "all_ranked": [],
    }
    monkeypatch.setattr(sa, "score_latest_swing_universe", lambda capital=50_000.0: dict(fake_scored))
    monkeypatch.setattr(bot_mod.engine, "broker", PaperBroker(initial_capital=50_000.0))

    sig_resp = await client.get("/api/v1/signals/swing")
    assert sig_resp.status_code == 200
    assert sig_resp.json()["recommendations"][0]["symbol"] == "INFY"

    scan_resp = await client.post("/api/v1/bot/swing/paper-scan?execute=true")
    assert scan_resp.status_code == 200
    scan_body = scan_resp.json()
    assert scan_body["executed"] is True
    assert len(scan_body["orders"]) == 1
    assert scan_body["orders"][0]["result"]["status"] == "FILLED"


@pytest.mark.asyncio
async def test_live_broker_supports_cnc_delivery_product(monkeypatch) -> None:
    from trading import live_broker as lb_mod

    captured_payloads = []

    class _Resp:
        def raise_for_status(self): return None
        def json(self): return {"data": {"order_id": "CNC-1"}}

    class _Client:
        def __init__(self, timeout: float = 8.0): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return None
        async def post(self, url: str, headers=None, json=None):
            captured_payloads.append(json)
            return _Resp()

    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "dummy-rest-token")
    monkeypatch.setattr(lb_mod, "upstox_client", None)
    safe_cfg = SimpleNamespace(live_trading_enabled=True, emergency_kill_switch_active=False)
    monkeypatch.setattr(lb_mod, "get_settings", lambda: safe_cfg)
    monkeypatch.setattr(lb_mod, "settings", safe_cfg)
    monkeypatch.setattr(lb_mod.httpx, "AsyncClient", _Client)

    broker = lb_mod.LiveBroker("k", "s", "https://127.0.0.1")
    res = await broker.place_order("NSE_EQ|INE009A01021", "BUY", 1, "MARKET", price=1500.0, product="D")
    assert res["status"] == "EXCHANGE_PENDING"
    assert captured_payloads[0]["product"] == "D"
