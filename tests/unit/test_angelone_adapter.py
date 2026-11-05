"""Unit tests for AngelOneAdapter.
Verifies read-only isolation, credential verification, pyotp session authentication,
historical candle conversion, and 5-level market depth parsing.
"""

from unittest.mock import MagicMock
from datetime import datetime, timedelta
import pytest

from trader.domain.models import DataSource, Timeframe, IST
from trader.providers.angelone_adapter import AngelOneAdapter, STANDARD_ANGEL_TOKENS


def test_angelone_read_only_isolation():
    """Asserts that AngelOneAdapter has zero broker execution or portfolio modification methods."""
    adapter = AngelOneAdapter()
    forbidden = [
        "place_order", "placeOrder", "modify_order", "modifyOrder",
        "cancel_order", "cancelOrder", "holding", "allholding",
        "position", "convertPosition", "orderBook", "tradeBook"
    ]
    for method in forbidden:
        assert not hasattr(adapter, method), f"Safety violation: {method} found on AngelOneAdapter"


def test_angelone_configured_status():
    """Verifies that is_configured returns True only when all credentials exist."""
    unconf = AngelOneAdapter()
    assert unconf.is_configured is False

    conf = AngelOneAdapter(
        api_key="TEST_API_KEY",
        client_code="A100200",
        pin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    assert conf.is_configured is True
    assert conf.source_type == DataSource.ANGELONE


def test_angelone_instrument_resolution():
    """Verifies that indices and liquid equities resolve to Angel One tokens."""
    adapter = AngelOneAdapter()
    nifty = adapter.resolve_instrument("NIFTY")
    assert nifty is not None
    assert nifty["exchange"] == "NSE"
    assert nifty["token"] == "99926000"

    reliance = adapter.resolve_instrument("RELIANCE")
    assert reliance is not None
    assert reliance["exchange"] == "NSE"
    assert reliance["token"] == "2885"

    sensex = adapter.resolve_instrument("SENSEX")
    assert sensex is not None
    assert sensex["exchange"] == "BSE"


def test_angelone_mocked_authentication():
    """Tests successful TOTP authentication session generation."""
    mock_connect = MagicMock()
    mock_connect.generateSession.return_value = {
        "status": True,
        "message": "SUCCESS",
        "data": {
            "jwtToken": "mock_jwt_123",
            "refreshToken": "mock_refresh_456",
            "feedToken": "mock_feed_789",
        },
    }

    adapter = AngelOneAdapter(
        api_key="API_KEY",
        client_code="CLIENT_CODE",
        pin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
        smart_connect=mock_connect,
    )

    success = adapter.authenticate()
    assert success is True
    assert adapter.is_connected is True
    assert adapter._jwt_token == "mock_jwt_123"


def test_angelone_mocked_get_candles():
    """Tests fetching and canonical conversion of historical candles."""
    mock_connect = MagicMock()
    mock_connect.generateSession.return_value = {
        "status": True,
        "data": {"jwtToken": "token", "feedToken": "feed"},
    }
    mock_connect.getCandleData.return_value = {
        "status": True,
        "data": [
            ["2026-01-01T09:15:00+05:30", 2500.0, 2550.0, 2480.0, 2520.0, 150000],
            ["2026-01-02T09:15:00+05:30", 2520.0, 2580.0, 2510.0, 2570.0, 180000],
        ],
    }

    adapter = AngelOneAdapter(
        api_key="KEY",
        client_code="CLIENT",
        pin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
        smart_connect=mock_connect,
    )
    adapter._is_connected = True
    adapter._jwt_token = "token"
    adapter._token_expiry = datetime.now(IST) + timedelta(hours=10)

    candles = adapter.get_historical_candles("RELIANCE", timeframe=Timeframe.DAILY)
    assert len(candles) == 2
    assert candles[0].symbol == "RELIANCE"
    assert candles[0].close == 2520.0
    assert candles[1].high == 2580.0


def test_angelone_mocked_get_market_depth():
    """Tests 5-level market depth parsing from SmartConnect getMarketData FULL response."""
    mock_connect = MagicMock()
    mock_connect.getMarketData.return_value = {
        "status": True,
        "data": {
            "fetched": [
                {
                    "tradingSymbol": "RELIANCE-EQ",
                    "depth": {
                        "buy": [
                            {"price": 2500.0, "quantity": 1000, "orders": 12},
                            {"price": 2499.5, "quantity": 800, "orders": 8},
                            {"price": 2499.0, "quantity": 600, "orders": 6},
                            {"price": 2498.5, "quantity": 400, "orders": 4},
                            {"price": 2498.0, "quantity": 200, "orders": 2},
                        ],
                        "sell": [
                            {"price": 2501.0, "quantity": 900, "orders": 10},
                            {"price": 2501.5, "quantity": 700, "orders": 7},
                            {"price": 2502.0, "quantity": 500, "orders": 5},
                            {"price": 2502.5, "quantity": 300, "orders": 3},
                            {"price": 2503.0, "quantity": 100, "orders": 1},
                        ],
                    },
                }
            ]
        },
    }

    adapter = AngelOneAdapter(
        api_key="KEY",
        client_code="CLIENT",
        pin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
        smart_connect=mock_connect,
    )
    adapter._is_connected = True
    adapter._jwt_token = "token"
    adapter._token_expiry = datetime.now(IST) + timedelta(hours=10)

    depth = adapter.get_market_depth("RELIANCE")
    assert depth.symbol == "RELIANCE"
    assert depth.best_bid == 2500.0
    assert depth.best_ask == 2501.0
    assert depth.spread == 1.0
    assert len(depth.levels) == 5
    assert depth.total_bid_quantity == 3000
    assert depth.total_ask_quantity == 2500
    assert depth.top5_imbalance > 0  # more buyers than sellers
