"""Unit tests for Risk Management and Kill Switch."""

import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from trader.domain.models import PortfolioState, Position, OrderSide, IST
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.sizing import calculate_position_size
from trader.risk.checks import RiskManager
from trader.data.freshness import FreshnessReport, FeedStatus


@pytest.fixture
def temp_kill_switch():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test_kill_switch.state"
        ks = PersistentKillSwitch(state_file=p)
        yield ks


def test_kill_switch_lifecycle_and_fail_closed(temp_kill_switch):
    assert temp_kill_switch.is_active() is False

    temp_kill_switch.activate("Test emergency halt")
    assert temp_kill_switch.is_active() is True
    assert "Test emergency halt" in temp_kill_switch.get_reason()

    temp_kill_switch.deactivate("Resuming operations")
    assert temp_kill_switch.is_active() is False

    # Corrupt state file to verify fail-closed
    temp_kill_switch.state_file.write_text("CORRUPT_JSON_DATA")
    assert temp_kill_switch.is_active() is True # Must fail closed


def test_position_sizing_normal_fit():
    # Equity: ₹10,000, 0.5% risk = ₹50
    # Entry: ₹500, Stop: ₹475 -> Stop distance = ₹25
    # Raw Qty = 50 / 25 = 2 shares.
    # 2 shares * ₹500 = ₹1,000 (10% of portfolio <= 25% single-stock cap)
    res = calculate_position_size(
        entry_price=500.0,
        stop_loss=475.0,
        total_equity=10000.0,
        cash_balance=10000.0,
        max_risk_pct=0.005,
    )
    assert res.approved is True
    assert res.quantity == 2
    assert res.calculated_risk_inr == 50.0
    assert res.allocated_capital_inr == 1000.0


def test_position_sizing_rejected_when_single_share_exceeds_risk():
    # Entry: ₹3,000, Stop: ₹2,900 -> Stop distance = ₹100
    # Risk budget = ₹50. 1 share risks ₹100 > ₹50. Must reject!
    res = calculate_position_size(
        entry_price=3000.0,
        stop_loss=2900.0,
        total_equity=10000.0,
        cash_balance=10000.0,
        max_risk_pct=0.005,
    )
    assert res.approved is False
    assert res.quantity == 0
    assert "Risk budget breach" in res.reason


def test_risk_manager_blocks_when_max_positions_reached(temp_kill_switch):
    rm = RiskManager(kill_switch=temp_kill_switch, max_open_positions=2)
    pf = PortfolioState(total_equity=10000.0, cash_balance=5000.0)

    # 2 active positions already held
    pos1 = Position(symbol="RELIANCE", quantity=1, current_price=2500.0)
    pos2 = Position(symbol="TCS", quantity=1, current_price=3500.0)

    assessment = rm.assess_order(
        symbol="INFY",
        side=OrderSide.BUY,
        price=1500.0,
        stop_loss=1470.0,
        portfolio=pf,
        open_positions=[pos1, pos2],
    )
    assert assessment.approved is False
    assert any("Max open positions reached" in err for err in assessment.rejection_reasons)


def test_risk_manager_blocks_when_feed_stale(temp_kill_switch):
    rm = RiskManager(kill_switch=temp_kill_switch)
    pf = PortfolioState(total_equity=10000.0, cash_balance=10000.0)

    stale_report = FreshnessReport(
        status=FeedStatus.STALE,
        is_actionable=False,
        latency_seconds=500.0,
        message="STALE FEED: 500s latency",
    )

    assessment = rm.assess_order(
        symbol="SBIN",
        side=OrderSide.BUY,
        price=800.0,
        stop_loss=780.0,
        portfolio=pf,
        open_positions=[],
        feed_freshness=stale_report,
    )
    assert assessment.approved is False
    assert any("freshness guard breach" in err for err in assessment.rejection_reasons)
