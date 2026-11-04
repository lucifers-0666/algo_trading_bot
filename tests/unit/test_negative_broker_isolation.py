"""Negative Safety & Isolation Verification Tests.
PROVES THAT THE SYSTEM CANNOT ACCESS REAL BROKER ORDER ENDPOINTS.
PROVES THAT DELIBERATE RISK BYPASS ATTEMPTS ARE REJECTED.
"""

import tempfile
from pathlib import Path
import pytest
from trader.paper.broker import VirtualPaperBroker
from trader.risk.kill_switch import PersistentKillSwitch
from trader.risk.checks import RiskManager
from trader.domain.models import OrderSide


@pytest.fixture
def isolated_broker():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test_ks.state"
        ks = PersistentKillSwitch(state_file=p)
        rm = RiskManager(kill_switch=ks)
        broker = VirtualPaperBroker(risk_manager=rm)
        yield broker


def test_paper_mode_cannot_access_real_broker(isolated_broker):
    """Safety assertion proving paper mode has zero live broker connectivity."""
    assert isolated_broker.is_live_broker_connected() is False
    assert not hasattr(isolated_broker, "route_real_order")
    assert not hasattr(isolated_broker, "connect_demat_account")


def test_deliberate_risk_bypass_attempt_is_rejected(isolated_broker):
    """Negative security test: attempts to bypass risk limits with an oversized position."""
    # Attempt to order 1,000 shares of Reliance (₹2,800,000 on a ₹10,000 account)
    order, trade, assessment = isolated_broker.submit_simulated_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        price=2800.0,
        stop_loss=2750.0,
        quantity=1000, # Deliberate oversized bypass attempt
    )

    # Must be firmly rejected
    assert assessment.approved is False
    assert order.status.value == "REJECTED"
    assert trade is None
    assert any("breach" in r.lower() for r in assessment.rejection_reasons)

    # Prove ledger is untouched
    state = isolated_broker.accountant.get_portfolio_state()
    assert state.cash_balance == 10000.0
    assert state.open_positions_count == 0


def test_kill_switch_active_blocks_all_execution(isolated_broker):
    """Proves that engaged kill switch definitively blocks trade submission."""
    isolated_broker.risk_manager.kill_switch.activate("Testing safety block")

    order, trade, assessment = isolated_broker.submit_simulated_order(
        symbol="SBIN",
        side=OrderSide.BUY,
        price=500.0,
        stop_loss=475.0,
    )
    assert assessment.approved is False
    assert order.status.value == "REJECTED"
    assert trade is None
    assert any("Kill Switch is ENGAGED" in r for r in assessment.rejection_reasons)
