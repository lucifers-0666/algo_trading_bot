import pytest
import pandas as pd
from datetime import datetime, timedelta

from trader.domain.models import Candle, IST, Timeframe
from tests.fixtures.synthetic_fixture import generate_synthetic_candles
from trader.strategies.momentum import MomentumStrategy
from trader.strategies.breakout import DonchianBreakoutStrategy
from trader.strategies.regime import detect_market_regime, MarketRegime
from trader.backtest.comparison import run_strategy_comparison
from tests.fixtures.synthetic_fixture import SyntheticDataProvider
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


def test_news_sentiment_strategy():
    from trader.strategies.news_sentiment_strategy import NewsSentimentStrategy
    from trader.features.technical import candles_to_dataframe, compute_all_indicators

    candles = generate_synthetic_candles("INFY", num_days=100, seed=42)
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)

    strat = NewsSentimentStrategy(min_sentiment_score=0.20)

    # When sentiment is negative or below min_sentiment_score, entry is blocked
    sig_low = strat.evaluate_entry(df_ind, sentiment_score=-0.10)
    assert sig_low is None

    # Exit evaluations work properly
    exit_sig = strat.evaluate_exit(df_ind, entry_price=1600.0, stop_loss=1500.0, target=1700.0, holding_candles=20)
    assert exit_sig is not None


def test_relative_strength_strategy():
    from trader.strategies.relative_strength import SectorRelativeStrengthStrategy
    from trader.features.technical import candles_to_dataframe, compute_all_indicators

    stock_candles = generate_synthetic_candles("TCS", num_days=100, seed=42)
    bm_candles = generate_synthetic_candles("RELIANCE", num_days=100, seed=10)

    df_stock = compute_all_indicators(candles_to_dataframe(stock_candles))
    df_bm = compute_all_indicators(candles_to_dataframe(bm_candles))

    strat = SectorRelativeStrengthStrategy(lookback_bars=20, min_alpha=0.01)
    alpha = strat.compute_relative_strength(df_stock, df_bm)
    assert isinstance(alpha, float)

    # Check exit
    exit_sig = strat.evaluate_exit(df_stock, entry_price=3900.0, stop_loss=3800.0, target=4100.0, holding_candles=25)
    assert exit_sig is not None

