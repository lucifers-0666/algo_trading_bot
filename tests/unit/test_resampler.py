"""Unit Tests for Multi-Timeframe Candle Resampler.
Verifies aggregation math, timeframe parsing, downsampling restrictions, and OHLC invariants.
"""

from datetime import datetime, timedelta
import pytest

from trader.domain.models import Candle, Timeframe, DataSource, IST
from trader.data.resampler import resample_candles, parse_timeframe


def create_sample_minute_candles(count: int = 60, base_price: float = 100.0) -> list[Candle]:
    """Generates synthetic 1-minute sequential candles starting at 09:15 IST."""
    start_dt = IST.localize(datetime(2026, 3, 2, 9, 15, 0))
    candles = []
    p = base_price
    for i in range(count):
        ts = start_dt + timedelta(minutes=i)
        o = p
        h = p + 2.0
        l = p - 1.0
        c = p + 1.0
        v = 1000.0
        candles.append(
            Candle(
                exchange="NSE",
                symbol="TESTSTOCK",
                timestamp=ts,
                interval=Timeframe.MINUTE_1,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                source=DataSource.SYNTHETIC,
            )
        )
        p = c
    return candles


def test_parse_valid_and_invalid_timeframes():
    assert parse_timeframe("1m") == Timeframe.MINUTE_1
    assert parse_timeframe("3m") == Timeframe.MINUTE_3
    assert parse_timeframe("5m") == Timeframe.MINUTE_5
    assert parse_timeframe("15m") == Timeframe.MINUTE_15
    assert parse_timeframe("30m") == Timeframe.MINUTE_30
    assert parse_timeframe("1h") == Timeframe.HOUR_1
    assert parse_timeframe("1d") == Timeframe.DAILY
    assert parse_timeframe("1w") == Timeframe.WEEKLY

    with pytest.raises(ValueError, match="Unsupported timeframe"):
        parse_timeframe("2m")

    with pytest.raises(ValueError, match="Unsupported timeframe"):
        parse_timeframe("10d")


def test_resample_1m_to_5m():
    candles_1m = create_sample_minute_candles(60)
    resampled_5m = resample_candles(candles_1m, Timeframe.MINUTE_5)

    # 60 1-minute candles should aggregate into 12 5-minute candles
    assert len(resampled_5m) == 12

    first_bar = resampled_5m[0]
    assert first_bar.interval == Timeframe.MINUTE_5
    assert first_bar.open == candles_1m[0].open
    assert first_bar.close == candles_1m[4].close
    assert first_bar.high == max(c.high for c in candles_1m[:5])
    assert first_bar.low == min(c.low for c in candles_1m[:5])
    assert first_bar.volume == sum(c.volume for c in candles_1m[:5])


def test_resample_1m_to_15m():
    candles_1m = create_sample_minute_candles(60)
    resampled_15m = resample_candles(candles_1m, Timeframe.MINUTE_15)

    # 60 1-minute candles should aggregate into 4 15-minute candles
    assert len(resampled_15m) == 4
    for bar in resampled_15m:
        assert bar.interval == Timeframe.MINUTE_15
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close


def test_cannot_downsample_higher_to_lower_timeframe():
    # 5m candles cannot be downsampled to 1m without high-resolution source
    candles_1m = create_sample_minute_candles(15)
    resampled_15m = resample_candles(candles_1m, Timeframe.MINUTE_15)

    with pytest.raises(ValueError, match="Cannot downsample"):
        resample_candles(resampled_15m, Timeframe.MINUTE_1)


def test_resample_same_timeframe_returns_input():
    candles_1m = create_sample_minute_candles(10)
    result = resample_candles(candles_1m, Timeframe.MINUTE_1)
    assert result == candles_1m


def test_resample_empty_candles():
    assert resample_candles([], Timeframe.MINUTE_5) == []
