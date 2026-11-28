"""
core/logging_config.py — Structured logging configuration.

Uses structlog for structured, JSON-ready logging with:
  - Request ID propagation
  - UTC timestamps
  - Log level filtering
  - Audit log separation
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


# ── Custom processors ────────────────────────────────────────

def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add application-level context to every log record."""
    event_dict.setdefault("app", "market-intelligence-ai")
    return event_dict


def drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove 'color_message' added by uvicorn."""
    event_dict.pop("color_message", None)
    return event_dict


# ── Setup ────────────────────────────────────────────────────

def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    audit_log_path: str | None = None,
) -> None:
    """
    Configure structlog and Python stdlib logging.

    Call once at application startup (in main.py lifespan).
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        drop_color_message_key,
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # ── stdout handler ────────────────────────────────────────
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # ── audit file handler (separate file, WARNING+) ─────────
    handlers: list[logging.Handler] = [stdout_handler]
    if audit_log_path:
        audit_path = Path(audit_log_path)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_handler = logging.FileHandler(audit_path, encoding="utf-8")
        audit_handler.setFormatter(formatter)
        audit_handler.setLevel(logging.WARNING)
        handlers.append(audit_handler)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy libraries
    for noisy in ("httpx", "httpcore", "asyncio", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger with the given name."""
    return structlog.get_logger(name)


# ── Audit logger ─────────────────────────────────────────────

_audit_log = structlog.get_logger("audit")


def audit(
    action: str,
    user_id: str | None = None,
    **kwargs: Any,
) -> None:
    """
    Write a structured audit log entry.

    Every significant action (order placement, config change, model update,
    emergency trigger) must call this function.
    """
    _audit_log.warning(
        "AUDIT",
        action=action,
        user_id=user_id or "system",
        **kwargs,
    )
