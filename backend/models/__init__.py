"""
models/__init__.py — Import all ORM models so Alembic can auto-detect them.
"""

from db.base import Base  # noqa: F401

from models.user import User, Alert                       # noqa: F401
from models.company import Company, Symbol, Exchange, CompanyRelationship  # noqa: F401
from models.price import Price, CorporateAction, IndexConstituent  # noqa: F401
from models.news import NewsSource, NewsItem, EventCluster   # noqa: F401
from models.event import Event                            # noqa: F401
from models.fundamental import Financial, Guidance        # noqa: F401
from models.trading import (                              # noqa: F401
    Portfolio, Order, Position,
    TradeThesis, TradeJournalEntry,
)
from models.risk import RiskEvent, BacktestRun, AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User", "Alert",
    "Company", "Symbol", "Exchange", "CompanyRelationship",
    "Price", "CorporateAction", "IndexConstituent",
    "NewsSource", "NewsItem", "EventCluster",
    "Event",
    "Financial", "Guidance",
    "Portfolio", "Order", "Position", "TradeThesis", "TradeJournalEntry",
    "RiskEvent", "BacktestRun", "AuditLog",
]
