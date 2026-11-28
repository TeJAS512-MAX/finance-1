"""
tests/conftest.py — Shared pytest fixtures.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test environment before importing app code
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mi_user:changeme@localhost:5432/market_intelligence_test")
os.environ.setdefault("LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("EMERGENCY_KILL_SWITCH_ACTIVE", "false")

from db.base import Base
from db.session import get_db
from main import app


# ── Async event loop ──────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ── In-memory SQLite for unit tests ───────────────────────────
# Note: SQLite doesn't support pgvector; for integration tests use Postgres.

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    # SQLite doesn't support all PG features; we create tables manually for tests
    async with engine.begin() as conn:
        # Simplified table creation for unit tests
        await conn.run_sync(lambda c: None)  # no-op: use mocks in unit tests
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
