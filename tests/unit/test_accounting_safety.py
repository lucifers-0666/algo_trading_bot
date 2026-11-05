"""Regression tests for virtual-account ledger integrity."""

import pytest

from trader.domain.models import OrderSide, Trade
from trader.paper.accounting import PortfolioAccountant


def make_trade(
    *,
    trade_id: str,
    side: OrderSide,
    quantity: int,
    price: float,
    net_value: float,
    total_costs: float = 0.0,
) -> Trade:
    return Trade(
        trade_id=trade_id,
        order_id=f"order-{trade_id}",
        symbol="SBIN",
        side=side,
        quantity=quantity,
        price=price,
        total_costs_inr=total_costs,
        net_value_inr=net_value,
    )


def test_oversell_is_rejected_without_crediting_cash():
    account = PortfolioAccountant(starting_cash=10_000.0)
    buy = make_trade(
        trade_id="buy-1",
        side=OrderSide.BUY,
        quantity=1,
        price=500.0,
        net_value=500.0,
    )
    account.apply_fill(buy)
    cash_before = account.cash_balance
    position_before = account.positions["SBIN"].model_copy(deep=True)

    oversell = make_trade(
        trade_id="sell-too-many",
        side=OrderSide.SELL,
        quantity=2,
        price=600.0,
        net_value=1_200.0,
    )

    with pytest.raises(ValueError, match="only holding 1"):
        account.apply_fill(oversell)

    assert account.cash_balance == cash_before
    assert account.positions["SBIN"].quantity == position_before.quantity
    assert account.positions["SBIN"].average_entry_price == position_before.average_entry_price


def test_sell_without_position_is_rejected_without_crediting_cash():
    account = PortfolioAccountant(starting_cash=10_000.0)
    sell = make_trade(
        trade_id="sell-empty",
        side=OrderSide.SELL,
        quantity=1,
        price=100.0,
        net_value=100.0,
    )

    with pytest.raises(ValueError, match="only holding 0"):
        account.apply_fill(sell)

    assert account.cash_balance == 10_000.0
    assert account.positions == {}


def test_buy_that_would_make_virtual_cash_negative_is_rejected():
    account = PortfolioAccountant(starting_cash=1_000.0)
    buy = make_trade(
        trade_id="buy-over-cash",
        side=OrderSide.BUY,
        quantity=2,
        price=500.0,
        net_value=1_001.0,
    )

    with pytest.raises(ValueError, match="Insufficient virtual cash"):
        account.apply_fill(buy)

    assert account.cash_balance == 1_000.0
    assert account.positions == {}
