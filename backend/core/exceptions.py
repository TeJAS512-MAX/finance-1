"""
core/exceptions.py — Domain exceptions and FastAPI exception handlers.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


# ── Domain Exceptions ────────────────────────────────────────

class MarketIntelligenceError(Exception):
    """Base exception for all domain errors."""
    status_code: int = 500
    detail: str = "An internal error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(MarketIntelligenceError):
    status_code = 404
    detail = "Resource not found."


class ValidationError(MarketIntelligenceError):
    status_code = 422
    detail = "Validation error."


class DataQualityError(MarketIntelligenceError):
    """Raised when data does not meet quality thresholds."""
    status_code = 422
    detail = "Data quality check failed."


class StaleDataError(DataQualityError):
    """Raised when price or news data is too old to trust."""
    detail = "Data is stale — cannot proceed safely."


class LiveTradingDisabledError(MarketIntelligenceError):
    """Raised when live trading is attempted but disabled."""
    status_code = 403
    detail = (
        "Live trading is disabled. "
        "Set LIVE_TRADING_ENABLED=true only after all safety gates pass."
    )


class RiskLimitExceededError(MarketIntelligenceError):
    """Raised when a trade would violate a hard risk limit."""
    status_code = 422
    detail = "Trade rejected: risk limit exceeded."


class EmergencyKillSwitchActiveError(MarketIntelligenceError):
    """Raised when the emergency kill switch is active."""
    status_code = 503
    detail = (
        "Emergency kill switch is active. "
        "All new orders are halted. Manual review required."
    )


class InsufficientEvidenceError(MarketIntelligenceError):
    """Raised when the AI has insufficient verified evidence to act."""
    status_code = 422
    detail = "Insufficient verified evidence — NO TRADE."


class LLMHallucinationRisk(MarketIntelligenceError):
    """Raised when the LLM output cannot be verified against sources."""
    status_code = 422
    detail = (
        "AI-generated claim could not be verified against source data. "
        "Output suppressed to prevent hallucination."
    )


class BrokerError(MarketIntelligenceError):
    """Raised on broker connectivity or order placement errors."""
    status_code = 502
    detail = "Broker error."


class DataLeakageDetected(MarketIntelligenceError):
    """Raised when future data is detected in a backtest feature."""
    status_code = 422
    detail = "Data leakage detected — backtest aborted."


# ── FastAPI Exception Handlers ───────────────────────────────

async def domain_exception_handler(
    request: Request, exc: MarketIntelligenceError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "detail": exc.detail,
            "path": str(request.url),
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred.",
            "path": str(request.url),
        },
    )
