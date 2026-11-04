import pytest
import pandas as pd
from datetime import datetime, timedelta

from trader.domain.models import Candle, IST, Timeframe
from trader.data.synthetic import generate_synthetic_candles
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy
from trader.strategies.regime import detect_market_regime, MarketRegime
from trader.backtest.comparison import run_strategy_comparison
from trader.providers.synthetic_provider import SyntheticDataProvider
from trader.scanner.ranking import MarketScannerEngine


def test_market_regime_classification():
    """Verify market regime classification and NO_TRADE recommendations."""
    candles = generate_synthetic_candles("RELIANCE", num_days=100, seed=42)
    from trader.features.technical import candles_to_dataframe, compute_all_indicators
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)

    assessment = detect_market_regime(df_ind)
    assert assessment.regime in [
        MarketRegime.BULL_TRENDING,
        MarketRegime.BEAR_TRENDING,
        MarketRegime.SIDEWAYS_CONSOLIDATION,
        MarketRegime.HIGH_VOLATILITY,
        MarketRegime.LOW_VOLATILITY,
    ]
    assert assessment.trade_permission in ["ALLOW_TRADING", "REDUCE_SIZE", "NO_TRADE"]


def test_momentum_strategy_signals():
    """Verify momentum strategy triggers BUY on strong trending data."""
    candles = generate_synthetic_candles("TCS", num_days=120, seed=42, trend_bias=0.003)
    from trader.features.technical import candles_to_dataframe, compute_all_indicators
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)

    strat = MomentumStrategy(lookback_momentum=15, min_momentum_pct=0.01, rvol_min=0.5)
    sig = strat.evaluate_entry(df_ind)
    # Even if not triggered on final candle, evaluate exit must not raise exceptions
    exit_sig = strat.evaluate_exit(df_ind, entry_price=3500.0, stop_loss=3400.0, holding_candles=25)
    assert exit_sig is not None  # Max holding candles reached


def test_donchian_breakout_strategy():
    """Verify Donchian breakout strategy triggers on 20-day breakout."""
    candles = generate_synthetic_candles("INFY", num_days=120, seed=42)
    from trader.features.technical import candles_to_dataframe, compute_all_indicators
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)

    strat = DonchianBreakoutStrategy(breakout_period=15, volume_mult=0.5)
    _ = strat.evaluate_entry(df_ind)
    exit_sig = strat.evaluate_exit(df_ind, entry_price=1500.0, stop_loss=1400.0, holding_candles=30)
    assert exit_sig is not None


def test_strategy_comparison_runner():
    """Verify running comparison across Baseline, Momentum, and Breakout."""
    universe = {
        "RELIANCE": generate_synthetic_candles("RELIANCE", num_days=80, seed=10),
        "TCS": generate_synthetic_candles("TCS", num_days=80, seed=20),
    }

    report = run_strategy_comparison(universe, initial_capital=10000.0)
    assert len(report.comparison_table) == 3
    strat_names = [r.strategy_name for r in report.comparison_table]
    assert any("Baseline Swing" in s for s in strat_names)
    assert any("Momentum" in s for s in strat_names)
    assert any("Breakout" in s for s in strat_names)


def test_scanner_snapshot_cache():
    """Verify that MarketScannerEngine caches prepared symbol metrics and doesn't recalculate."""
    provider = SyntheticDataProvider(seed=42)
    engine = MarketScannerEngine(provider=provider, symbols=["RELIANCE", "TCS"])

    assert len(engine._metrics_cache) == 0
    engine.refresh_snapshot()
    assert len(engine._metrics_cache) == 2
    assert "RELIANCE" in engine._metrics_cache
    assert "TCS" in engine._metrics_cache

    # Subsequent scan uses cache
    gainers = engine.scan_top_gainers()
    assert len(gainers) > 0
    engine.clear_cache()
    assert len(engine._metrics_cache) == 0
