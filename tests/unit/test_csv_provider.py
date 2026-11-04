"""Unit tests for CSV Data Provider."""

from pathlib import Path
from trader.providers.csv_provider import CSVDataProvider
from trader.domain.models import DataSource


def test_csv_provider_loads_directory():
    provider = CSVDataProvider(data_path="data/sample")
    status = provider.get_connection_status()
    assert status["provider"] == "csv"
    assert status["connected"] is True
    assert status["loaded_symbols_count"] >= 3
    assert "RELIANCE" in status["loaded_symbols"]


def test_csv_provider_get_historical_and_quote():
    provider = CSVDataProvider(data_path="data/sample")
    candles = provider.get_historical_candles("RELIANCE")
    assert len(candles) > 0
    assert candles[0].symbol == "RELIANCE"
    assert candles[0].source == DataSource.CSV

    quote = provider.get_latest_quote("RELIANCE")
    assert quote.symbol == "RELIANCE"
    assert quote.ltp == candles[-1].close
    assert quote.bid < quote.ask

