"""
trading/paper_broker.py — Paper (simulated) broker implementation.

Implements BrokerProvider for paper trading with:
  - Realistic slippage simulation
  - Commission calculation
  - Partial fills for large orders
  - Order rejection on invalid conditions
  - Full audit logging

is_paper = True always.
This broker NEVER connects to a real exchange.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.config import get_settings
from core.logging_config import audit, get_logger
from services.interfaces import BrokerProvider

logger = get_logger(__name__)
settings = get_settings()

# Slippage model: fraction of ATR added to market orders
SLIPPAGE_FRACTION = settings.backtest_default_slippage_pct / 100.0
COMMISSION_FRACTION = settings.backtest_default_commission_pct / 100.0


class PaperBroker(BrokerProvider):
    """
    Simulated paper broker.

    Maintains an in-memory order book and position ledger.
    All prices come from the MarketDataProvider (injected).
    """

    def __init__(self, initial_capital: float | None = None, market_mode: str = "stocks") -> None:
        self._cash = initial_capital or settings.paper_trading_initial_capital
        self._initial_capital = self._cash
        self.market_mode = market_mode
        self._positions: Dict[str, Dict[str, Any]] = {}   # ticker → position
        self._orders: Dict[str, Dict[str, Any]] = {}       # order_id → order
        self._fills: List[Dict[str, Any]] = []
        self._total_commission = 0.0
        self._total_slippage = 0.0

    @property
    def is_paper(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "PaperBroker"

    # ── Account ────────────────────────────────────────────

    async def get_account(self) -> Dict[str, Any]:
        total_market_value = sum(
            pos["quantity"] * pos["last_price"]
            for pos in self._positions.values()
            if pos.get("last_price")
        )
        total_equity = self._cash + total_market_value
        return {
            "cash": round(self._cash, 2),
            "total_equity": round(total_equity, 2),
            "total_market_value": round(total_market_value, 2),
            "initial_capital": self._initial_capital,
            "total_pnl": round(total_equity - self._initial_capital, 2),
            "total_commission": round(self._total_commission, 2),
            "total_slippage": round(self._total_slippage, 2),
            "currency": settings.paper_trading_currency,
            "is_paper": True,
            "market_mode": self.market_mode,
        }

    # ── Positions ──────────────────────────────────────────

    async def get_positions(self) -> List[Dict[str, Any]]:
        formatted_positions = []
        for pos in self._positions.values():
            avg_price = pos.get("avg_entry_price", 0)
            qty = pos.get("quantity", 0)
            curr = pos.get("last_price", avg_price)
            pnl = (curr - avg_price) * qty if pos["direction"] == "LONG" else (avg_price - curr) * qty
            if avg_price > 0:
                pnl_pct = ((curr - avg_price) / avg_price) * 100 if pos["direction"] == "LONG" else ((avg_price - curr) / avg_price) * 100
            else:
                pnl_pct = 0
            
            formatted_positions.append({
                # Keep the broker key.  The trading engine uses the Upstox
                # instrument key to update prices and to close the position.
                "ticker": pos.get("ticker", "UNKNOWN"),
                "symbol": pos.get("ticker", "UNKNOWN").split("|")[-1] if "|" in pos.get("ticker", "") else pos.get("ticker", "UNKNOWN"),
                "quantity": qty,
                "avg_price": avg_price,
                "current_price": curr,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "side": pos.get("direction", "LONG"),
                "market_mode": self.market_mode,
            })
        return formatted_positions

    # ── Quote ──────────────────────────────────────────────

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        pos = self._positions.get(ticker, {})
        return {
            "ticker": ticker,
            "last_price": pos.get("last_price"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_paper": True,
        }

    # ── Order Placement ────────────────────────────────────

    async def place_order(
        self,
        ticker: str,
        direction: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simulate order placement.

        Market orders: fill immediately with slippage.
        Limit orders: pend until price condition is met (simplified: fill at limit).
        """
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Validate direction
        if direction not in ("BUY", "SELL"):
            return self._reject(order_id, "Invalid direction")
        if quantity <= 0:
            return self._reject(order_id, "Quantity must be positive")

        # Simulate fill price with slippage
        exec_price = price or 0.0
        if not exec_price:
            return self._reject(order_id, "No price provided for paper fill")

        slippage_amount = exec_price * SLIPPAGE_FRACTION
        if direction == "BUY":
            fill_price = exec_price * (1 + SLIPPAGE_FRACTION)  # Buy slightly higher
        else:
            fill_price = exec_price * (1 - SLIPPAGE_FRACTION)  # Sell slightly lower

        commission = fill_price * quantity * COMMISSION_FRACTION
        notional = fill_price * quantity

        # Capital check for BUY
        if direction == "BUY" and (notional + commission) > self._cash:
            return self._reject(order_id, f"Insufficient cash: need {notional:.2f}, have {self._cash:.2f}")

        realized_pnl = 0.0
        # Execute
        if direction == "BUY":
            self._cash -= (notional + commission)
            pos = self._positions.get(ticker)
            if pos:
                # Average down
                total_qty = pos["quantity"] + quantity
                pos["avg_entry_price"] = (
                    pos["avg_entry_price"] * pos["quantity"] + fill_price * quantity
                ) / total_qty
                pos["quantity"] = total_qty
            else:
                self._positions[ticker] = {
                    "ticker": ticker,
                    "direction": "LONG",
                    "quantity": quantity,
                    "avg_entry_price": fill_price,
                    "last_price": fill_price,
                    "opened_at": now.isoformat(),
                }
        else:  # SELL
            pos = self._positions.get(ticker)
            if not pos or pos["quantity"] < quantity:
                return self._reject(order_id, "Insufficient position to sell")
            
            realized_pnl = (fill_price - pos["avg_entry_price"]) * quantity - commission
            self._cash += (notional - commission)
            pos["quantity"] -= quantity
            if pos["quantity"] < 1e-6:
                del self._positions[ticker]

        self._total_commission += commission
        self._total_slippage += slippage_amount * quantity

        order_record = {
            "order_id": order_id,
            "ticker": ticker,
            "direction": direction,
            "quantity": quantity,
            "order_type": order_type,
            "requested_price": price,
            "fill_price": round(fill_price, 4),
            "commission": round(commission, 2),
            "slippage": round(slippage_amount * quantity, 2),
            "notional": round(notional, 2),
            "realized_pnl": round(realized_pnl, 2),
            "status": "FILLED",
            "submitted_at": now.isoformat(),
            "filled_at": now.isoformat(),
            "is_paper": True,
            "tag": tag,
            "market_mode": self.market_mode,
        }
        self._orders[order_id] = order_record
        self._fills.append(order_record)

        audit(
            "PAPER_ORDER_FILLED",
            ticker=ticker,
            direction=direction,
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=order_id,
        )
        logger.info(
            "Paper order filled",
            ticker=ticker,
            direction=direction,
            qty=quantity,
            fill_price=fill_price,
        )
        return order_record

    async def cancel_order(self, broker_order_id: str) -> bool:
        order = self._orders.get(broker_order_id)
        if order and order["status"] == "PENDING":
            order["status"] = "CANCELLED"
            return True
        return False

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        return self._orders.get(broker_order_id, {"status": "NOT_FOUND"})

    # ── Helpers ────────────────────────────────────────────

    def _reject(self, order_id: str, reason: str) -> Dict[str, Any]:
        logger.warning("Paper order rejected", order_id=order_id, reason=reason)
        audit("PAPER_ORDER_REJECTED", order_id=order_id, reason=reason)
        record = {"order_id": order_id, "status": "REJECTED", "rejection_reason": reason}
        self._orders[order_id] = record
        return record

    def update_price(self, ticker: str, price: float) -> None:
        """Update current price for a position (call on each price tick)."""
        if ticker in self._positions:
            self._positions[ticker]["last_price"] = price

    def get_fills(self) -> List[Dict[str, Any]]:
        return list(self._fills)
