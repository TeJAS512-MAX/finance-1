"""
tests/test_health.py — Health endpoint tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient) -> None:
    """GET /health must return 200 with status: ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_detail_safety_flags(client: AsyncClient) -> None:
    """
    GET /health/detail must expose safety flags.
    live_trading_enabled must be False in test environment.
    """
    response = await client.get("/health/detail")
    assert response.status_code == 200
    data = response.json()
    assert "safety_flags" in data
    # CRITICAL: live trading must be off in tests
    assert data["safety_flags"]["live_trading_enabled"] is False
    assert "risk_limits" in data
    assert data["safety_flags"]["emergency_kill_switch_active"] is False


@pytest.mark.asyncio
async def test_health_contains_disclaimer(client: AsyncClient) -> None:
    """Health detail must include research disclaimer."""
    response = await client.get("/health/detail")
    data = response.json()
    assert "disclaimer" in data
    assert "research" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_openapi_docs_available(client: AsyncClient) -> None:
    """OpenAPI docs must be accessible in non-production environments."""
    response = await client.get("/docs")
    # In dev/test mode docs are available (200 or 301 redirect)
    assert response.status_code in (200, 301, 307)


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient) -> None:
    """Prometheus metrics endpoint must be accessible."""
    response = await client.get("/metrics")
    assert response.status_code == 200
