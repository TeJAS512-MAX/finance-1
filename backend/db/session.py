"""
db/session.py — Async MongoDB session factory using Motor.
"""

from __future__ import annotations

from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from core.config import get_settings

settings = get_settings()

# Initialize motor client lazily when the app starts
class MongoDBManager:
    client: AsyncIOMotorClient | None = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            # We don't initialize here globally to avoid event loop issues,
            # but usually FastAPI lifespan handles this.
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
        return cls.client

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency that yields a MongoDB database."""
    client = MongoDBManager.get_client()
    db = client[settings.mongodb_db_name]
    yield db
