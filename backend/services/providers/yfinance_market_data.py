"""
services/providers/yfinance_market_data.py — YFinance Market Data Provider.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from backend.services.interfaces import MarketDataProvider


class YFinanceMarketDataProvider(MarketDataProvider):
    """
    Implementation of MarketDataProvider using yfinance.
    Note: yfinance makes synchronous network calls, so we run them in threads.
    """

    def _format_ticker(self, ticker: str, exchange: str) -> str:
        """Format ticker for yfinance based on exchange."""
        exchange = exchange.upper()
        if exchange == "NSE":
            return f"{ticker}.NS"
        elif exchange == "BSE":
            return f"{ticker}.BO"
        return ticker

    async def get_quote(self, ticker: str, exchange: str) -> Dict[str, Any]:
        yf_ticker = self._format_ticker(ticker, exchange)
        
        def _fetch_quote() -> Dict[str, Any]:
            stock = yf.Ticker(yf_ticker)
            info = stock.fast_info
            # fast_info doesn't have everything, try fast_info first for speed
            return {
                "symbol": ticker,
                "exchange": exchange,
                "price": info.last_price,
                "volume": info.last_volume,
                "market_cap": info.market_cap,
                "currency": info.currency,
                "previous_close": info.previous_close,
                "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            }

        return await asyncio.to_thread(_fetch_quote)

    async def get_ohlcv(
        self,
        ticker: str,
        exchange: str,
        start: date,
        end: date,
        timeframe: str = "1D",
    ) -> pd.DataFrame:
        yf_ticker = self._format_ticker(ticker, exchange)
        
        # Mapping timeframe
        interval_map = {
            "1D": "1d",
            "1W": "1wk",
            "1M": "1mo",
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
        }
        interval = interval_map.get(timeframe, "1d")

        def _fetch_data() -> pd.DataFrame:
            df = yf.download(
                tickers=yf_ticker,
                start=start.isoformat(),
                end=end.isoformat(),
                interval=interval,
                progress=False,
            )
            if df.empty:
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adjusted_close"])
            
            # yfinance creates MultiIndex columns if multiple tickers, but we pass one
            df = df.reset_index()
            
            # rename columns to lowercase
            df.columns = [str(c).lower() for c in df.columns]
            
            # map specific columns
            rename_map = {
                "date": "date",
                "datetime": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "adj close": "adjusted_close",
            }
            df = df.rename(columns=rename_map)
            
            # Ensure date is timezone aware (UTC)
            if "date" in df.columns:
                if df["date"].dt.tz is None:
                    df["date"] = df["date"].dt.tz_localize("UTC")
                else:
                    df["date"] = df["date"].dt.tz_convert("UTC")
            
            return df

        return await asyncio.to_thread(_fetch_data)

    async def get_corporate_actions(
        self,
        ticker: str,
        exchange: str,
        start: date,
        end: date,
    ) -> List[Dict[str, Any]]:
        yf_ticker = self._format_ticker(ticker, exchange)

        def _fetch_actions() -> List[Dict[str, Any]]:
            stock = yf.Ticker(yf_ticker)
            actions = stock.actions
            if actions.empty:
                return []
            
            actions = actions.loc[start.isoformat():end.isoformat()]
            
            result = []
            for d, row in actions.iterrows():
                result.append({
                    "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
                    "dividends": float(row.get("Dividends", 0.0)),
                    "stock_splits": float(row.get("Stock Splits", 0.0)),
                })
            return result

        return await asyncio.to_thread(_fetch_actions)

    async def search_symbols(self, query: str, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """yfinance doesn't have a great search API natively. Returning a dummy or limited wrapper."""
        return [
            {"symbol": query.upper(), "name": f"Searched: {query.upper()}", "exchange": exchange or "UNKNOWN"}
        ]

    @property
    def provider_name(self) -> str:
        return "yfinance"

    @property
    def supported_exchanges(self) -> List[str]:
        return ["NSE", "BSE", "NYSE", "NASDAQ"]
