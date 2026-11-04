"""Unit tests for Stock Scanner Engine."""

from trader.providers.synthetic_provider import SyntheticDataProvider
from trader.scanner.ranking import MarketScannerEngine


def test_market_scanner_engine_runs_all_scanners():
    provider = SyntheticDataProvider(seed=42)
    scanner = MarketScannerEngine(provider=provider, symbols=["RELIANCE", "TCS", "INFY", "SBIN"])

    results = scanner.run_full_scan()
    assert "top_gainers" in results
    assert "top_losers" in results
    assert "relative_volume" in results
    assert "momentum" in results
    assert "trend_strength" in results
    assert "volatility" in results
    assert "unusual_movement" in results

    # Verify candidate properties
    gainers = results["top_gainers"]
    assert len(gainers) > 0
    top = gainers[0]
    assert top.symbol in ["RELIANCE", "TCS", "INFY", "SBIN"]
    assert len(top.inclusion_reasons) > 0
    assert top.latest_price > 0.0
    assert "sma_20" in top.indicators
    assert "rsi_14" in top.indicators


def test_scanner_transparent_reasons():
    provider = SyntheticDataProvider(seed=55)
    scanner = MarketScannerEngine(provider=provider, symbols=["RELIANCE"])
    rvol_candidates = scanner.scan_relative_volume()

    assert len(rvol_candidates) == 1
    cand = rvol_candidates[0]
    # Check that reasons are transparent and not empty
    assert len(cand.inclusion_reasons) > 0 or len(cand.exclusion_reasons) > 0

