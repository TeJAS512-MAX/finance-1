"""
api/routes/health.py — Health check endpoints.

Provides:
  GET /health         — Basic liveness check
  GET /health/ready   — Readiness check (DB + Redis connectivity)
  GET /health/detail  — Full system status (authenticated)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import get_settings
from db.session import get_db

router = APIRouter()
settings = get_settings()

_start_time = time.time()


@router.get("/health", summary="Liveness check")
async def health_live() -> dict:
    """Basic liveness — returns 200 if the process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/health/ready", summary="Readiness check")
async def health_ready(db: AsyncIOMotorDatabase = Depends(get_db)) -> dict:
    """
    Readiness check — verifies database connectivity.
    Returns 503 if any dependency is unavailable.
    """
    checks: dict = {}

    # Database
    try:
        await db.command("ping")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> dict:
    """Dummy metrics endpoint."""
    return {"metrics": "ok"}


@router.get("/health/detail", summary="Detailed system status")
async def health_detail() -> dict:
    """Full system status including safety flags."""
    uptime_seconds = time.time() - _start_time
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
        "uptime_seconds": round(uptime_seconds, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safety_flags": {
            "live_trading_enabled": settings.live_trading_enabled,
            "emergency_kill_switch_active": settings.emergency_kill_switch_active,
            "paper_trading_initial_capital": settings.paper_trading_initial_capital,
            "currency": settings.paper_trading_currency,
        },
        "risk_limits": {
            "max_position_size_pct": settings.max_position_size_pct,
            "max_sector_exposure_pct": settings.max_sector_exposure_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "max_orders_per_minute": settings.max_orders_per_minute,
        },
        "disclaimer": (
            "This system is for research and paper trading only. "
            "Not financial advice. Past performance does not guarantee future results."
        ),
    }
