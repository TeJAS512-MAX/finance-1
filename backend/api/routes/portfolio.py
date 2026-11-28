"""api/routes/portfolio.py"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps import require_api_access
from core.config import get_settings
from datetime import datetime

router = APIRouter()
settings = get_settings()

async def get_broker():
    """Always return the SAME broker the bot engine is trading with."""
    from trading.bot_engine import engine
    
    if engine.broker is not None:
        return engine.broker
    
    if settings.live_trading_enabled:
        from os import environ
        from trading.live_broker import LiveBroker
        return LiveBroker(
            api_key=environ.get("UPSTOX_API_KEY", ""),
            api_secret=environ.get("UPSTOX_API_SECRET", ""),
            redirect_uri=environ.get("UPSTOX_REDIRECT_URI", "https://127.0.0.1")
        )
    else:
        from trading.paper_broker import PaperBroker
        return PaperBroker()

@router.get("", summary="Get portfolio summary", dependencies=[Depends(require_api_access("read:portfolio"))])
async def get_portfolio(): 
    broker = await get_broker()
    account = await broker.get_account()
    return account

@router.get("/positions", summary="Get open positions", dependencies=[Depends(require_api_access("read:portfolio"))])
async def get_positions(): 
    broker = await get_broker()
    positions = await broker.get_positions()
    return {"positions": positions}

@router.get("/history", summary="Get equity curve and trade P&L history", dependencies=[Depends(require_api_access("read:portfolio"))])
async def get_history(market_mode: Literal["stocks", "crypto"] = Query("stocks")):
    """Returns equity snapshots and per-trade P&L for the dashboard charts."""
    from trading.bot_engine import engine
    
    if engine.broker is None:
        return {"market_mode": market_mode, "history": [], "trades": []}
    
    broker = engine.broker
    account = await broker.get_account()
    
    # For PaperBroker: read fills to build trade P&L bars
    trades = []
    equity_history = []
    
    if hasattr(broker, 'get_fills'):
        fills = [
            fill for fill in broker.get_fills()
            if fill.get("market_mode", "stocks") == market_mode
        ]
        running_equity = account.get('initial_capital', 1000.0)
        
        for i, fill in enumerate(fills):
            direction = fill.get('direction', '')
            notional = fill.get('notional', 0)
            commission = fill.get('commission', 0)
            
            if direction == 'BUY':
                running_equity -= (notional + commission)
            else:  # SELL
                running_equity += (notional - commission)
            
            t = fill.get('filled_at', datetime.now().isoformat())
            time_label = t[11:16] if len(t) > 16 else str(i + 1)  # HH:MM
            
            equity_history.append({
                "time": time_label,
                "equity": round(running_equity, 2)
            })
            
            if direction == 'SELL':
                trades.append({
                    "label": time_label,
                    "pnl": fill.get('realized_pnl', 0.0),
                    "symbol": fill.get('ticker', ''),
                    "market_mode": fill.get("market_mode", market_mode),
                })
        
        # Add current equity as final point
        current_equity = account.get('total_equity', running_equity)
        
        # Always add the current point
        equity_history.append({
            "time": datetime.now().strftime("%H:%M"),
            "equity": round(current_equity, 2)
        })
        
        # If there are no trades yet, Recharts needs at least 2 points to draw a line
        if len(equity_history) == 1:
            equity_history.insert(0, {
                "time": "Start",
                "equity": round(current_equity, 2)
            })
    
    return {"market_mode": market_mode, "history": equity_history, "trades": trades}
