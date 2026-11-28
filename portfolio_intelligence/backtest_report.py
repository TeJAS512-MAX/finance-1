"""
portfolio_intelligence/backtest_report.py — Item 57: Research Integrity / Backtest Report
===========================================================================================

Every backtest must generate a research report with ALL fields specified in Item 57.

The report explicitly states:
  "BACKTEST RESULTS DO NOT GUARANTEE FUTURE PERFORMANCE."

Report sections:
  1. Data period and sources
  2. Features used
  3. Model version and parameters
  4. Transaction cost and slippage assumptions
  5. Training / validation / test period split
  6. Out-of-sample results
  7. Performance metrics
  8. Drawdown analysis
  9. Limitations
  10. Anti-overfitting checks

Also implements Data-Leakage Detection (Item 58 sub-item).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DISCLAIMER = (
    "\n" + "=" * 70 + "\n"
    "⚠️  IMPORTANT DISCLAIMER\n"
    "=" * 70 + "\n"
    "BACKTEST RESULTS DO NOT GUARANTEE FUTURE PERFORMANCE.\n"
    "Past performance of any strategy is not indicative of future results.\n"
    "This backtest was conducted on HISTORICAL data only.\n"
    "Real-world trading involves risks not fully captured in backtesting,\n"
    "including: market impact, liquidity constraints, execution delays,\n"
    "regime changes, and model degradation.\n"
    "=" * 70 + "\n"
)


# ---------------------------------------------------------------------------
# Data leakage detection
# ---------------------------------------------------------------------------

class DataLeakageDetector:
    """
    Detects potential look-ahead bias / data leakage in backtest features.

    Key rules:
      - Feature timestamp must be ≤ bar timestamp
      - News published at T must not appear in bars before T
      - Training data must not overlap with test data
    """

    @staticmethod
    def check_feature_timestamps(
        features: List[Dict[str, Any]],
        bar_timestamp: datetime,
        feature_name: str = "unknown",
    ) -> List[str]:
        """
        Verify that all feature values were available at bar_timestamp.

        Returns a list of leakage warnings (empty = no leakage detected).
        """
        warnings = []
        for feat in features:
            feat_time = feat.get("timestamp")
            if feat_time is None:
                warnings.append(
                    f"MISSING_TIMESTAMP: Feature '{feature_name}' has no timestamp. "
                    "Cannot verify absence of look-ahead bias."
                )
                continue
            if isinstance(feat_time, str):
                feat_time = datetime.fromisoformat(feat_time)
            if feat_time > bar_timestamp:
                warnings.append(
                    f"LOOK_AHEAD_BIAS DETECTED: Feature '{feature_name}' "
                    f"has timestamp {feat_time.isoformat()} which is AFTER "
                    f"bar timestamp {bar_timestamp.isoformat()}. "
                    "This constitutes data leakage and must be fixed."
                )
        return warnings

    @staticmethod
    def check_train_test_overlap(
        train_end: datetime,
        test_start: datetime,
    ) -> List[str]:
        """Verify train and test periods do not overlap."""
        warnings = []
        if test_start <= train_end:
            warnings.append(
                f"TRAIN_TEST_OVERLAP: Test period starts ({test_start.isoformat()}) "
                f"before training ends ({train_end.isoformat()}). "
                "This constitutes data leakage."
            )
        return warnings

    @staticmethod
    def check_survivorship_bias(
        symbols_used: List[str],
        symbols_available_at_start: List[str],
    ) -> List[str]:
        """Warn if only currently-active symbols were used (survivorship bias)."""
        warnings = []
        if symbols_used and symbols_available_at_start:
            # If using subset without delisted stocks, flag it
            warnings.append(
                "SURVIVORSHIP_BIAS_RISK: Verify that delisted or bankrupt companies "
                "from the test period are included in the universe. "
                "Using only currently-active symbols introduces survivorship bias."
            )
        return warnings


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------

@dataclass
class BacktestReport:
    """
    Complete research report for a backtest run.
    All fields from spec Item 57 are present.
    """

    # Identification
    report_id: str
    strategy_name: str
    model_version: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = "Market Intelligence AI Research Platform"

    # Data
    data_start: Optional[datetime] = None
    data_end: Optional[datetime] = None
    data_sources: List[str] = field(default_factory=list)
    features_used: List[str] = field(default_factory=list)
    universe_size: int = 0
    universe_description: str = ""

    # Model
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Cost assumptions
    transaction_cost_pct: float = 0.03   # Round-trip commission
    slippage_pct: float = 0.05           # Slippage per trade
    latency_assumption_ms: float = 500.0  # Assumed execution latency

    # Data splits
    train_start: Optional[datetime] = None
    train_end: Optional[datetime] = None
    validation_start: Optional[datetime] = None
    validation_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None

    # In-sample results
    is_total_return_pct: Optional[float] = None
    is_sharpe_ratio: Optional[float] = None
    is_max_drawdown_pct: Optional[float] = None
    is_total_trades: Optional[int] = None
    is_win_rate_pct: Optional[float] = None

    # Out-of-sample results
    oos_total_return_pct: Optional[float] = None
    oos_cagr_pct: Optional[float] = None
    oos_volatility_pct: Optional[float] = None
    oos_sharpe_ratio: Optional[float] = None
    oos_sortino_ratio: Optional[float] = None
    oos_max_drawdown_pct: Optional[float] = None
    oos_calmar_ratio: Optional[float] = None
    oos_profit_factor: Optional[float] = None
    oos_win_rate_pct: Optional[float] = None
    oos_expectancy: Optional[float] = None
    oos_total_trades: Optional[int] = None
    oos_avg_win_pct: Optional[float] = None
    oos_avg_loss_pct: Optional[float] = None
    oos_turnover_pct: Optional[float] = None
    oos_transaction_costs_total: Optional[float] = None

    # Anti-overfitting
    walk_forward_results: List[Dict[str, Any]] = field(default_factory=list)
    monte_carlo_5th_percentile_return: Optional[float] = None
    monte_carlo_95th_percentile_return: Optional[float] = None
    parameter_stability_score: Optional[float] = None

    # Data quality / leakage
    leakage_warnings: List[str] = field(default_factory=list)
    survivorship_bias_check: str = "NOT_PERFORMED"

    # Limitations
    limitations: List[str] = field(default_factory=list)
    known_risks: List[str] = field(default_factory=list)

    # MLflow
    mlflow_run_id: Optional[str] = None

    def to_text(self) -> str:
        """Generate the full human-readable research report."""
        lines = [
            DISCLAIMER,
            f"BACKTEST RESEARCH REPORT",
            f"{'=' * 70}",
            f"Strategy:      {self.strategy_name}",
            f"Report ID:     {self.report_id}",
            f"Model Version: {self.model_version}",
            f"Generated:     {self.generated_at.isoformat()}",
            f"Generated by:  {self.generated_by}",
            "",
            f"{'─' * 70}",
            f"1. DATA PERIOD & SOURCES",
            f"{'─' * 70}",
            f"  Data period:  {_fmt(self.data_start)} → {_fmt(self.data_end)}",
            f"  Sources:      {', '.join(self.data_sources) or 'Not specified'}",
            f"  Universe:     {self.universe_size} instruments — {self.universe_description}",
            f"  Features:     {', '.join(self.features_used) or 'Not listed'}",
            "",
            f"{'─' * 70}",
            f"2. MODEL & PARAMETERS",
            f"{'─' * 70}",
            f"  Version:      {self.model_version}",
            f"  Parameters:",
        ]
        for k, v in self.parameters.items():
            lines.append(f"    {k}: {v}")

        lines += [
            "",
            f"{'─' * 70}",
            f"3. TRANSACTION COST & SLIPPAGE ASSUMPTIONS",
            f"{'─' * 70}",
            f"  Commission (round-trip): {self.transaction_cost_pct:.3f}%",
            f"  Slippage:                {self.slippage_pct:.3f}%",
            f"  Latency assumption:      {self.latency_assumption_ms:.0f}ms",
            "",
            f"{'─' * 70}",
            f"4. DATA SPLITS",
            f"{'─' * 70}",
            f"  Training:    {_fmt(self.train_start)} → {_fmt(self.train_end)}",
            f"  Validation:  {_fmt(self.validation_start)} → {_fmt(self.validation_end)}",
            f"  Test (OOS):  {_fmt(self.test_start)} → {_fmt(self.test_end)}",
            "",
            f"{'─' * 70}",
            f"5. IN-SAMPLE RESULTS",
            f"{'─' * 70}",
            f"  Total Return:   {_pct(self.is_total_return_pct)}",
            f"  Sharpe Ratio:   {_val(self.is_sharpe_ratio)}",
            f"  Max Drawdown:   {_pct(self.is_max_drawdown_pct)}",
            f"  Total Trades:   {self.is_total_trades or 'N/A'}",
            f"  Win Rate:       {_pct(self.is_win_rate_pct)}",
            "",
            f"{'─' * 70}",
            f"6. OUT-OF-SAMPLE RESULTS",
            f"{'─' * 70}",
            f"  Total Return:   {_pct(self.oos_total_return_pct)}",
            f"  CAGR:           {_pct(self.oos_cagr_pct)}",
            f"  Volatility:     {_pct(self.oos_volatility_pct)}",
            f"  Sharpe Ratio:   {_val(self.oos_sharpe_ratio)}",
            f"  Sortino Ratio:  {_val(self.oos_sortino_ratio)}",
            f"  Max Drawdown:   {_pct(self.oos_max_drawdown_pct)}",
            f"  Calmar Ratio:   {_val(self.oos_calmar_ratio)}",
            f"  Profit Factor:  {_val(self.oos_profit_factor)}",
            f"  Win Rate:       {_pct(self.oos_win_rate_pct)}",
            f"  Expectancy:     {_val(self.oos_expectancy)}",
            f"  Total Trades:   {self.oos_total_trades or 'N/A'}",
            f"  Avg Win:        {_pct(self.oos_avg_win_pct)}",
            f"  Avg Loss:       {_pct(self.oos_avg_loss_pct)}",
            f"  Total Costs:    ₹{self.oos_transaction_costs_total or 0:,.0f}",
            "",
            f"{'─' * 70}",
            f"7. ANTI-OVERFITTING CHECKS",
            f"{'─' * 70}",
            f"  Walk-forward folds:  {len(self.walk_forward_results)}",
            f"  Monte Carlo 5th %ile: {_pct(self.monte_carlo_5th_percentile_return)}",
            f"  Monte Carlo 95th %ile: {_pct(self.monte_carlo_95th_percentile_return)}",
            f"  Parameter stability: {_val(self.parameter_stability_score)}",
            "",
            f"{'─' * 70}",
            f"8. DATA QUALITY & LEAKAGE",
            f"{'─' * 70}",
            f"  Survivorship bias check: {self.survivorship_bias_check}",
        ]
        if self.leakage_warnings:
            lines.append("  ⚠️  LEAKAGE WARNINGS:")
            for w in self.leakage_warnings:
                lines.append(f"     - {w}")
        else:
            lines.append("  No leakage warnings detected.")

        lines += [
            "",
            f"{'─' * 70}",
            f"9. LIMITATIONS",
            f"{'─' * 70}",
        ]
        default_limitations = [
            "Results based on historical data only and may not reflect future conditions.",
            "Market impact and liquidity constraints may differ in live trading.",
            "Model assumes stable data quality — outages and stale data are not simulated.",
            "Transaction costs are estimates; actual costs may vary.",
        ]
        all_lims = self.limitations or default_limitations
        for lim in all_lims:
            lines.append(f"  - {lim}")

        lines += [
            "",
            DISCLAIMER,
            f"MLflow Run ID: {self.mlflow_run_id or 'N/A'}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        import dataclasses
        d = dataclasses.asdict(self)
        d["disclaimer"] = DISCLAIMER.strip()
        # Convert datetimes to ISO strings
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d") if dt else "N/A"

def _pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if v is not None else "N/A"

def _val(v: Optional[float]) -> str:
    return f"{v:.4f}" if v is not None else "N/A"
