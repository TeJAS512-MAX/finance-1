"""
models.py — Shared data models for the Portfolio Intelligence System.

All engines share these dataclasses/enums to maintain a single source of truth.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MarketRegime(Enum):
    BULL_TREND       = "bull_trend"
    BEAR_TREND       = "bear_trend"
    RANGING          = "ranging"
    HIGH_VOLATILITY  = "high_volatility"
    LOW_VOLATILITY   = "low_volatility"
    CRISIS           = "crisis"
    RECOVERY         = "recovery"
    UNKNOWN          = "unknown"


class StrategyFamily(Enum):
    TREND           = "trend"
    MOMENTUM        = "momentum"
    MEAN_REVERSION  = "mean_reversion"
    EVENT_DRIVEN    = "event_driven"
    FUNDAMENTAL     = "fundamental"
    NEWS_DRIVEN     = "news_driven"


class ExpectationResult(Enum):
    BEAT      = "beat"
    IN_LINE   = "in_line"
    MISS      = "miss"
    UNCERTAIN = "uncertain"


class TradeDirection(Enum):
    LONG  = "long"
    SHORT = "short"


class AllocationDecision(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REDUCED  = "reduced"


class EmergencyTrigger(Enum):
    UNEXPECTED_API_BEHAVIOR     = "unexpected_api_behavior"
    ABNORMAL_ORDER_FREQUENCY    = "abnormal_order_frequency"
    DATA_CORRUPTION             = "data_corruption"
    STALE_PRICES                = "stale_prices"
    MODEL_FAILURE               = "model_failure"
    EXCESSIVE_LOSSES            = "excessive_losses"
    UNEXPECTED_PORTFOLIO_EXPOSURE = "unexpected_portfolio_exposure"
    DUPLICATE_ORDERS            = "duplicate_orders"
    BROKER_CONNECTIVITY         = "broker_connectivity"


class LiveTradingGate(Enum):
    BACKTEST_PASSED        = "backtest_passed"
    OOS_TEST_PASSED        = "oos_test_passed"
    PAPER_TRADING_PASSED   = "paper_trading_passed"
    RISK_CONFIG_SET        = "risk_config_set"
    MANUAL_CONFIRMED       = "manual_confirmed"


# ---------------------------------------------------------------------------
# Shared data models
# ---------------------------------------------------------------------------

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    sector: str
    asset_class: str
    beta: float = 1.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealised_pnl(self) -> float:
        return (self.current_price - self.avg_entry_price) * self.quantity

    @property
    def unrealised_pct(self) -> float:
        if self.avg_entry_price == 0:
            return 0.0
        return (self.current_price - self.avg_entry_price) / self.avg_entry_price


@dataclass
class Portfolio:
    positions: Dict[str, Position] = field(default_factory=dict)
    cash: float = 0.0
    total_equity_peak: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> float:
        return self.total_market_value + self.cash

    @property
    def drawdown(self) -> float:
        if self.total_equity_peak == 0:
            return 0.0
        return (self.total_equity_peak - self.total_equity) / self.total_equity_peak

    def sector_concentrations(self) -> Dict[str, float]:
        equity = self.total_equity
        if equity == 0:
            return {}
        concentrations: Dict[str, float] = {}
        for pos in self.positions.values():
            concentrations[pos.sector] = (
                concentrations.get(pos.sector, 0.0) + pos.market_value / equity
            )
        return concentrations


@dataclass
class TradeCandidate:
    """A proposed trade awaiting evaluation."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    direction: TradeDirection = TradeDirection.LONG
    proposed_quantity: float = 0.0
    proposed_price: float = 0.0
    strategy: StrategyFamily = StrategyFamily.TREND
    signal_strength: float = 0.0          # 0..1
    expected_holding_days: int = 1
    catalyst_event_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeRecord:
    """A completed (or paper) trade with outcome data."""
    trade_id: str
    symbol: str
    direction: TradeDirection
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    strategy: StrategyFamily
    pnl: float = 0.0
    pnl_pct: float = 0.0
    transaction_costs: float = 0.0
    slippage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InformationEvent:
    """A market-moving information event subject to decay."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Optional[str] = None
    event_type: str = ""            # e.g. "earnings", "guidance", "news", "macro"
    headline: str = ""
    publication_time: datetime = field(default_factory=datetime.utcnow)
    confirmation_time: Optional[datetime] = None
    relevance_score: float = 1.0    # starts at 1.0, decays over time
    contradicted_by: List[str] = field(default_factory=list)   # event_ids
    is_materially_important: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CatalystEvent:
    """A scheduled or unscheduled catalyst (earnings, FOMC, guidance, etc.)."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Optional[str] = None
    event_type: str = ""
    scheduled_time: datetime = field(default_factory=datetime.utcnow)
    actual_time: Optional[datetime] = None
    market_expectation: Optional[float] = None
    analyst_consensus: Optional[float] = None
    previous_guidance: Optional[float] = None
    actual_result: Optional[float] = None
    expectation_result: Optional[ExpectationResult] = None
    market_reaction_pct: Optional[float] = None
    reaction_speed_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationResult:
    """Output of the Capital Allocation Engine."""
    trade_id: str
    decision: AllocationDecision
    approved_quantity: float
    approved_notional: float
    rejection_reasons: List[str] = field(default_factory=list)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EmergencyEvent:
    """Recorded emergency trigger."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger: EmergencyTrigger = EmergencyTrigger.MODEL_FAILURE
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
