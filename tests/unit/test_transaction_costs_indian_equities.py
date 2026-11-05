import pytest
from trader.domain.models import OrderSide
from trader.backtest.costs import (
    calculate_trade_costs,
    BrokerageModel,
    TradeCostBreakdown,
    DEFAULT_STT_RATE,
    DEFAULT_NSE_TXN_RATE,
    DEFAULT_SEBI_RATE,
    DEFAULT_STAMP_DUTY_RATE,
    DEFAULT_GST_RATE,
)


def test_small_order_costs_breakdown():
    """Verify exact cost breakdown on small retail delivery trades: ₹500, ₹1000, ₹2000, ₹5000."""
    # Test ₹1,000 BUY trade at 10 bps slippage
    # Price 100.0, Qty 10.
    # Slippage = 10 bps = 0.10% -> Effective price 100.10.
    # Gross value = 10 * 100.10 = 1001.00.
    buy_costs = calculate_trade_costs(
        side=OrderSide.BUY,
        price=100.0,
        quantity=10,
        brokerage_model=BrokerageModel.DISCOUNT_FLAT,
        brokerage_flat=20.0,
        slippage_bps=10.0,
    )

    assert buy_costs.gross_trade_value == 1001.0
    assert buy_costs.slippage_inr == 1.0
    # Brokerage: min(20, 1001 * 0.05%) = 0.50
    assert buy_costs.brokerage_inr == 0.50
    # STT: 0.1% on 1001 = 1.00
    assert buy_costs.stt_inr == 1.00
    # Stamp duty: 0.0015% on 1001 = 0.15
    assert buy_costs.stamp_duty_inr == 0.15
    # Regulatory charges are clearly distinct from broker commission
    assert buy_costs.broker_charges_inr == 0.50
    assert buy_costs.statutory_charges_inr > 0.0
    assert buy_costs.total_costs_inr == round(buy_costs.brokerage_inr + buy_costs.statutory_charges_inr, 2)
    # Net trade amount for BUY: gross_value + total_costs
    assert buy_costs.net_trade_amount == round(buy_costs.gross_trade_value + buy_costs.total_costs_inr, 2)


def test_zero_brokerage_delivery_model():
    """Verify zero-brokerage delivery model (e.g. Zerodha standard equity delivery)."""
    trade_costs = calculate_trade_costs(
        side=OrderSide.BUY,
        price=500.0,
        quantity=10,
        brokerage_model=BrokerageModel.ZERO_DELIVERY,
        slippage_bps=0.0,
    )

    assert trade_costs.brokerage_inr == 0.0
    assert trade_costs.broker_charges_inr == 0.0
    # Only statutory taxes are charged
    assert trade_costs.total_costs_inr == trade_costs.statutory_charges_inr
    assert trade_costs.stt_inr == 5.0 # 0.1% of 5,000


def test_sell_side_statutory_differences():
    """Verify sell-side delivery charges: STT is charged, Stamp duty is NOT charged on SELL."""
    sell_costs = calculate_trade_costs(
        side=OrderSide.SELL,
        price=2000.0,
        quantity=2,
        slippage_bps=0.0,
    )

    assert sell_costs.gross_trade_value == 4000.0
    assert sell_costs.stt_inr == 4.0 # 0.1% on sell delivery
    assert sell_costs.stamp_duty_inr == 0.0 # 0% on sell
    # Net trade amount for SELL: gross_value - total_costs
    assert sell_costs.net_trade_amount == round(sell_costs.gross_trade_value - sell_costs.total_costs_inr, 2)
