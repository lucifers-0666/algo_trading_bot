import pytest
from datetime import datetime, date, time
from trader.domain.models import IST
from trader.data.calendar import NSETradingCalendar, default_nse_calendar
from tests.fixtures.synthetic_fixture import generate_synthetic_candles


def test_nse_calendar_holidays_and_weekends():
    """Verify that weekends and declared statutory holidays are excluded from trading days."""
    cal = default_nse_calendar

    # Sunday
    sunday = datetime(2026, 1, 4, 11, 0, tzinfo=IST)
    assert cal.is_trading_day(sunday) is False
    assert cal.is_market_open(sunday) is False

    # Republic Day (Jan 26, 2026 is Monday)
    republic_day = datetime(2026, 1, 26, 10, 0, tzinfo=IST)
    assert cal.is_trading_day(republic_day) is False
    assert cal.is_market_open(republic_day) is False

    # Regular Tuesday during trading hours (Jan 27, 2026, 10:30 IST)
    regular_day_open = datetime(2026, 1, 27, 10, 30, tzinfo=IST)
    assert cal.is_trading_day(regular_day_open) is True
    assert cal.is_market_open(regular_day_open) is True

    # Regular Tuesday after market close (Jan 27, 2026, 16:00 IST)
    regular_day_closed = datetime(2026, 1, 27, 16, 0, tzinfo=IST)
    assert cal.is_trading_day(regular_day_closed) is True
    assert cal.is_market_open(regular_day_closed) is False


def test_synthetic_data_local_rng_determinism():
    """Verify that synthetic generation is reproducible with seed and uses local RNG."""
    candles1 = generate_synthetic_candles("INFY", num_days=30, seed=123)
    candles2 = generate_synthetic_candles("INFY", num_days=30, seed=123)
    candles3 = generate_synthetic_candles("INFY", num_days=30, seed=999)

    assert len(candles1) == 30
    assert len(candles2) == 30
    assert candles1[0].close == candles2[0].close
    assert candles1[-1].close == candles2[-1].close
    # Different seed gives different results
    assert candles1[-1].close != candles3[-1].close



