"""
tests/test_paper_trading.py — Paper broker and trading engine tests.
"""

from __future__ import annotations

import pytest

from trading.paper_broker import PaperBroker


@pytest.mark.asyncio
async def test_default_paper_account_starts_with_50000_inr() -> None:
    broker = PaperBroker()

    account = await broker.get_account()

    assert account["initial_capital"] == 50_000.0
    assert account["cash"] == 50_000.0
    assert account["currency"] == "INR"


@pytest.fixture
def broker() -> PaperBroker:
    return PaperBroker(initial_capital=1_000_000.0)


@pytest.mark.asyncio
async def test_initial_account_state(broker: PaperBroker) -> None:
    account = await broker.get_account()
    assert account["cash"] == 1_000_000.0
    assert account["total_equity"] == 1_000_000.0
    assert account["is_paper"] is True
    assert account["currency"] == "INR"


@pytest.mark.asyncio
async def test_buy_order_reduces_cash(broker: PaperBroker) -> None:
    result = await broker.place_order(
        ticker="TCS", direction="BUY", quantity=10, order_type="MARKET", price=4000.0
    )
    assert result["status"] == "FILLED"
    assert result["is_paper"] is True

    account = await broker.get_account()
    # Cash reduced by notional + commission + slippage
    assert account["cash"] < 1_000_000.0
    assert account["cash"] > 900_000.0  # shouldn't have spent too much


@pytest.mark.asyncio
async def test_sell_without_position_rejected(broker: PaperBroker) -> None:
    result = await broker.place_order(
        ticker="INFY", direction="SELL", quantity=10, order_type="MARKET", price=1500.0
    )
    assert result["status"] == "REJECTED"
    assert "Insufficient position" in result["rejection_reason"]


@pytest.mark.asyncio
async def test_buy_then_sell_position_closes(broker: PaperBroker) -> None:
    # Buy 10 shares
    await broker.place_order("WIPRO", "BUY", 10, "MARKET", price=500.0)
    positions_before = await broker.get_positions()
    assert len(positions_before) == 1
    assert positions_before[0]["symbol"] == "WIPRO"
    assert positions_before[0]["ticker"] == "WIPRO"

    # Sell all 10 shares
    await broker.place_order("WIPRO", "SELL", 10, "MARKET", price=550.0)
    positions_after = await broker.get_positions()
    assert len(positions_after) == 0  # Position closed


@pytest.mark.asyncio
async def test_updated_market_price_is_used_for_open_position(broker: PaperBroker) -> None:
    await broker.place_order("NSE_EQ|INE467B01029", "BUY", 10, "MARKET", price=4000.0)
    broker.update_price("NSE_EQ|INE467B01029", 4100.0)

    positions = await broker.get_positions()
    assert positions[0]["ticker"] == "NSE_EQ|INE467B01029"
    assert positions[0]["current_price"] == 4100.0


@pytest.mark.asyncio
async def test_insufficient_cash_rejected(broker: PaperBroker) -> None:
    # Try to buy 3000 shares at 2500 = 7.5M > 1M initial capital
    result = await broker.place_order("RELIANCE", "BUY", 3000, "MARKET", price=2500.0)
    assert result["status"] == "REJECTED"
    assert "cash" in result["rejection_reason"].lower()


@pytest.mark.asyncio
async def test_slippage_applied_to_buy(broker: PaperBroker) -> None:
    result = await broker.place_order("HDFC", "BUY", 1, "MARKET", price=1000.0)
    assert result["status"] == "FILLED"
    # Fill price must be slightly above requested (slippage on buy)
    assert result["fill_price"] >= 1000.0


@pytest.mark.asyncio
async def test_slippage_applied_to_sell(broker: PaperBroker) -> None:
    await broker.place_order("HDFC", "BUY", 5, "MARKET", price=1000.0)
    result = await broker.place_order("HDFC", "SELL", 5, "MARKET", price=1000.0)
    assert result["status"] == "FILLED"
    # Fill price must be slightly below requested (slippage on sell)
    assert result["fill_price"] <= 1000.0


@pytest.mark.asyncio
async def test_commission_is_deducted(broker: PaperBroker) -> None:
    result = await broker.place_order("BAJAJ", "BUY", 10, "MARKET", price=8000.0)
    assert result["commission"] > 0


@pytest.mark.asyncio
async def test_fills_are_recorded(broker: PaperBroker) -> None:
    await broker.place_order("TATASTEEL", "BUY", 5, "MARKET", price=150.0)
    fills = broker.get_fills()
    assert len(fills) == 1
    assert fills[0]["ticker"] == "TATASTEEL"


@pytest.mark.asyncio
async def test_invalid_direction_rejected(broker: PaperBroker) -> None:
    result = await broker.place_order("TCS", "HOLD", 10, "MARKET", price=4000.0)
    assert result["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_zero_quantity_rejected(broker: PaperBroker) -> None:
    result = await broker.place_order("TCS", "BUY", 0, "MARKET", price=4000.0)
    assert result["status"] == "REJECTED"
