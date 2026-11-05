import pytest
from pathlib import Path
from datetime import datetime

from trader.domain.models import Position, Trade, OrderSide, PortfolioState, IST
from trader.storage.database import DatabaseManager
from trader.storage.repositories import PositionRepository, PortfolioRepository
from trader.paper.accounting import PortfolioAccountant


def test_position_persistence_and_restart_recovery(tmp_path: Path):
    db_file = tmp_path / "test_persistence.db"
    db_mgr = DatabaseManager(db_path=db_file)
    pos_repo = PositionRepository(db=db_mgr)
    portfolio_repo = PortfolioRepository(db=db_mgr)

    # Initial session
    accountant1 = PortfolioAccountant(
        starting_cash=10000.0,
        portfolio_repo=portfolio_repo,
        position_repo=pos_repo,
    )

    trade1 = Trade(
        trade_id="trd_101",
        order_id="ord_101",
        symbol="INFY",
        side=OrderSide.BUY,
        quantity=5,
        price=1500.0,
        total_costs_inr=15.0,
        net_value_inr=7515.0,
        timestamp=datetime.now(IST),
    )
    accountant1.apply_fill(trade1)

    assert accountant1.cash_balance == 10000.0 - 7515.0
    assert "INFY" in accountant1.positions
    assert accountant1.positions["INFY"].quantity == 5

    # Simulate application restart: instantiate a fresh accountant on same db
    accountant2 = PortfolioAccountant(
        starting_cash=10000.0,
        portfolio_repo=portfolio_repo,
        position_repo=pos_repo,
    )

    assert "INFY" in accountant2.positions
    assert accountant2.positions["INFY"].quantity == 5
    assert accountant2.positions["INFY"].average_entry_price == 1500.0
    assert accountant2.cash_balance == 2485.0
    assert accountant2.total_equity == 2485.0 + (5 * 1500.0)

    # Now sell partially
    trade2 = Trade(
        trade_id="trd_102",
        order_id="ord_102",
        symbol="INFY",
        side=OrderSide.SELL,
        quantity=2,
        price=1600.0,
        total_costs_inr=8.0,
        net_value_inr=3192.0,
        timestamp=datetime.now(IST),
    )
    accountant2.apply_fill(trade2)

    assert accountant2.positions["INFY"].quantity == 3

    # Simulate second restart
    accountant3 = PortfolioAccountant(
        starting_cash=10000.0,
        portfolio_repo=portfolio_repo,
        position_repo=pos_repo,
    )
    assert accountant3.positions["INFY"].quantity == 3

    # Reset account with confirmation
    assert accountant3.reset_account(confirmation=True) is True
    assert len(accountant3.positions) == 0
    assert accountant3.cash_balance == 10000.0

    # Ensure positions table is clean in DB
    persisted_after_reset = pos_repo.get_all_positions()
    assert len(persisted_after_reset) == 0


def test_daily_loss_limit_uses_day_starting_equity(tmp_path: Path):
    from trader.risk.checks import RiskManager
    from trader.risk.kill_switch import PersistentKillSwitch

    ks_file = tmp_path / "ks_daily.state"
    kill_switch = PersistentKillSwitch(state_file=ks_file)
    kill_switch.deactivate("Reset for test")

    # RiskManager with 1% daily loss limit
    risk_mgr = RiskManager(
        kill_switch=kill_switch,
        daily_loss_limit_pct=0.01,
    )

    # Case 1: Account started at 10,000, grew to 12,000 yesterday.
    # Today's starting equity is 12,000. 1% limit is 120.
    portfolio = PortfolioState(
        starting_cash=10000.0,
        cash_balance=11800.0,
        day_starting_equity=12000.0,
        total_equity=11850.0, # Loss today is 150 > 120
    )

    assessment = risk_mgr.assess_order(
        symbol="TCS",
        side=OrderSide.BUY,
        price=3500.0,
        stop_loss=3400.0,
        portfolio=portfolio,
        open_positions=[],
    )

    assert assessment.approved is False
    assert any("Daily loss limit breached" in r for r in assessment.rejection_reasons)
