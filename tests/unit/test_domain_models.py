"""Unit tests for Canonical Domain Models."""

from datetime import datetime
import pytest
import pytz

from trader.domain.models import (
    Candle,
    Quote,
    Order,
    Trade,
    Position,
    PortfolioState,
    AuditLog,
    DataSource,
    Timeframe,
    OrderSide,
    OrderType,
    OrderStatus,
    IST,
)


def test_candle_creation_valid():
    dt = datetime(2026, 11, 4, 15, 30, tzinfo=IST)
    c = Candle(
        exchange="NSE",
        symbol="reliance",
        timestamp=dt,
        interval=Timeframe.DAILY,
        open=2500.0,
        high=2550.0,
        low=2480.0,
        close=2530.0,
        volume=100000.0,
        source=DataSource.SYNTHETIC,
    )
    assert c.symbol == "RELIANCE"
    assert c.open == 2500.0
    assert c.high == 2550.0
    assert c.low == 2480.0
    assert c.close == 2530.0
    assert c.timestamp.tzinfo.zone == "Asia/Kolkata"


def test_candle_validation_high_less_than_low():
    dt = datetime(2026, 11, 4, 15, 30, tzinfo=IST)
    with pytest.raises(ValueError, match="cannot be less than Low"):
        Candle(
            symbol="TCS",
            timestamp=dt,
            open=3000.0,
            high=2900.0,
            low=2950.0,
            close=2920.0,
            volume=5000.0,
        )


def test_candle_validation_high_less_than_open():
    dt = datetime(2026, 11, 4, 15, 30, tzinfo=IST)
    with pytest.raises(ValueError, match="must be >= Open"):
        Candle(
            symbol="TCS",
            timestamp=dt,
            open=3000.0,
            high=2950.0,
            low=2900.0,
            close=2920.0,
            volume=5000.0,
        )


def test_candle_validation_low_greater_than_close():
    dt = datetime(2026, 11, 4, 15, 30, tzinfo=IST)
    with pytest.raises(ValueError, match="must be <= Open"):
        Candle(
            symbol="TCS",
            timestamp=dt,
            open=3000.0,
            high=3100.0,
            low=2950.0,
            close=2900.0,
            volume=5000.0,
        )


def test_quote_creation():
    q = Quote(
        symbol="infy",
        ltp=1650.0,
        bid=1649.5,
        ask=1650.5,
        volume=1200000.0,
    )
    assert q.symbol == "INFY"
    assert q.ltp == 1650.0


def test_position_unrealized_pnl_update():
    pos = Position(
        symbol="SBIN",
        quantity=10,
        average_entry_price=800.0,
        current_price=800.0,
    )
    assert pos.unrealized_pnl == 0.0

    pos.update_market_price(820.0)
    assert pos.current_price == 820.0
    assert pos.unrealized_pnl == 200.0

    pos.update_market_price(790.0)
    assert pos.current_price == 790.0
    assert pos.unrealized_pnl == -100.0

