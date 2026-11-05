"""Unit tests for Multi-Broker Transaction Costs & Statutory Charges Engine.
Verifies DP charges on delivery sell orders, STT differentiation (delivery vs intraday),
stamp duty, GST, and roundtrip net PnL and breakeven calculations.
"""

import pytest
from trader.domain.models import OrderSide
from trader.backtest.costs import (
    calculate_trade_costs,
    simulate_roundtrip_trade,
    BrokerProfile,
    TradeType,
)


def test_angelone_delivery_zero_brokerage_with_dp_charges():
    """Angel One delivery: ₹0 brokerage, DP charges levied on SELL only."""
    # BUY delivery
    buy = calculate_trade_costs(
        side=OrderSide.BUY,
        price=1000.0,
        quantity=10,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.DELIVERY,
    )
    assert buy.brokerage_inr == 0.0
    assert buy.dp_charges_inr == 0.0
    assert buy.stt_inr > 0.0  # 0.1% STT on BUY delivery
    assert buy.stamp_duty_inr > 0.0  # Stamp duty on BUY delivery

    # SELL delivery
    sell = calculate_trade_costs(
        side=OrderSide.SELL,
        price=1050.0,
        quantity=10,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.DELIVERY,
    )
    assert sell.brokerage_inr == 0.0
    assert sell.dp_charges_inr == 23.60  # ₹20 + 18% GST = ₹23.60 for Angel One
    assert sell.stt_inr > 0.0  # 0.1% STT on SELL delivery
    assert sell.stamp_duty_inr == 0.0  # Zero stamp duty on SELL


def test_zerodha_and_dhan_dp_charges():
    """Verifies broker-specific DP charges."""
    sell_zerodha = calculate_trade_costs(
        side=OrderSide.SELL,
        price=500.0,
        quantity=20,
        broker=BrokerProfile.ZERODHA,
        trade_type=TradeType.DELIVERY,
    )
    # Zerodha: ₹13.50 + 18% GST = ₹15.93
    assert sell_zerodha.dp_charges_inr == 15.93

    sell_dhan = calculate_trade_costs(
        side=OrderSide.SELL,
        price=500.0,
        quantity=20,
        broker=BrokerProfile.DHAN,
        trade_type=TradeType.DELIVERY,
    )
    # Dhan: ₹12.50 + 18% GST = ₹14.75
    assert sell_dhan.dp_charges_inr == 14.75


def test_intraday_vs_delivery_stt_difference():
    """Intraday has 0% STT on BUY and 0.025% STT on SELL. Delivery has 0.1% on both."""
    buy_delivery = calculate_trade_costs(
        side=OrderSide.BUY,
        price=1000.0,
        quantity=10,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.DELIVERY,
        slippage_bps=0.0,
    )
    buy_intraday = calculate_trade_costs(
        side=OrderSide.BUY,
        price=1000.0,
        quantity=10,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.INTRADAY,
        slippage_bps=0.0,
    )

    assert buy_delivery.stt_inr == 10.0  # 0.10% of ₹10,000 = ₹10
    assert buy_intraday.stt_inr == 0.0   # 0% STT on intraday buy

    sell_intraday = calculate_trade_costs(
        side=OrderSide.SELL,
        price=1000.0,
        quantity=10,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.INTRADAY,
        slippage_bps=0.0,
    )
    # 0.025% of ₹10,000 = ₹2.50
    assert sell_intraday.stt_inr == 2.50
    assert sell_intraday.dp_charges_inr == 0.0  # No DP charges on intraday!


def test_roundtrip_simulation_and_breakeven():
    """Tests roundtrip simulation net P&L and breakeven calculation."""
    sim = simulate_roundtrip_trade(
        symbol="TCS",
        buy_price=3500.0,
        sell_price=3600.0,
        quantity=5,
        broker=BrokerProfile.ANGEL_ONE,
        trade_type=TradeType.DELIVERY,
    )

    assert sim.gross_pnl == 500.0
    assert sim.net_pnl < sim.gross_pnl  # Taxes deducted
    assert sim.total_dp_charges == 23.60
    assert sim.breakeven_sell_price > 3500.0
    assert sim.net_pnl > 400.0
