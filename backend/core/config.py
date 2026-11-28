"""
core/config.py — Centralized configuration via Pydantic Settings.

All environment variables are typed, validated, and defaulted here.
No other module should read os.environ directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "Market Intelligence AI"
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: SecretStr = Field(..., min_length=32)
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://localhost:8001",
    ]

    # ── Database ─────────────────────────────────────────────
    mongodb_url: str = Field(
        default="mongodb://localhost:27017/"
    )
    mongodb_db_name: str = "market_intelligence"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ── MLflow ───────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "market-intelligence-ai"

    # ── Market Data ──────────────────────────────────────────
    # Live market data must come from a real broker/API such as Kite Connect.
    # Yahoo Finance is historical/backtesting-only data, not the live feed.
    market_data_provider: Literal["yfinance", "alpha_vantage", "polygon", "nse_official"] = "yfinance"
    live_market_data_provider: Literal["zerodha", "upstox", "fyers", "nse_official"] = "zerodha"
    historical_market_data_provider: Literal["yfinance", "alpha_vantage", "polygon", "nse_official"] = "yfinance"
    alpha_vantage_api_key: Optional[SecretStr] = None
    polygon_api_key: Optional[SecretStr] = None
    twelve_data_api_key: Optional[SecretStr] = None
    nse_api_base_url: str = "https://www.nseindia.com"
    bse_api_base_url: str = "https://api.bseindia.com"

    # ── News ─────────────────────────────────────────────────
    news_provider: str = "gnews"
    gnews_api_key: Optional[SecretStr] = None
    newsapi_key: Optional[SecretStr] = None

    # ── LLM ──────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "google", "local_ollama"] = "openai"
    openai_api_key: Optional[SecretStr] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[SecretStr] = None
    anthropic_model: str = "claude-3-haiku-20240307"
    google_ai_api_key: Optional[SecretStr] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── Live Trading Safety (CRITICAL) ───────────────────────
    # !! This must ALWAYS default to False !!
    live_trading_enabled: bool = False

    # ── Paper Trading ────────────────────────────────────────
    paper_trading_initial_capital: float = 50_000.0
    paper_trading_currency: str = "INR"

    # ── Broker (only used when live_trading_enabled=True) ────
    zerodha_api_key: Optional[SecretStr] = None
    zerodha_api_secret: Optional[SecretStr] = None
    zerodha_user_id: Optional[str] = None

    # ── Risk Limits (HARD — cannot be overridden by AI) ──────
    max_portfolio_risk_pct: float = Field(default=5.0, ge=0.1, le=20.0)
    max_position_size_pct: float = Field(default=10.0, ge=1.0, le=50.0)
    max_sector_exposure_pct: float = Field(default=30.0, ge=5.0, le=100.0)
    max_daily_loss_pct: float = Field(default=5.0, ge=0.5, le=30.0)
    max_drawdown_pct: float = Field(default=20.0, ge=5.0, le=50.0)
    max_orders_per_minute: int = Field(default=10, ge=1, le=100)
    min_signal_confidence: int = Field(default=40, ge=0, le=100)
    max_correlation_new_position: float = Field(default=0.7, ge=0.0, le=1.0)

    # ── Emergency Kill Switch ─────────────────────────────────
    emergency_kill_switch_active: bool = False
    emergency_kill_requires_manual_reset: bool = True

    # ── Data Quality ─────────────────────────────────────────
    max_price_staleness_seconds: int = 60
    max_news_staleness_hours: int = 24
    data_quality_min_completeness: float = 0.8

    # ── Rate Limiting ─────────────────────────────────────────
    api_rate_limit_per_minute: int = 60
    news_fetch_interval_seconds: int = 300
    price_fetch_interval_seconds: int = 60

    # ── Backtesting Defaults ──────────────────────────────────
    backtest_default_commission_pct: float = 0.03
    backtest_default_slippage_pct: float = 0.05
    backtest_default_initial_capital: float = 1_000_000.0

    # ── Security ─────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    bcrypt_rounds: int = Field(default=12, ge=10, le=14)

    # ── Logging ──────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    audit_log_enabled: bool = True

    # ── Feature Flags ─────────────────────────────────────────
    feature_knowledge_graph: bool = True
    feature_llm_thesis: bool = True
    feature_technical_analysis: bool = True
    feature_fundamental_analysis: bool = True
    feature_sentiment_analysis: bool = True
    feature_backtesting: bool = True
    feature_paper_trading: bool = True
    feature_sme_finance: bool = True  # Set False to hide Tax/Finance in standalone Stock-AI B2B mode

    # ── B2B API Auth ───────────────────────────────────────────
    # When api_auth_enabled=True (or app_env="production"), all trading/AI
    # routes require either Authorization: Bearer <JWT> or X-API-Key: <key>.
    # Format: comma-separated "key:role" pairs, e.g. "abc123:admin,xyz456:viewer"
    api_auth_enabled: bool = False  # Explicit opt-in; auto-enforced in production
    b2b_api_keys: str = ""          # Comma-separated "key:role" B2B client credentials

    # ── Notification ──────────────────────────────────────────
    notification_email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[SecretStr] = None
    alert_email_from: Optional[str] = None
    alert_email_to: Optional[str] = None
    notification_webhook_enabled: bool = False
    webhook_url: Optional[str] = None

    # ── Validation ───────────────────────────────────────────

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, v: object) -> object:
        """Treat common non-boolean build or log-level values like 'release' or 'WARN' as False."""
        if isinstance(v, str) and v.strip().lower() in {
            "release",
            "prod",
            "production",
            "warn",
            "warning",
            "info",
            "error",
            "critical",
            "off",
            "none",
            "null",
            "",
        }:
            return False
        return v

    @field_validator("live_trading_enabled", mode="after")
    @classmethod
    def validate_live_trading(cls, v: bool) -> bool:
        """Warn loudly if live trading is being enabled."""
        if v:
            import warnings
            warnings.warn(
                "⚠️  LIVE TRADING IS BEING ENABLED. "
                "Ensure all safety gates have been passed before proceeding.",
                stacklevel=2,
            )
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
