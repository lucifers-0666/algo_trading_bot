"""Unit tests for Virtual Paper Broker and Portfolio Accounting."""

import tempfile
from pathlib import Path
import pytest
from trader.domain.models import OrderSide, OrderStatus
from trader.paper.accounting import PortfolioAccountant
from trader.paper.orders import OrderManager
from trader.paper.broker import VirtualPaperBroker
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.checks import RiskManager


@pytest.fixture
def broker():
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = PersistentKillSwitch(state_file=Path(tmpdir) / "ks.state")
        rm = RiskManager(kill_switch=ks)
        b = VirtualPaperBroker(risk_manager=rm, slippage_bps=0.0)
        yield b


def test_paper_broker_initial_capital():
    accountant = PortfolioAccountant(starting_cash=10000.0)
    state = accountant.get_portfolio_state()
    assert state.starting_cash == 10000.0
    assert state.cash_balance == 10000.0
    assert state.total_equity == 10000.0
    assert state.open_positions_count == 0


def test_paper_broker_buy_and_sell_lifecycle(broker):
    # 1. BUY Order: Entry ₹500, Stop ₹475 -> Stop distance ₹25 -> Sized to 2 shares (Risk ₹50 <= ₹50 budget)
    order_buy, trade_buy, assessment = broker.submit_simulated_order(
        symbol="SBIN",
        side=OrderSide.BUY,
        price=500.0,
        stop_loss=475.0,
    )
    assert assessment.approved is True
    assert order_buy.status == OrderStatus.FILLED
    assert trade_buy is not None
    assert trade_buy.quantity == 2
    assert trade_buy.price == 500.0

    state_after_buy = broker.accountant.get_portfolio_state()
    assert state_after_buy.open_positions_count == 1
    assert "SBIN" in broker.accountant.positions
    # Cash deducted: Gross (₹1,000) + Costs (~₹1.80)
    assert state_after_buy.cash_balance < 10000.0 - 1000.0

    # 2. SELL Order: Sell 2 shares @ ₹520 (Profit of ₹20/share gross)
    order_sell, trade_sell, assess_sell = broker.submit_simulated_order(
        symbol="SBIN",
        side=OrderSide.SELL,
        price=520.0,
    )
    assert assess_sell.approved is True
    assert order_sell.status == OrderStatus.FILLED
    assert trade_sell is not None
    assert trade_sell.quantity == 2
    assert trade_sell.price == 520.0

    state_after_sell = broker.accountant.get_portfolio_state()
    assert state_after_sell.open_positions_count == 0
    assert "SBIN" not in broker.accountant.positions
    # Gross gain = ₹40. Net realized P&L must be ~₹40 minus both trade costs
    assert state_after_sell.realized_pnl > 30.0 # Positively profitable net after fees
    assert state_after_sell.cash_balance > 10000.0


def test_paper_broker_rejects_unauthorized_risk_trade(broker):
    # Attempt to buy a ₹4,000 stock with ₹150 stop distance (risking ₹150 > ₹50 budget)
    order, trade, assess = broker.submit_simulated_order(
        symbol="TCS",
        side=OrderSide.BUY,
        price=4000.0,
        stop_loss=3850.0,
    )
    assert assess.approved is False
    assert order.status == OrderStatus.REJECTED
    assert trade is None
    assert "Risk budget breach" in order.rejection_reason

    # Verify no funds deducted
    state = broker.accountant.get_portfolio_state()
    assert state.cash_balance == 10000.0
    assert state.open_positions_count == 0



def test_paper_broker_rejects_user_quantity_above_risk_approved_size(broker):
    # Risk sizing approves 2 shares (₹50 planned risk), so a caller must not
    # override the quantity to 20 shares and bypass the risk manager.
    order, trade, assessment = broker.submit_simulated_order(
        symbol="SBIN",
        side=OrderSide.BUY,
        price=500.0,
        stop_loss=475.0,
        quantity=20,
    )
    assert assessment.approved is False
    assert order.status == OrderStatus.REJECTED
    assert trade is None
    assert broker.accountant.cash_balance == 10000.0
    assert broker.accountant.positions == {}

def test_portfolio_account_reset():
    accountant = PortfolioAccountant(starting_cash=10000.0)
    accountant.cash_balance = 7500.0
    accountant.realized_pnl = -500.0

    # Reset without confirmation must fail
    res_no = accountant.reset_account(confirmation=False)
    assert res_no is False
    assert accountant.cash_balance == 7500.0

    # Reset with confirmation must succeed
    res_yes = accountant.reset_account(confirmation=True)
    assert res_yes is True
    assert accountant.cash_balance == 10000.0
    assert accountant.realized_pnl == 0.0
