"""
portfolio_intelligence/counterfactual.py — Item 53: Counterfactual Trade Analysis
==================================================================================

For every completed trade, this engine calculates:

  1. ACTUAL outcome  — what actually happened
  2. COUNTERFACTUAL — what would have happened if the system had NOT traded
     (i.e., the "do-nothing" alternative)
  3. EVIDENCE ANALYSIS — what evidence would have changed the decision

Both results are stored for model evaluation and retraining.

Usage
-----
engine = CounterfactualEngine()
result = engine.analyse(trade, price_series)
engine.store(result)

Design notes
-------------
- Counterfactual is computed against a benchmark (typically buy-and-hold or cash).
- The engine does NOT use any information that was not available at trade entry time.
- Results feed back into the model evaluation engine (Item 12).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import TradeDirection, TradeRecord


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualResult:
    trade_id: str
    symbol: str
    direction: TradeDirection

    # Actual outcome
    actual_entry_price: float
    actual_exit_price: float
    actual_pnl_pct: float
    actual_holding_days: int
    actual_transaction_costs_pct: float
    actual_net_pnl_pct: float          # after costs

    # Counterfactual: "what if no trade?"
    cf_price_at_entry: float           # same as actual (no trade taken)
    cf_price_at_exit: float            # price of symbol at same exit time
    cf_pnl_pct: float                  # what the symbol did while position was held
    cf_cash_return_pct: float          # risk-free / cash return for same period
    cf_no_trade_outcome_pct: float     # cash return (opportunity cost of holding cash)

    # Comparison
    alpha_vs_no_trade_pct: float       # actual_net - cf_no_trade
    alpha_vs_underlying_pct: float     # actual_net - cf_pnl (vs just holding the stock)
    trade_added_value: bool            # True if actual > counterfactual

    # Evidence analysis
    original_evidence: List[str]
    evidence_that_would_change_decision: List[str]
    signals_that_failed: List[str]
    signals_that_worked: List[str]

    # Analysis text (AI-generated, clearly labeled)
    ai_analysis: Optional[str] = None
    ai_lesson: Optional[str] = None

    analysed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CounterfactualEngine:
    """
    Analyses completed trades against their counterfactual alternative.

    The counterfactual always respects the information set available at
    trade entry — no future information is used in the analysis of the
    DECISION (though future prices are used to compute outcomes).
    """

    ANNUAL_RISK_FREE_RATE = 0.065   # Approx India G-sec rate

    def __init__(self) -> None:
        self._results: List[CounterfactualResult] = []

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyse(
        self,
        trade: TradeRecord,
        price_at_exit: float,
        original_evidence: Optional[List[str]] = None,
        evidence_that_would_change: Optional[List[str]] = None,
        signals_that_failed: Optional[List[str]] = None,
        signals_that_worked: Optional[List[str]] = None,
    ) -> CounterfactualResult:
        """
        Compute counterfactual analysis for a completed trade.

        Parameters
        ----------
        trade           : The completed TradeRecord.
        price_at_exit   : Price of the symbol at the time the trade was closed.
                          (Used to compute the counterfactual "held through" return.)
        original_evidence : Evidence strings that led to the trade.
        evidence_that_would_change : Evidence that, if known, would have changed the decision.
        """
        holding_days = (trade.exit_time - trade.entry_time).days

        # Actual outcome
        if trade.direction == TradeDirection.LONG:
            actual_pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
        else:  # SHORT
            actual_pnl_pct = (trade.entry_price - trade.exit_price) / trade.entry_price * 100

        costs_pct = (trade.transaction_costs + trade.slippage) / (trade.entry_price * trade.quantity) * 100
        actual_net_pnl_pct = actual_pnl_pct - costs_pct

        # Counterfactual: holding cash
        daily_risk_free = self.ANNUAL_RISK_FREE_RATE / 252
        cf_cash_return_pct = daily_risk_free * holding_days * 100

        # Counterfactual: underlying stock return (what the stock did)
        cf_pnl_pct = (price_at_exit - trade.entry_price) / trade.entry_price * 100

        # Alpha calculations
        alpha_vs_no_trade = actual_net_pnl_pct - cf_cash_return_pct
        alpha_vs_underlying = actual_net_pnl_pct - cf_pnl_pct
        trade_added_value = alpha_vs_no_trade > 0

        result = CounterfactualResult(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            direction=trade.direction,
            actual_entry_price=trade.entry_price,
            actual_exit_price=trade.exit_price,
            actual_pnl_pct=actual_pnl_pct,
            actual_holding_days=holding_days,
            actual_transaction_costs_pct=costs_pct,
            actual_net_pnl_pct=actual_net_pnl_pct,
            cf_price_at_entry=trade.entry_price,
            cf_price_at_exit=price_at_exit,
            cf_pnl_pct=cf_pnl_pct,
            cf_cash_return_pct=cf_cash_return_pct,
            cf_no_trade_outcome_pct=cf_cash_return_pct,
            alpha_vs_no_trade_pct=alpha_vs_no_trade,
            alpha_vs_underlying_pct=alpha_vs_underlying,
            trade_added_value=trade_added_value,
            original_evidence=original_evidence or [],
            evidence_that_would_change_decision=evidence_that_would_change or [],
            signals_that_failed=signals_that_failed or [],
            signals_that_worked=signals_that_worked or [],
        )

        self._results.append(result)
        return result

    # ------------------------------------------------------------------
    # Aggregated analysis
    # ------------------------------------------------------------------

    def model_performance_summary(self) -> Dict[str, Any]:
        """Return aggregated statistics across all counterfactual analyses."""
        if not self._results:
            return {"error": "No counterfactual results available yet."}

        total = len(self._results)
        value_added = sum(1 for r in self._results if r.trade_added_value)
        avg_alpha = sum(r.alpha_vs_no_trade_pct for r in self._results) / total
        avg_actual_net = sum(r.actual_net_pnl_pct for r in self._results) / total

        # Collect commonly failed signals
        failed_signal_counts: Dict[str, int] = {}
        for r in self._results:
            for sig in r.signals_that_failed:
                failed_signal_counts[sig] = failed_signal_counts.get(sig, 0) + 1

        top_failed = sorted(failed_signal_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_trades_analysed": total,
            "trades_that_added_value": value_added,
            "value_add_rate_pct": value_added / total * 100,
            "avg_alpha_vs_no_trade_pct": round(avg_alpha, 3),
            "avg_actual_net_pnl_pct": round(avg_actual_net, 3),
            "top_failed_signals": top_failed,
            "disclaimer": (
                "Historical performance analysis only. "
                "Does not guarantee future results."
            ),
        }

    def get_results(self) -> List[CounterfactualResult]:
        return list(self._results)
