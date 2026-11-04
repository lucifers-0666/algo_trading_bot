"""Unit tests for Market Data Normalizer."""

from datetime import datetime
import pytz

from trader.domain.models import IST, Timeframe, DataSource
from trader.data.normalizer import parse_timestamp_to_ist, normalize_row_to_candle


def test_parse_timestamp_to_ist_formats():
    # String ISO
    dt1 = parse_timestamp_to_ist("2026-11-04 15:30:00")
    assert dt1.tzinfo.zone == "Asia/Kolkata"
    assert dt1.year == 2026 and dt1.month == 11 and dt1.day == 4

    # String NSE format
    dt2 = parse_timestamp_to_ist("04-Nov-2026")
    assert dt2.tzinfo.zone == "Asia/Kolkata"
    assert dt2.day == 4 and dt2.month == 11

    # Epoch milliseconds
    dt3 = parse_timestamp_to_ist(1730714400000)
    assert dt3.tzinfo.zone == "Asia/Kolkata"


def test_normalize_row_to_candle_bhavcopy():
    row = {
        "SYMBOL": "RELIANCE",
        "SERIES": "EQ",
        "OPEN": "2800.50",
        "HIGH": "2850.00",
        "LOW": "2790.00",
        "CLOSE": "2840.25",
        "TOTTRDQTY": "3500000",
        "TOTTRDVAL": "9900000000",
        "TIMESTAMP": "04-NOV-2026",
    }
    candle = normalize_row_to_candle(row)
    assert candle.symbol == "RELIANCE"
    assert candle.open == 2800.50
    assert candle.high == 2850.00
    assert candle.close == 2840.25
    assert candle.volume == 3500000.0
    assert candle.turnover == 9900000000.0
    assert candle.timestamp.tzinfo.zone == "Asia/Kolkata"


def test_normalize_row_to_candle_yahoo():
    row = {
        "Date": "2026-11-04",
        "Open": 1500.0,
        "High": 1520.0,
        "Low": 1490.0,
        "Close": 1515.0,
        "Volume": 500000,
    }
    candle = normalize_row_to_candle(row, default_symbol="INFY")
    assert candle.symbol == "INFY"
    assert candle.open == 1500.0
    assert candle.volume == 500000.0

