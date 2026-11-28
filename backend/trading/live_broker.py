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

try:
    import upstox_client
except ImportError:
    upstox_client = None
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
        self.configuration = upstox_client.Configuration() if upstox_client is not None else None
        self.portfolio_api = None
        self.user_api = None
        self.order_api = None
        if upstox_client is None:
            logger.error("upstox_client SDK not installed. LiveBroker execution disabled.")
        elif upstox_access:
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
        if not self.user_api:
            return {
                "cash": 0.0,
                "total_equity": 0.0,
                "currency": "INR",
                "is_paper": False,
                "status": "ERROR: MISSING_UPSTOX_ACCESS_TOKEN",
            }
        try:
            funds_response = await asyncio.to_thread(
                self.user_api.get_user_fund_margin, api_version='2.0'
            )
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
        if not self.portfolio_api:
            return []
        try:
            api_response = await asyncio.to_thread(
                self.portfolio_api.get_positions, api_version='2.0'
            )
            positions = []
            if api_response.data:
                for pos in api_response.data:
                    avg_p = pos.average_price or 0.0
                    qty = pos.quantity or 0
                    denom = abs(avg_p * qty)
                    positions.append({
                        "ticker": pos.instrument_token if hasattr(pos, 'instrument_token') else pos.tradingsymbol,
                        "symbol": pos.tradingsymbol,
                        "quantity": qty,
                        "avg_price": avg_p,
                        "current_price": pos.last_price,
                        "pnl": pos.pnl,
                        "pnl_pct": (pos.pnl / denom) * 100 if denom > 0 else 0.0,
                        "side": "LONG" if qty > 0 else ("SHORT" if qty < 0 else "FLAT")
                    })
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch Upstox positions: {e}")
            return []

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Fetch live tick data via Kite Connect or Upstox official quote API."""
        if self.kite:
            try:
                symbol_clean = ticker.split("|")[-1] if "|" in ticker else ticker
                instrument = f"NSE:{symbol_clean}" if not symbol_clean.startswith("NSE:") else symbol_clean
                quote_data = await asyncio.to_thread(self.kite.quote, instrument)
                data = quote_data.get(instrument, {})
                last_price = float(data.get("last_price", 0.0) or 0.0)
                if last_price > 0:
                    return {
                        "ticker": ticker,
                        "last_price": last_price,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "is_paper": False,
                    }
            except Exception as e:
                logger.error(f"Failed to fetch live quote from Zerodha for {ticker}: {e}")

        try:
            from services.providers.upstox_market_data import INSTRUMENT_KEYS, get_live_quote

            symbol = next(
                (sym for sym, key in INSTRUMENT_KEYS.items() if key == ticker or sym == ticker),
                ticker.split("|")[-1],
            )
            upstox_quote = await get_live_quote(symbol)
            ltp = float(upstox_quote.get("ltp", 0.0) or 0.0)
            return {
                "ticker": ticker,
                "last_price": ltp,
                "timestamp": upstox_quote.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "is_paper": False,
            }
        except Exception as e:
            logger.error(f"Failed to fetch live quote from Upstox for {ticker}: {e}")
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
        Places a real order on the exchange using Upstox after fail-closed safety checks.
        """
        live_settings = get_settings()
        if not live_settings.live_trading_enabled:
            logger.error("LIVE_TRADING_ENABLED=false. Real order blocked by LiveBroker gate.")
            return {"status": "REJECTED", "reason": "LIVE_TRADING_DISABLED", "is_paper": False}
        if live_settings.emergency_kill_switch_active or settings.emergency_kill_switch_active:
            logger.error("KILL SWITCH ACTIVE. Order blocked.")
            return {"status": "REJECTED", "reason": "KILL_SWITCH", "is_paper": False}
        if not self.order_api:
            logger.error("Upstox OrderApi not initialized (missing access token).")
            return {"status": "REJECTED", "reason": "BROKER_NOT_INITIALIZED", "is_paper": False}

        transaction_type = 'BUY' if direction == "BUY" else 'SELL'
        order_type_upstox = 'MARKET' if order_type == "MARKET" else 'LIMIT'

        audit("LIVE_ORDER_INITIATED", ticker=ticker, direction=direction, quantity=quantity)
        
        try:
            body = upstox_client.PlaceOrderRequest(
                quantity=int(quantity),
                product='I', # Intraday
                validity='DAY',
                price=price if price and order_type_upstox == 'LIMIT' else 0.0,
                instrument_token=ticker,
                order_type=order_type_upstox,
                transaction_type=transaction_type,
                disclosed_quantity=0,
                trigger_price=stop_price or 0,
                is_amo=False
            )
            api_response = await asyncio.to_thread(
                self.order_api.place_order, body, api_version='2.0'
            )
            
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
        if not self.order_api or not get_settings().live_trading_enabled:
            return False
        try:
            await asyncio.to_thread(
                self.order_api.cancel_order, order_id=broker_order_id, api_version='2.0'
            )
            audit("LIVE_ORDER_CANCELLED", order_id=broker_order_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel Upstox order {broker_order_id}: {e}")
            return False

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        if not self.order_api:
            return {"order_id": broker_order_id, "status": "UNAVAILABLE"}
        try:
            resp = await asyncio.to_thread(
                self.order_api.get_order_details, order_id=broker_order_id, api_version='2.0'
            )
            data = resp.data
            return {
                "order_id": broker_order_id,
                "status": getattr(data, "status", "UNKNOWN"),
                "filled_quantity": getattr(data, "filled_quantity", 0),
                "average_price": getattr(data, "average_price", 0.0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch order status for {broker_order_id}: {e}")
            return {"order_id": broker_order_id, "status": "ERROR", "reason": str(e)}

    async def get_orders(self) -> List[Dict[str, Any]]:
        if not self.order_api:
            return []
        try:
            resp = await asyncio.to_thread(self.order_api.get_order_book, api_version='2.0')
            orders = []
            for o in getattr(resp, "data", []) or []:
                orders.append({
                    "id": getattr(o, "order_id", ""),
                    "symbol": getattr(o, "tradingsymbol", ""),
                    "side": getattr(o, "transaction_type", ""),
                    "type": getattr(o, "order_type", ""),
                    "qty": getattr(o, "quantity", 0),
                    "price": getattr(o, "average_price", 0.0) or getattr(o, "price", 0.0),
                    "status": getattr(o, "status", "UNKNOWN"),
                    "time": getattr(o, "order_timestamp", "--"),
                })
            return orders
        except Exception as e:
            logger.error(f"Failed to fetch Upstox order book: {e}")
            return []
