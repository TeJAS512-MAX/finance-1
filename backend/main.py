"""
main.py — FastAPI application entry point.

Startup sequence:
  1. Configure logging
  2. Validate critical safety settings
  3. Initialize DB connection pool
  4. Register all API routers
  5. Register exception handlers
  6. Expose health + metrics endpoints
"""

from __future__ import annotations

import time
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.exceptions import (
    MarketIntelligenceError,
    domain_exception_handler,
    generic_exception_handler,
)
from core.logging_config import configure_logging, get_logger
from db.session import MongoDBManager

settings = get_settings()

# ── Logging (must be first) ───────────────────────────────────
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
)
logger = get_logger("main")


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    logger.info("🚀 Market Intelligence AI starting")
    
    # Init MongoDB
    MongoDBManager.get_client()

    yield  # Application is running

    logger.info("Market Intelligence AI shutting down")
    if MongoDBManager.client:
        MongoDBManager.client.close()


# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="Market Intelligence AI",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────

app.add_exception_handler(MarketIntelligenceError, domain_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ── Routers ──────────────────────────────────────────────────

from api.routes import health, signals, portfolio, bot, orders, news, finance
from api.routes.token import router as token_router

app.include_router(health.router, tags=["Health"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(bot.router, prefix="/api/v1/bot", tags=["Bot"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
app.include_router(token_router, prefix="/api/v1/token", tags=["Token"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["SME Finance"])
# trigger reload
