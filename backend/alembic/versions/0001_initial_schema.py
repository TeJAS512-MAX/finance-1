"""
alembic/versions/0001_initial_schema.py — Initial database schema.

Creates all tables defined in the ORM models.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure extensions exist (also done in postgres/init.sql but safe to repeat)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # ── exchanges ─────────────────────────────────────────────
    op.create_table(
        "exchanges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("country", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("trading_hours_start", sa.String(10)),
        sa.Column("trading_hours_end", sa.String(10)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── companies ──────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("sector", sa.String(100), index=True),
        sa.Column("industry", sa.String(100)),
        sa.Column("country", sa.String(50), server_default="India"),
        sa.Column("headquarters", sa.String(255)),
        sa.Column("founded_year", sa.Integer()),
        sa.Column("website", sa.String(512)),
        sa.Column("employee_count", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_sector", "companies", ["sector"])
    op.create_index("ix_companies_name_trgm", "companies", ["name"], postgresql_using="gin",
                    postgresql_ops={"name": "gin_trgm_ops"})

    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("preferences", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── symbols ───────────────────────────────────────────────
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ticker", sa.String(30), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("exchanges.id"), nullable=False),
        sa.Column("isin", sa.String(20)),
        sa.Column("lot_size", sa.Integer(), server_default="1"),
        sa.Column("tick_size", sa.Float(), server_default="0.05"),
        sa.Column("market_cap", sa.Float()),
        sa.Column("float_shares", sa.Float()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("last_price", sa.Float()),
        sa.Column("last_price_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("ticker", "exchange_id", name="uq_ticker_exchange"),
    )
    op.create_index("ix_symbols_ticker", "symbols", ["ticker"])

    # ── company_relationships ────────────────────────────────
    op.create_table(
        "company_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("target_company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_inferred", sa.Boolean(), server_default=sa.false()),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("evidence", sa.Text()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── news_sources ──────────────────────────────────────────
    op.create_table(
        "news_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("domain", sa.String(255), unique=True, nullable=False),
        sa.Column("country", sa.String(50), server_default="India"),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("source_type", sa.String(50)),
        sa.Column("credibility_score", sa.Float(), server_default="0.5"),
        sa.Column("historical_accuracy", sa.Float(), server_default="0.5"),
        sa.Column("originality_score", sa.Float(), server_default="0.5"),
        sa.Column("correction_rate", sa.Float(), server_default="0"),
        sa.Column("confirmation_rate", sa.Float(), server_default="0"),
        sa.Column("duplicate_rate", sa.Float(), server_default="0"),
        sa.Column("total_articles", sa.Integer(), server_default="0"),
        sa.Column("confirmed_scoops", sa.Integer(), server_default="0"),
        sa.Column("is_primary_source", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── event_clusters ────────────────────────────────────────
    op.create_table(
        "event_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("event_type", sa.String(50)),
        sa.Column("canonical_headline", sa.String(1024), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_articles", sa.Integer(), server_default="1"),
        sa.Column("independent_sources", sa.Integer(), server_default="1"),
        sa.Column("verification_status", sa.String(30), server_default="SINGLE_SOURCE"),
        sa.Column("cluster_embedding", Vector(1536)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── news_items ────────────────────────────────────────────
    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("news_sources.id")),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_published_at", sa.DateTime(timezone=True)),
        sa.Column("headline", sa.String(1024), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("event_type", sa.String(50)),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("mentioned_companies", postgresql.ARRAY(sa.String())),
        sa.Column("credibility_score", sa.Float(), server_default="0.5"),
        sa.Column("verification_status", sa.String(30), server_default="UNVERIFIED_RUMOUR"),
        sa.Column("information_type", sa.String(30), server_default="UNVERIFIED_PUBLIC_RUMOUR"),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_clusters.id")),
        sa.Column("is_original", sa.Boolean(), server_default=sa.true()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("sentiment_score", sa.Float()),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("impact_score", sa.Float()),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("first_seen", sa.Boolean(), server_default=sa.false()),
        sa.Column("early_signal_score", sa.Float()),
        sa.Column("raw_metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_news_items_published_at", "news_items", ["published_at"])
    op.create_index("ix_news_items_event_type", "news_items", ["event_type"])
    op.create_index("ix_news_items_content_hash", "news_items", ["content_hash"])
    # Vector index for semantic search
    op.execute(
        "CREATE INDEX ix_news_items_embedding ON news_items "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # ── prices ────────────────────────────────────────────────
    op.create_table(
        "prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False, server_default="1D"),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("adjusted_close", sa.Float()),
        sa.Column("vwap", sa.Float()),
        sa.Column("trades", sa.Integer()),
        sa.Column("data_source", sa.String(50), server_default="yfinance"),
        sa.Column("is_adjusted", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("symbol_id", "date", "timeframe", name="uq_price_symbol_date_tf"),
    )
    op.create_index("ix_prices_symbol_date", "prices", ["symbol_id", "date"])

    # ── financials ────────────────────────────────────────────
    op.create_table(
        "financials",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("statement_type", sa.String(20), nullable=False),
        sa.Column("fiscal_year", sa.Integer()),
        sa.Column("currency", sa.String(10), server_default="INR"),
        sa.Column("unit", sa.String(20), server_default="crores"),
        sa.Column("source", sa.String(100)),
        sa.Column("is_audited", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_restated", sa.Boolean(), server_default=sa.false()),
        sa.Column("revenue", sa.Float()), sa.Column("gross_profit", sa.Float()),
        sa.Column("ebitda", sa.Float()), sa.Column("ebit", sa.Float()),
        sa.Column("net_income", sa.Float()), sa.Column("eps", sa.Float()),
        sa.Column("eps_diluted", sa.Float()), sa.Column("gross_margin", sa.Float()),
        sa.Column("ebitda_margin", sa.Float()), sa.Column("net_margin", sa.Float()),
        sa.Column("total_assets", sa.Float()), sa.Column("total_equity", sa.Float()),
        sa.Column("total_debt", sa.Float()), sa.Column("cash_and_equivalents", sa.Float()),
        sa.Column("net_debt", sa.Float()), sa.Column("current_ratio", sa.Float()),
        sa.Column("debt_to_equity", sa.Float()), sa.Column("operating_cash_flow", sa.Float()),
        sa.Column("capex", sa.Float()), sa.Column("free_cash_flow", sa.Float()),
        sa.Column("cash_conversion", sa.Float()), sa.Column("pe_ratio", sa.Float()),
        sa.Column("pb_ratio", sa.Float()), sa.Column("ps_ratio", sa.Float()),
        sa.Column("ev_ebitda", sa.Float()), sa.Column("roe", sa.Float()),
        sa.Column("roce", sa.Float()), sa.Column("roa", sa.Float()),
        sa.Column("revenue_growth_yoy", sa.Float()), sa.Column("earnings_growth_yoy", sa.Float()),
        sa.Column("raw_data", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("company_id", "period", "period_type", "statement_type",
                            name="uq_financial_period"),
    )

    # ── events ────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_clusters.id")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_public_source_at", sa.DateTime(timezone=True)),
        sa.Column("confirmation_at", sa.DateTime(timezone=True)),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("event_confidence", sa.Float(), server_default="0.5"),
        sa.Column("potential_financial_impact", sa.String(10)),
        sa.Column("potential_market_impact", sa.String(10)),
        sa.Column("time_horizon", sa.String(15)),
        sa.Column("uncertainty", sa.Float(), server_default="0.5"),
        sa.Column("primary_source_url", sa.String(2048)),
        sa.Column("independent_sources_count", sa.Integer(), server_default="1"),
        sa.Column("verification_status", sa.String(30), server_default="SINGLE_SOURCE"),
        sa.Column("price_before", sa.Float()), sa.Column("price_after", sa.Float()),
        sa.Column("return_before_event", sa.Float()), sa.Column("return_after_event", sa.Float()),
        sa.Column("volume_change_pct", sa.Float()), sa.Column("abnormal_return", sa.Float()),
        sa.Column("priced_in_score", sa.Float()), sa.Column("event_surprise_score", sa.Float()),
        sa.Column("market_expectation", sa.Float()), sa.Column("analyst_consensus", sa.Float()),
        sa.Column("previous_guidance", sa.Float()), sa.Column("actual_result", sa.Float()),
        sa.Column("expectation_verdict", sa.String(15)),
        sa.Column("market_reaction_pct", sa.Float()), sa.Column("reaction_speed_ms", sa.Float()),
        sa.Column("reaction_alignment", sa.String(30)),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("raw_metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_company_id", "events", ["company_id"])

    # ── portfolios ────────────────────────────────────────────
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(20), server_default="paper"),
        sa.Column("initial_capital", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="INR"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("current_cash", sa.Float()),
        sa.Column("total_equity", sa.Float()), sa.Column("total_unrealised_pnl", sa.Float()),
        sa.Column("total_realised_pnl", sa.Float()), sa.Column("peak_equity", sa.Float()),
        sa.Column("max_drawdown", sa.Float()), sa.Column("sharpe_ratio", sa.Float()),
        sa.Column("sortino_ratio", sa.Float()), sa.Column("total_return_pct", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── trade_theses ──────────────────────────────────────────
    op.create_table(
        "trade_theses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id"), nullable=False),
        sa.Column("direction", sa.String(10)),
        sa.Column("signal", sa.String(20)),
        sa.Column("catalyst_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id")),
        sa.Column("catalyst_description", sa.Text()),
        sa.Column("evidence", postgresql.ARRAY(sa.String())),
        sa.Column("event_status", sa.String(30)),
        sa.Column("financial_impact", sa.Text()), sa.Column("technical_context", sa.Text()),
        sa.Column("market_regime", sa.String(30)), sa.Column("priced_in_assessment", sa.Text()),
        sa.Column("bull_case", sa.Text()), sa.Column("bear_case", sa.Text()),
        sa.Column("key_risks", postgresql.ARRAY(sa.String())),
        sa.Column("invalidation_conditions", postgresql.ARRAY(sa.String())),
        sa.Column("time_horizon", sa.String(20)),
        sa.Column("confidence", sa.Integer()),
        sa.Column("model_agreement_score", sa.Float()),
        sa.Column("source_quality", sa.String(30)),
        sa.Column("why_it_matters", sa.Text()),
        sa.Column("expected_financial_impact", sa.Text()),
        sa.Column("market_reaction_assessment", sa.Text()),
        sa.Column("already_priced_in", sa.Text()),
        sa.Column("fundamental_context", sa.Text()),
        sa.Column("actual_return_pct", sa.Float()),
        sa.Column("thesis_was_correct", sa.Boolean()),
        sa.Column("invalidation_triggered", sa.String(255)),
        sa.Column("thesis_status", sa.String(20), server_default="ACTIVE"),
        sa.Column("generated_by_model", sa.String(100)),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_llm_output", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── orders ────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id"), nullable=False),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trade_theses.id")),
        sa.Column("order_type", sa.String(20)),
        sa.Column("direction", sa.String(10)),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("limit_price", sa.Float()), sa.Column("stop_price", sa.Float()),
        sa.Column("requested_price", sa.Float()),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("filled_quantity", sa.Float(), server_default="0"),
        sa.Column("avg_fill_price", sa.Float()),
        sa.Column("commission", sa.Float(), server_default="0"),
        sa.Column("slippage", sa.Float(), server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("filled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("is_paper", sa.Boolean(), server_default=sa.true()),
        sa.Column("broker_order_id", sa.String(100)),
        sa.Column("rejection_reason", sa.String(512)),
        sa.Column("strategy", sa.String(50)),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── positions ─────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("symbols.id"), nullable=False),
        sa.Column("direction", sa.String(10)),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_entry_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float()), sa.Column("market_value", sa.Float()),
        sa.Column("unrealised_pnl", sa.Float()), sa.Column("unrealised_pnl_pct", sa.Float()),
        sa.Column("realised_pnl", sa.Float(), server_default="0"),
        sa.Column("total_commission", sa.Float(), server_default="0"),
        sa.Column("stop_loss_price", sa.Float()), sa.Column("take_profit_price", sa.Float()),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trade_theses.id")),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_open", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("portfolio_id", "symbol_id", name="uq_position_portfolio_symbol"),
    )

    # ── risk_events ───────────────────────────────────────────
    op.create_table(
        "risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), server_default="HIGH"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id")),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("requires_manual_review", sa.Boolean(), server_default=sa.true()),
        sa.Column("kill_switch_activated", sa.Boolean(), server_default=sa.false()),
        sa.Column("raw_metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── backtest_runs ─────────────────────────────────────────
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("strategy", sa.String(100), nullable=False),
        sa.Column("data_start", sa.DateTime(timezone=True)),
        sa.Column("data_end", sa.DateTime(timezone=True)),
        sa.Column("data_sources", postgresql.JSONB()),
        sa.Column("features_used", postgresql.JSONB()),
        sa.Column("model_version", sa.String(100)),
        sa.Column("parameters", postgresql.JSONB()),
        sa.Column("commission_pct", sa.Float(), server_default="0.03"),
        sa.Column("slippage_pct", sa.Float(), server_default="0.05"),
        sa.Column("train_start", sa.DateTime(timezone=True)),
        sa.Column("train_end", sa.DateTime(timezone=True)),
        sa.Column("validation_start", sa.DateTime(timezone=True)),
        sa.Column("validation_end", sa.DateTime(timezone=True)),
        sa.Column("test_start", sa.DateTime(timezone=True)),
        sa.Column("test_end", sa.DateTime(timezone=True)),
        sa.Column("total_return_pct", sa.Float()), sa.Column("cagr_pct", sa.Float()),
        sa.Column("volatility_pct", sa.Float()), sa.Column("sharpe_ratio", sa.Float()),
        sa.Column("sortino_ratio", sa.Float()), sa.Column("max_drawdown_pct", sa.Float()),
        sa.Column("calmar_ratio", sa.Float()), sa.Column("profit_factor", sa.Float()),
        sa.Column("win_rate_pct", sa.Float()), sa.Column("expectancy", sa.Float()),
        sa.Column("total_trades", sa.Integer()),
        sa.Column("oos_total_return_pct", sa.Float()), sa.Column("oos_sharpe_ratio", sa.Float()),
        sa.Column("limitations", sa.Text()), sa.Column("report_path", sa.String(512)),
        sa.Column("mlflow_run_id", sa.String(100)),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── alerts ────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), server_default="INFO"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("channels", postgresql.JSONB()),
        sa.Column("reference_id", sa.String(100)),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("raw_metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── audit.audit_logs ──────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("request_id", sa.String(100)),
        sa.Column("outcome", sa.String(20), server_default="SUCCESS"),
        sa.Column("detail", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="audit",
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], schema="audit")
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], schema="audit")

    # ── trade_journal ─────────────────────────────────────────
    op.create_table(
        "trade_journal",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trade_theses.id")),
        sa.Column("why_entered", sa.Text()),
        sa.Column("what_information_caused_entry", sa.Text()),
        sa.Column("what_ai_expected", sa.Text()),
        sa.Column("what_actually_happened", sa.Text()),
        sa.Column("what_changed", sa.Text()),
        sa.Column("why_exited", sa.Text()),
        sa.Column("what_was_wrong", sa.Text()),
        sa.Column("what_was_right", sa.Text()),
        sa.Column("lesson", sa.Text()),
        sa.Column("market_regime_at_entry", sa.String(30)),
        sa.Column("market_regime_at_exit", sa.String(30)),
        sa.Column("entry_confidence", sa.Integer()),
        sa.Column("realised_pnl_pct", sa.Float()),
        sa.Column("holding_days", sa.Integer()),
        sa.Column("counterfactual_result", sa.Text()),
        sa.Column("counterfactual_no_trade_outcome_pct", sa.Float()),
        sa.Column("what_evidence_would_change_decision", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("trade_journal")
    op.drop_table("audit_logs", schema="audit")
    op.drop_table("alerts")
    op.drop_table("backtest_runs")
    op.drop_table("risk_events")
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_table("trade_theses")
    op.drop_table("portfolios")
    op.drop_table("events")
    op.drop_table("financials")
    op.drop_table("prices")
    op.drop_table("news_items")
    op.drop_table("event_clusters")
    op.drop_table("news_sources")
    op.drop_table("company_relationships")
    op.drop_table("symbols")
    op.drop_table("users")
    op.drop_table("companies")
    op.drop_table("exchanges")
