"""
trading/live_broker.py — Live Broker implementation for NSE.

Implements a Hybrid BrokerProvider:
- REAL LIVE TRADING (Execution & Portfolio) via Upstox Developer API.
- LIVE MARKET DATA (Quotes/Analysis) via Zerodha Kite Connect.
WARNING: THIS MODULE PLACES ACTUAL ORDERS ON THE STOCK EXCHANGE.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import os

import upstox_client
try:
    from kiteconnect import KiteConnect
except ImportError:
    KiteConnect = None

from core.config import get_settings
from core.logging_config import audit, get_logger
from services.interfaces import BrokerProvider

logger = get_logger(__name__)
settings = get_settings()

class LiveBroker(BrokerProvider):
    """
    Real broker integration for NSE.
    Executes live market and limit orders directly via Upstox.
    Uses Zerodha Kite Connect to fetch live pricing for analysis.
    """

    def __init__(self, api_key: str, api_secret: str, redirect_uri: str) -> None:
        # Upstox Initialization
        self.api_key = api_key
        upstox_access = os.getenv("UPSTOX_ACCESS_TOKEN")
        self.configuration = upstox_client.Configuration()
        if upstox_access:
            self.configuration.access_token = upstox_access
            self.portfolio_api = upstox_client.PortfolioApi(upstox_client.ApiClient(self.configuration))
            self.user_api = upstox_client.UserApi(upstox_client.ApiClient(self.configuration))
            self.order_api = upstox_client.OrderApi(upstox_client.ApiClient(self.configuration))
            logger.warning("LIVE BROKER INITIALIZED [UPSTOX EXECUTION]. TRADES WILL USE REAL CAPITAL.")
        else:
            logger.error("MISSING UPSTOX_ACCESS_TOKEN in .env. Execution will fail.")
            
        # Zerodha KiteConnect Initialization for Data
        kite_api = os.getenv("KITE_API_KEY")
        kite_access = os.getenv("KITE_ACCESS_TOKEN")
        if KiteConnect is None:
            logger.error("kiteconnect package is not installed.")
            self.kite = None
        elif not kite_api or not kite_access:
            logger.error("MISSING KITE_API_KEY or KITE_ACCESS_TOKEN in .env. Live Data will fail.")
            self.kite = None
        else:
            self.kite = KiteConnect(api_key=kite_api)
            self.kite.set_access_token(kite_access)
            logger.info("ZERODHA KITE CONNECT INITIALIZED [LIVE DATA].")

        self._is_paper = False

    @property
    def is_paper(self) -> bool:
        return self._is_paper

    @property
    def provider_name(self) -> str:
        return "Hybrid_UpstoxTrade_ZerodhaData"

    async def get_account(self) -> Dict[str, Any]:
        """Fetch live account margins and balances from Upstox."""
        try:
            funds_response = self.user_api.get_user_fund_margin(api_version='2.0')
            equity = funds_response.data.get('equity', {})
            return {
                "cash": equity.get('available_margin', 0.0),
                "total_equity": equity.get('net_margin', 0.0),
                "currency": "INR",
                "is_paper": False,
                "status": "UPSTOX_CONNECTED"
            }
        except Exception as e:
            logger.error(f"Failed to fetch Upstox account: {e}")
            return {
                "cash": 0.0,
                "total_equity": 0.0,
                "currency": "INR",
                "is_paper": False,
                "status": f"ERROR: {str(e)}"
            }

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch real open positions from Upstox."""
        try:
            api_response = self.portfolio_api.get_positions(api_version='2.0')
            positions = []
            if api_response.data:
                for pos in api_response.data:
                    positions.append({
                        "ticker": pos.instrument_token if hasattr(pos, 'instrument_token') else pos.tradingsymbol,
                        "symbol": pos.tradingsymbol,
                        "quantity": pos.quantity,
                        "avg_price": pos.average_price,
                        "current_price": pos.last_price,
                        "pnl": pos.pnl,
                        "pnl_pct": (pos.pnl / (pos.average_price * pos.quantity)) * 100 if pos.average_price and pos.quantity else 0,
                        "side": "LONG" if pos.quantity > 0 else ("SHORT" if pos.quantity < 0 else "FLAT")
                    })
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch Upstox positions: {e}")
            return []

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Fetch live tick data using Zerodha Kite Connect."""
        if not self.kite:
            logger.error("Cannot fetch live quote; Kite Connect not initialized.")
            return {
                "ticker": ticker,
                "last_price": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_paper": False,
            }
        
        try:
            # Kite Connect expects instruments prefixed with exchange, e.g. NSE:RELIANCE
            instrument = f"NSE:{ticker}" if not ticker.startswith("NSE:") else ticker
            quote_data = self.kite.quote(instrument)
            
            data = quote_data.get(instrument, {})
            last_price = data.get("last_price", 0.0)
            
            return {
                "ticker": ticker,
                "last_price": float(last_price),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_paper": False,
            }
        except Exception as e:
            logger.error(f"Failed to fetch live quote from Zerodha for {ticker}: {e}")
            return {
                "ticker": ticker,
                "last_price": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_paper": False,
            }

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
        DANGER: Places a real order on the exchange using Upstox.
        """
        if settings.emergency_kill_switch_active:
            logger.error("KILL SWITCH ACTIVE. Order blocked.")
            return {"status": "REJECTED", "reason": "KILL_SWITCH"}

        transaction_type = 'BUY' if direction == "BUY" else 'SELL'
        order_type_upstox = 'MARKET' if order_type == "MARKET" else 'LIMIT'

        audit("LIVE_ORDER_INITIATED", ticker=ticker, direction=direction, quantity=quantity)
        
        try:
            body = upstox_client.PlaceOrderRequest(
                quantity=int(quantity),
                product='I', # Intraday
                validity='DAY',
                price=price if price else 0.0,
                instrument_token=ticker, # Needs NSE_EQ|INE... token formatting
                order_type=order_type_upstox,
                transaction_type=transaction_type,
                disclosed_quantity=0,
                trigger_price=0,
                is_amo=False
            )
            api_response = self.order_api.place_order(body, api_version='2.0')
            
            order_id = api_response.data.order_id if api_response.data else str(uuid.uuid4())
            logger.warning(f"LIVE UPSTOX ORDER PLACED: {direction} {quantity} {ticker} -> ID: {order_id}")
            
            return {
                "order_id": order_id,
                "ticker": ticker,
                "status": "EXCHANGE_PENDING",
                "is_paper": False
            }
        except Exception as e:
            logger.error(f"Upstox live order failed: {str(e)}")
            return {"status": "FAILED", "reason": str(e)}

    async def cancel_order(self, broker_order_id: str) -> bool:
        return True

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        return {"status": "PENDING"}
