"""Regression tests for paper broker cash/inventory guard handling."""

from trader.domain.models import OrderSide, OrderStatus
from trader.paper.accounting import PortfolioAccountant
from trader.paper.broker import VirtualPaperBroker
from trader.risk.checks import RiskManager
from trader.risk.kill_switch import PersistentKillSwitch


def test_order_is_rejected_cleanly_when_fees_exceed_virtual_cash(tmp_path):
    kill_switch = PersistentKillSwitch(state_file=tmp_path / "kill-switch.state")
    kill_switch.deactivate("Explicit test fixture reset")

    accountant = PortfolioAccountant(starting_cash=1_000.0)
    risk_manager = RiskManager(
        kill_switch=kill_switch,
        max_risk_per_trade_pct=1.0,
        max_position_size_pct=1.0,
        max_portfolio_exposure_pct=1.0,
    )
    broker = VirtualPaperBroker(
        accountant=accountant,
        risk_manager=risk_manager,
        slippage_bps=0.0,
        brokerage_flat=20.0,
    )

    # The gross purchase consumes all ₹1,000. Brokerage/taxes make the
    # actual cash outflow larger, so the virtual broker must reject it.
    order, trade, assessment = broker.submit_simulated_order(
        symbol="SBIN",
        side=OrderSide.BUY,
        price=500.0,
        stop_loss=450.0,
    )

    assert assessment.approved is False
    assert order.status == OrderStatus.REJECTED
    assert trade is None
    assert "Insufficient virtual cash" in order.rejection_reason
    assert accountant.cash_balance == 1_000.0
    assert accountant.positions == {}
