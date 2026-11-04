"""Unit tests for SQLite Database and Repositories."""

import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from trader.domain.models import (
    Candle,
    Order,
    Trade,
    PortfolioState,
    Timeframe,
    DataSource,
    OrderSide,
    OrderType,
    OrderStatus,
    IST,
)
from trader.storage.database import DatabaseManager
from trader.storage.repositories import (
    CandleRepository,
    OrderRepository,
    TradeRepository,
    PortfolioRepository,
    AuditRepository,
)


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_trader.db"
        db = DatabaseManager(db_path=db_path)
        yield db


def test_candle_repository_crud(temp_db):
    repo = CandleRepository(temp_db)
    dt1 = IST.localize(datetime(2026, 11, 3, 15, 30))
    dt2 = IST.localize(datetime(2026, 11, 4, 15, 30))

    c1 = Candle(symbol="RELIANCE", timestamp=dt1, open=2500, high=2550, low=2490, close=2540, volume=1000)
    c2 = Candle(symbol="RELIANCE", timestamp=dt2, open=2540, high=2580, low=2520, close=2570, volume=1200)

    inserted = repo.save_candles([c1, c2])
    assert inserted == 2

    fetched = repo.get_candles("RELIANCE")
    assert len(fetched) == 2
    assert fetched[0].close == 2540
    assert fetched[1].close == 2570

    symbols = repo.get_distinct_symbols()
    assert symbols == ["RELIANCE"]


def test_order_and_trade_repository(temp_db):
    order_repo = OrderRepository(temp_db)
    trade_repo = TradeRepository(temp_db)

    order = Order(
        order_id="ord_001",
        symbol="TCS",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=5,
        status=OrderStatus.PENDING,
    )
    order_repo.save_order(order)

    fetched_ord = order_repo.get_order("ord_001")
    assert fetched_ord is not None
    assert fetched_ord.symbol == "TCS"
    assert fetched_ord.status == OrderStatus.PENDING

    # Update order to filled
    order.status = OrderStatus.FILLED
    order_repo.save_order(order)
    assert order_repo.get_order("ord_001").status == OrderStatus.FILLED

    # Save trade
    trade = Trade(
        trade_id="trd_001",
        order_id="ord_001",
        symbol="TCS",
        side=OrderSide.BUY,
        quantity=5,
        price=3500.0,
        brokerage_inr=20.0,
        net_value_inr=17520.0,
    )
    trade_repo.save_trade(trade)

    trades = trade_repo.get_trades("TCS")
    assert len(trades) == 1
    assert trades[0].trade_id == "trd_001"
    assert trades[0].net_value_inr == 17520.0


def test_portfolio_and_audit_repository(temp_db):
    pf_repo = PortfolioRepository(temp_db)
    audit_repo = AuditRepository(temp_db)

    state = PortfolioState(
        starting_cash=10000.0,
        cash_balance=8500.0,
        reserved_margin=0.0,
        realized_pnl=50.0,
        unrealized_pnl=120.0,
        total_equity=10170.0,
        peak_equity=10170.0,
        max_drawdown_pct=0.0,
        open_positions_count=1,
    )
    pf_repo.save_snapshot(state)

    latest = pf_repo.get_latest_snapshot()
    assert latest is not None
    assert latest.cash_balance == 8500.0
    assert latest.total_equity == 10170.0

    # Audit log
    evt = audit_repo.log_event("RISK_LIMIT_CHECK", symbol="TCS", details={"approved": True, "qty": 5})
    assert evt.event_id.startswith("evt_")

    logs = audit_repo.get_recent_logs(limit=10)
    assert len(logs) == 1
    assert logs[0].event_type == "RISK_LIMIT_CHECK"
    assert logs[0].details["qty"] == 5
