# Market Intelligence AI

> A production-quality AI-powered market intelligence and algorithmic trading **research** platform for Indian equities (NSE/BSE).

---

## ⚠️ Important Disclaimers

- This system is a **research and paper-trading tool only**.
- **Live trading is disabled by default** and requires explicit multi-step configuration.
- The system uses only **legally and publicly available information**.
- This is **NOT** financial advice. Past performance does not guarantee future results.
- Confidence scores are **NOT** profit probabilities.
- The system is designed to frequently decide **NO TRADE** when evidence is weak.

---

## Project Overview

```
Market Intelligence AI
├── Data Ingestion Layer        → OHLCV, financials, news, filings
├── Intelligence Engines        → Event detection, impact analysis, sentiment
├── Knowledge Graph             → Company relationships and dependencies
├── AI Analysis Layer           → Bull/Bear/Judge agents, thesis generation
├── Risk Management             → Hard limits that AI cannot override
├── Paper Trading Engine        → Virtual execution with realistic simulation
├── Backtesting Engine          → Event-driven, no look-ahead bias
├── Portfolio Intelligence      → Regime-aware capital allocation
└── Dashboard                   → Professional financial terminal UI
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | MongoDB + Redis |
| Live Market Data | Zerodha Kite Connect WebSocket + historical candles |
| Historical / Backtesting Data | Yahoo Finance |
| Cache / Queue | Redis 7, Celery |
| ML / AI | PyTorch, scikit-learn, XGBoost, LightGBM, MLflow |
| NLP | Modular LLM provider, embeddings, RAG |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Infrastructure | Docker, Docker Compose |

> Live market data is sourced from a broker/API such as Zerodha Kite Connect. Yahoo Finance is used only for historical and backtesting data, not for the live market feed.

---

## Project Structure

```
market-intelligence-ai/
├── backend/
│   ├── api/            # FastAPI routes (including /api/v1/finance SME Finance Hub)
│   ├── core/           # Config, logging, security, exceptions
│   ├── db/             # MongoDB / SQLAlchemy session
│   ├── models/         # ORM models (SQLAlchemy)
│   ├── schemas/        # Pydantic schemas (incl. SME finance schemas)
│   ├── services/       # Abstract provider interfaces
│   ├── data/           # Ingestion, market data, SME finance archetypes
│   ├── finance/        # Integrated SME Finance Engine (CNS, agents, causal, physics, calculators)
│   ├── ml/             # Regime detector, sentiment, ensemble
│   ├── ai/             # Thesis engine, Bull/Bear/Judge, priced-in
│   ├── trading/        # Paper broker, sizing, exit engine
│   ├── risk/           # Risk manager, circuit breakers
│   ├── backtesting/    # Event-driven backtester
│   ├── portfolio/      # Portfolio engine, capital allocation
│   ├── notifications/  # Alert system + providers
│   ├── security/       # Audit logs, RBAC
│   ├── tests/          # Unit + integration + finance + security tests
│   ├── alembic/        # DB migrations
│   ├── main.py         # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/            # Next.js 14 app router pages
│   ├── components/     # Reusable React components (incl. components/finance/)
│   ├── lib/            # API client, utils, and lib/finance/ state & API
│   ├── types/          # TypeScript types
│   ├── services/       # Frontend API service layer
│   ├── package.json
│   └── Dockerfile
├── portfolio_intelligence/   # Advanced portfolio intelligence modules
│   ├── models.py             # Shared dataclasses/enums
│   ├── information_decay.py  # Item 51: Information Decay
│   ├── expectation_reality.py # Item 52: Expectation vs Reality
│   ├── counterfactual.py     # Item 53: Counterfactual Analysis
│   ├── regime_strategy.py    # Item 54: Regime-Switching Strategies
│   ├── capital_allocation.py # Item 55: Capital Allocation
│   ├── emergency_kill.py     # Item 56: Emergency Kill Switch
│   ├── backtest_report.py    # Item 57: Research Integrity
│   └── live_trading_safety.py # Item 58: Live Trading Safety
├── infrastructure/
│   └── docker-compose.yml
├── scripts/
│   ├── init_db.py
│   └── seed_data.py
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── data_sources.md
├── .env.example
├── .gitignore
└── README.md
```

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project skeleton, Docker, DB, FastAPI, Next.js | ✅ |
| 2 | Market data ingestion, company DB | 🔄 |
| 3 | News ingestion, credibility, deduplication | 🔄 |
| 4 | Company knowledge graph | 🔄 |
| 5 | Fundamental + technical analysis | 🔄 |
| 6 | AI thesis engine, Bull/Bear/Judge | 🔄 |
| 7 | Backtesting engine | 🔄 |
| 8 | Paper trading | 🔄 |
| 9 | Risk engine | 🔄 |
| 10 | Full dashboard | 🔄 |
| 11 | AI trade journal | 🔄 |
| 12 | Model evaluation | 🔄 |
| 13 | Optional broker integration | ⏳ |
| 14 | Business Finance Phase (SME Finance Hub under AI Analysis) | ✅ |

---

## Getting Started

### Prerequisites

- Docker 24+
- Docker Compose 2.20+
- (Optional for local dev) Python 3.12+, Node 20+

### 1. Clone and configure

```bash
git clone <repo>
cd market-intelligence-ai
cp .env.example .env
# Edit .env — fill in your API keys
```

### 2. Start all services

```bash
docker compose up -d
```

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Open the dashboard

- Frontend & SME Finance Hub: http://localhost:3000 (select **SME Finance Hub** under **BUSINESS FINANCE** in the dashboard sidebar)
- Unified API docs (Market Intelligence + `/api/v1/finance/*`): http://localhost:8000/docs
- MLflow: http://localhost:5000

On Windows, `start.bat` starts the unified FastAPI backend on port 8000 and the unified Next.js dashboard on port 3000.
Before running it, close any existing app using ports 3000 or 8000.

---

## Key Design Principles

1. **NO look-ahead bias** — every feature respects its actual timestamp
2. **NO guaranteed returns** — confidence ≠ profit probability
3. **NO insider information** — only legally public data
4. **Risk controls override AI** — hard limits cannot be disabled by models
5. **Paper trading by default** — `LIVE_TRADING_ENABLED=false`
6. **Explainability mandatory** — every decision traces to its sources
7. **NO TRADE is valid** — the system frequently selects no-trade
8. **Modular providers** — market data, LLM, broker, notifications are swappable

---

## Environment Variables

See [.env.example](.env.example) for all configuration options.

Critical safety variables:

```
LIVE_TRADING_ENABLED=false          # MUST stay false for paper/research
EMERGENCY_KILL_SWITCH_ACTIVE=false  # Set to true to halt all activity
PAPER_TRADING_INITIAL_CAPITAL=50000 # Virtual INR starting balance
MAX_PORTFOLIO_RISK_PCT=2.0          # Maximum % of portfolio per trade
MAX_DAILY_LOSS_PCT=5.0              # Daily loss circuit breaker
```

---

## API Documentation

Auto-generated OpenAPI docs available at: `http://localhost:8000/docs`

---

## Testing

```bash
# All tests
docker compose exec backend pytest

# Specific suites
docker compose exec backend pytest tests/test_risk.py -v
docker compose exec backend pytest tests/test_paper_trading.py -v

# Critical: verify live trading cannot be activated accidentally
docker compose exec backend pytest tests/test_live_trading_safety.py -v
```

## Next-session return research

The optional research candidate estimates the next session's executable
open-to-close return after configured commission and slippage. It selects
**TRADE** only when the predicted net return is positive; otherwise it returns
**NO_TRADE**. This output is a research estimate, not a probability or trading
instruction, and it does not place orders. Both training and live inference use
the configured Upstox API; this predictor does not read Yahoo data or fall back
to a cached/alternate provider.

Training compares regression models through walk-forward validation against a
zero-return baseline, then evaluates the selected model on a separate
date-blocked holdout. Only a candidate that beats the walk-forward baseline,
has a positive date-block-bootstrap interval for error improvement, and passes
the configured paper profit/drawdown gates is eligible for research display.
Otherwise forecasts are withheld. The target and paper simulation use the same
configured commission/slippage; taxes and exchange/regulatory fees are not
included.

Training uses Upstox's V3 daily historical-candle endpoint, which documents
daily data from January 2000 and a maximum retrieval window of one decade per
request ([Upstox V3 candle API documentation](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)).
The default is 3,650 calendar days; `STOCK_DIRECTION_DAYS_BACK` can reduce that
window but cannot exceed 3,650 days.

On Windows, run from the project root:

```powershell
Set-Location .\backend
$env:STOCK_DIRECTION_DAYS_BACK = "3650" # Optional; must be 1 through 3650
# Optional comma-separated subset; defaults to the configured Upstox instruments.
# $env:STOCK_DIRECTION_SYMBOLS = "RELIANCE,INFY,TCS"
.\.venv\Scripts\python.exe -m backtesting.train_stock_direction
```

For training and read-only market data, configure Upstox's
`UPSTOX_ANALYTICS_TOKEN` in the backend environment or `.env`. Upstox documents
the [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/)
as valid for one year and supporting historical-data GET APIs; it must be
regenerated annually, not daily. Keep it separate from
`UPSTOX_ACCESS_TOKEN`, the daily OAuth token used for live trading. The
Analytics Token cannot place or modify orders. The regular access token remains
a fallback for market-data requests, but is not needed for training when the
Analytics Token is configured. The API key and secret are not needed to fetch
training data with an Analytics Token.

Each run fetches fresh Upstox candles. Failed symbols are reported and omitted;
their old cached rows are never used for that run. The trainer reserves the
latest 90 sessions for a date-blocked holdout and uses the full available
pre-test window within Upstox's V3 history. It includes stock identity in
the pooled model and compares regression candidates, including an equal-vote
tree ensemble, using time-ordered paper results, with prediction error as a
tie-breaker. When available, it adds leakage-safe NIFTY 50 return and volatility
features; candidates trained with this context require a same-session NIFTY 50
candle at inference. A no-trade baseline remains eligible when predictive
models do not show positive paper results. The report also includes a fixed
long-only paper
simulation from the configured starting capital, with the latest next-session
open-to-close prices, configured commission/slippage, a ₹500 profit target, and
a ₹1,000 maximum drawdown. A candidate must beat the return-error baselines and
reach the paper profit target in both validation and holdout without breaching
the drawdown limit to replace the currently installed model; repeated tuning
to force a target is not performed. Because the historical holdout has already
been inspected, the current training entry point explicitly disables
promotion from that holdout. Shadow results do not auto-promote a model; review
the prospective evidence before changing the display gate. The live
signal dashboard uses Upstox daily candles for inference and displays forecasts
only from a qualifying installed research artifact; it does not train inside a
signal request. Candle timestamps are normalized to the Asia/Kolkata session
date before splitting and backtesting, so formatting differences cannot split
one trading day into multiple folds or simulated sessions.

Every successful training run also saves the evaluated artifact as a separate
shadow candidate, even when it fails the display gate. This artifact is not
used by the dashboard or order system. After market close, run the following
once per session to record forecasts from candles strictly newer than the
candidate's training cutoff for each competing model, including the no-trade
baseline, and resolve prior forecasts against the next Upstox candle:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m backtesting.stock_direction_shadow
```

The forward log is written to
`backend/data/stock_direction_shadow_predictions.json`; it records decisions,
estimated and realized after-cost returns, and per-model paper simulations.
Shadow fetches are temporary and do not replace the longer training-history
cache.
Keep the same shadow candidate in place for the prospective evaluation period:
do not rerun training or tune from these observations during the 60–90 session
evaluation. The installed model remains withheld unless it independently
passes the existing promotion gates.

On Windows, a scheduled task can invoke
`backend/backtesting/run_stock_direction_shadow_scheduled.ps1` after market
close. The runner caps the evaluation at 90 forward sessions and removes its
scheduled task after all forecasts for those sessions have resolved.

A separate regime-aware cross-sectional challenger is available for research:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m backtesting.train_stock_direction_cross_sectional
```

It ranks stocks within each session, gates trades with a separate after-cost
return estimate, and includes market trend/high-volatility features. Its model
and report are saved separately under `backend/data/`; it never replaces the
active candidate or the scheduled evaluation. Historical test results are
descriptive only; any later deployment consideration requires a separate
prospective shadow evaluation.

Its Windows scheduled runner uses a separate log and waits for the schema-10
evaluation completion marker. It then retrains once on the latest completed
Upstox history, freezes that candidate, and runs its own 90-session evaluation:
`backend/backtesting/run_stock_direction_cross_sectional_shadow_scheduled.ps1`.

The model and evaluation report are saved as
`backend/data/stock_direction_candidate.joblib` and
`backend/data/stock_direction_candidate_meta.json`. The most recent training
attempt, including a candidate rejected by the gate, is recorded in
`backend/data/stock_direction_last_training_report.json`. The separate
forward-evaluation artifact is
`backend/data/stock_direction_shadow_candidate.joblib`. These are research
artifacts only; the candidate does not change order decisions or enable live
trading. Dashboard values are uncalibrated return estimates, not probabilities,
accuracy guarantees, or profit guarantees. Upstox may return no fresh history
for some symbols; those symbols are excluded instead of using stale data.

The binary model artifact is intentionally excluded from Git. Run training on
the deployment host and keep its artifact storage persistent; do not copy a
scikit-learn pickle between incompatible library versions. Older artifacts
trained under the previous source/schema are rejected and must be rebuilt from
Upstox data. Generate an Analytics Token in the Upstox Developer Apps page and
store it locally as `UPSTOX_ANALYTICS_TOKEN`; never paste it into source code,
commit it, or send it in chat.

---

## Legal & Compliance

- This system only uses **publicly available** information
- All data sources are documented
- No broker credentials stored in frontend code
- All API keys managed via environment variables
- Full audit log of every decision and action
- Users are responsible for compliance with applicable laws and regulations

---

## License

Research and educational use only. See LICENSE for details.
