"""Unit tests for DhanHQ Market Data Adapter and Dynamic Calendar."""

from datetime import datetime, date, time
import pytest
from unittest.mock import patch, MagicMock

from trader.domain.models import DataSource, IST
from trader.providers.dhan_adapter import DhanAdapter
from trader.data.calendar import NSETradingCalendar


def test_dhan_adapter_unconfigured_defaults_safely():
    adapter = DhanAdapter()
    assert adapter.is_configured is False
    assert adapter.source_type == DataSource.DHAN

    status = adapter.get_connection_status()
    assert status["configured"] is False
    assert status["mode"] == "READ_ONLY_MARKET_DATA"

    # Fetching quote when unconfigured raises ConnectionError (fail-closed)
    with pytest.raises(ConnectionError):
        adapter.get_latest_quote("RELIANCE")

    # Historical candles returns empty list safely
    candles = adapter.get_historical_candles("RELIANCE")
    assert candles == []

    # Market depth returns empty list with UNAVAILABLE source
    depth = adapter.get_market_depth("RELIANCE")
    assert depth["source"] == DataSource.UNAVAILABLE.value
    assert depth["bids"] == []


def test_dhan_adapter_parse_quote_packet():
    adapter = DhanAdapter(client_id="TEST_CLIENT", access_token="TEST_TOKEN")
    assert adapter.is_configured is True

    sample_packet = {
        "INFY": {
            "last_price": 1625.50,
            "volume": 2500000,
            "buy_price": 1625.00,
            "sell_price": 1626.00,
            "last_trade_time": "2026-11-05T10:30:00+05:30",
        }
    }

    quote = adapter.parse_quote_packet("INFY", sample_packet)
    assert quote.symbol == "INFY"
    assert quote.ltp == 1625.50
    assert quote.bid == 1625.00
    assert quote.ask == 1626.00
    assert quote.volume == 2500000
    assert quote.source == DataSource.DHAN


def test_dhan_adapter_parse_market_depth_packet():
    adapter = DhanAdapter(client_id="TEST_CLIENT", access_token="TEST_TOKEN")

    sample_depth = {
        "TCS": {
            "bids": [
                {"price": 3950.0, "quantity": 100, "orders": 5},
                {"price": 3949.5, "quantity": 250, "orders": 12},
            ],
            "asks": [
                {"price": 3951.0, "quantity": 150, "orders": 8},
                {"price": 3951.5, "quantity": 300, "orders": 15},
            ],
        }
    }

    depth = adapter.parse_market_depth_packet("TCS", sample_depth)
    assert depth["symbol"] == "TCS"
    assert len(depth["bids"]) == 2
    assert len(depth["asks"]) == 2
    assert depth["total_buy_quantity"] == 350
    assert depth["total_sell_quantity"] == 450
    assert depth["source"] == DataSource.DHAN.value


def test_nse_calendar_muhurat_trading_session():
    cal = NSETradingCalendar()
    # Diwali 2026 Muhurat is on 2026-11-09 from 18:15 to 19:15 IST
    muhurat_time = datetime(2026, 11, 9, 18, 30, tzinfo=IST)
    assert cal.is_muhurat_session(muhurat_time) is True
    assert cal.is_market_open(muhurat_time) is True

    # 17:30 IST on same day is outside Muhurat and outside regular hours
    pre_muhurat = datetime(2026, 11, 9, 17, 30, tzinfo=IST)
    assert cal.is_muhurat_session(pre_muhurat) is False
    assert cal.is_market_open(pre_muhurat) is False


def test_nse_calendar_dynamic_holiday_addition_and_removal():
    cal = NSETradingCalendar()
    test_day = date(2026, 6, 10) # Normal Wednesday
    assert cal.is_trading_day(test_day) is True

    cal.add_holiday(test_day)
    assert cal.is_trading_day(test_day) is False

    cal.remove_holiday(test_day)
    assert cal.is_trading_day(test_day) is True
