"""Unit tests for TrueData Adapter."""

import json
from trader.domain.models import DataSource
from trader.providers.truedata_adapter import TrueDataAdapter


def test_truedata_adapter_unconfigured_defaults_safely():
    adapter = TrueDataAdapter()
    assert adapter.is_configured is False
    status = adapter.get_connection_status()
    assert status["status"] == "DISABLED"
    assert status["configured"] is False

    # Historical candles return empty without crash
    candles = adapter.get_historical_candles("RELIANCE")
    assert candles == []


def test_truedata_adapter_parse_websocket_message():
    adapter = TrueDataAdapter(username="dummy", password="dummy")
    assert adapter.is_configured is True

    raw_frame = json.dumps({
        "symbol": "RELIANCE",
        "ltp": 2855.20,
        "bid": 2855.00,
        "ask": 2855.50,
        "volume": 4200000,
    })

    quote = adapter.parse_websocket_message(raw_frame)
    assert quote is not None
    assert quote.symbol == "RELIANCE"
    assert quote.ltp == 2855.20
    assert quote.bid == 2855.00
    assert quote.source == DataSource.TRUEDATA
