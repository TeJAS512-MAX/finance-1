"""
services/interfaces.py — Abstract provider interfaces.

Every external dependency (market data, news, LLM, broker, notifications)
is accessed through one of these interfaces. Concrete implementations live
in services/providers/ and are selected by configuration.

This ensures:
  - No hard-coding of a specific provider anywhere
  - Easy swapping of providers (e.g., yfinance → Polygon → NSE official)
  - Testability via mock implementations
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd


# ===========================================================
# A. Market Data Provider
# ===========================================================

class MarketDataProvider(ABC):
    """Abstract interface for market data (OHLCV, quotes, corporate actions)."""

    @abstractmethod
    async def get_quote(self, ticker: str, exchange: str) -> Dict[str, Any]:
        """Return latest quote for a ticker."""
        ...

    @abstractmethod
    async def get_ohlcv(
        self,
        ticker: str,
        exchange: str,
        start: date,
        end: date,
        timeframe: str = "1D",
    ) -> pd.DataFrame:
        """
        Return OHLCV data as a DataFrame with columns:
        [date, open, high, low, close, volume, adjusted_close]

        All timestamps must be timezone-aware.
        Data must not include any timestamps beyond `end`.
        """
        ...

    @abstractmethod
    async def get_corporate_actions(
        self,
        ticker: str,
        exchange: str,
        start: date,
        end: date,
    ) -> List[Dict[str, Any]]:
        """Return dividends, splits, bonuses in date range."""
        ...

    @abstractmethod
    async def search_symbols(self, query: str, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for symbols matching a query."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def supported_exchanges(self) -> List[str]: ...


# ===========================================================
# B. News / Information Provider
# ===========================================================

class NewsProvider(ABC):
    """Abstract interface for news and public information feeds."""

    @abstractmethod
    async def fetch_news(
        self,
        query: Optional[str] = None,
        company_name: Optional[str] = None,
        ticker: Optional[str] = None,
        from_date: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles matching the query.

        Each article dict must include:
        headline, content, published_at (timezone-aware), source_url,
        publisher, language.
        """
        ...

    @abstractmethod
    async def fetch_exchange_disclosures(
        self,
        ticker: Optional[str] = None,
        from_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch exchange/regulatory disclosures (BSE/NSE filings)."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ===========================================================
# C. LLM Provider
# ===========================================================

class LLMProvider(ABC):
    """
    Abstract interface for Large Language Model providers.

    Every method must return structured output (dict/Pydantic model),
    NOT raw text that could be misinterpreted.

    HALLUCINATION PROTECTION:
    - Models must not invent company data, prices, or news.
    - Every factual claim must reference the supplied source_texts.
    - If evidence is insufficient, return UNCERTAIN / NO_TRADE.
    """

    @abstractmethod
    async def analyse_sentiment(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyse sentiment.
        Returns: {sentiment: positive|negative|neutral|uncertain|contradictory,
                  score: float[-1,1], confidence: float[0,1], reasoning: str}
        """
        ...

    @abstractmethod
    async def generate_thesis(
        self,
        symbol: str,
        event_description: str,
        source_texts: List[str],
        financial_context: str,
        technical_context: str,
        market_regime: str,
    ) -> Dict[str, Any]:
        """
        Generate a trade thesis following spec Item 17 structure.

        source_texts: actual verified text snippets (not invented).
        Model MUST cite from source_texts only.
        """
        ...

    @abstractmethod
    async def generate_bull_bear_debate(
        self,
        symbol: str,
        source_texts: List[str],
        financial_context: str,
    ) -> Dict[str, Any]:
        """
        Run Bull/Bear/Judge debate (spec Item 16).
        Returns: {bull_case, bear_case, judge_verdict, supporting_evidence,
                  contradicting_evidence, unknowns, key_risks, confidence}
        """
        ...

    @abstractmethod
    async def assess_priced_in(
        self,
        symbol: str,
        event_description: str,
        price_history: str,
        abnormal_return: float,
    ) -> Dict[str, Any]:
        """
        Assess whether the event is already priced in (spec Item 11).
        Returns: {priced_in_score: float, assessment: str, reasoning: str}
        """
        ...

    @abstractmethod
    async def generate_journal_entry(
        self,
        trade_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate an AI trade journal entry (spec Item 25)."""
        ...

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Return embedding vector for a text string."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...


# ===========================================================
# D. Broker Provider
# ===========================================================

class BrokerProvider(ABC):
    """
    Abstract broker interface (paper or live).

    CRITICAL SAFETY RULE:
    The base class does NOT prevent live orders.
    That safety layer is enforced in:
      1. core/config.py (LIVE_TRADING_ENABLED check)
      2. risk/risk_manager.py (pre-order validation)
      3. PaperBroker (always returns simulated fills)

    LiveBroker must NEVER be instantiated if LIVE_TRADING_ENABLED=false.
    """

    @abstractmethod
    async def get_account(self) -> Dict[str, Any]:
        """Return account details (balance, margins, etc.)."""
        ...

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Return all open positions."""
        ...

    @abstractmethod
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Return current quote."""
        ...

    @abstractmethod
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
        Place an order.

        Returns order confirmation with broker_order_id.
        """
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel a pending order."""
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        """Return current status of an order."""
        ...

    @property
    @abstractmethod
    def is_paper(self) -> bool:
        """True for PaperBroker, False for LiveBroker."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ===========================================================
# E. Notification Provider
# ===========================================================

class NotificationProvider(ABC):
    """Abstract interface for sending alerts and notifications."""

    @abstractmethod
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "INFO",
        recipient: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an alert.
        Returns True if sent successfully.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def channel(self) -> str:
        """email | webhook | browser | sms"""
        ...
