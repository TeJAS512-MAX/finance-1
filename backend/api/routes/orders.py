"""api/routes/orders.py — Real order history from the active broker."""
from fastapi import APIRouter

router = APIRouter()

@router.get("", summary="List real order history from the active broker")
async def list_orders():
    """Returns actual filled/rejected orders from the paper or live broker."""
    from trading.bot_engine import engine

    if engine.broker is None:
        from core.config import get_settings
        mode = "Live" if get_settings().live_trading_enabled else "Paper"
        return {"orders": [], "note": f"Start the Trading Engine to see orders. Mode: {mode}"}

    broker = engine.broker

    # PaperBroker exposes get_fills()
    if hasattr(broker, 'get_fills'):
        fills = broker.get_fills()
        orders = []
        for f in reversed(fills):  # newest first
            orders.append({
                "id": f.get("order_id", "")[:12],
                "symbol": f.get("ticker", "").split("|")[-1] if "|" in f.get("ticker", "") else f.get("ticker", ""),
                "side": f.get("direction", ""),
                "type": f.get("order_type", "MARKET"),
                "qty": f.get("quantity", 0),
                "price": f.get("fill_price", 0),
                "status": f.get("status", "FILLED"),
                "time": f.get("filled_at", "")[:19].replace("T", " ") if f.get("filled_at") else "--",
                "notional": f.get("notional", 0),
                "commission": f.get("commission", 0),
            })
        return {"orders": orders, "mode": "Paper"}

    # LiveBroker exposes get_orders() when real trading is active
    if hasattr(broker, "get_orders"):
        return {"orders": await broker.get_orders(), "mode": "Live"}
    return {"orders": [], "note": "Live broker order history not available."}
