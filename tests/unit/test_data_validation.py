"""Unit tests for Data Validation Module."""

from datetime import datetime, timedelta
import pytz

from trader.domain.models import Candle, IST
from trader.data.validation import validate_single_candle, validate_candle_sequence


def test_validate_single_candle_valid():
    dt = datetime(2026, 11, 4, 15, 30, tzinfo=IST)
    c = Candle(
        symbol="RELIANCE",
        timestamp=dt,
        open=2500.0,
        high=2550.0,
        low=2490.0,
        close=2540.0,
        volume=1000.0,
    )
    res = validate_single_candle(c)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_validate_single_candle_future_timestamp():
    future_dt = datetime.now(IST) + timedelta(days=2)
    # We construct candle bypassing pydantic check if possible or using future date
    c = Candle(
        symbol="RELIANCE",
        timestamp=future_dt,
        open=2500.0,
        high=2550.0,
        low=2490.0,
        close=2540.0,
        volume=1000.0,
    )
    res = validate_single_candle(c)
    assert res.is_valid is False
    assert any("in the future" in err for err in res.errors)


def test_validate_candle_sequence_duplicates_and_order():
    base_dt = datetime(2026, 11, 1, 15, 30, tzinfo=IST)
    c1 = Candle(symbol="TCS", timestamp=base_dt, open=3000, high=3050, low=2980, close=3020, volume=100)
    c2 = Candle(symbol="TCS", timestamp=base_dt + timedelta(days=1), open=3020, high=3060, low=3010, close=3050, volume=120)
    # Duplicate timestamp
    c3 = Candle(symbol="TCS", timestamp=base_dt + timedelta(days=1), open=3050, high=3070, low=3030, close=3060, volume=110)
    # Out of order timestamp
    c4 = Candle(symbol="TCS", timestamp=base_dt - timedelta(days=1), open=2990, high=3010, low=2970, close=3000, volume=90)

    valid, res = validate_candle_sequence([c1, c2, c3, c4])
    assert len(valid) == 2 # Only c1 and c2 are valid and monotonic
    assert res.is_valid is False
    assert any("Duplicate timestamp" in err for err in res.errors)
    assert any("Out-of-order timestamp" in err for err in res.errors)
