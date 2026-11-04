"""Unit tests for Deterministic Baseline Strategy."""

from datetime import datetime, timedelta
import pandas as pd
import pytz

from trader.domain.models import IST
from trader.strategies.baseline import BaselineSwingStrategy, SignalType


def build_mock_indicators_df(num_rows: int = 60, base_price: float = 1000.0) -> pd.DataFrame:
    rows = []
    base_dt = IST.localize(datetime(2026, 8, 1, 15, 30))
    for i in range(num_rows):
        dt = base_dt + timedelta(days=i)
        p = base_price + (i * 5.0) # steady uptrend
        rows.append({
            "symbol": "RELIANCE",
            "timestamp": dt,
            "open": p - 2.0,
            "high": p + 8.0,
            "low": p - 4.0,
            "close": p,
            "volume": 200000.0,
            "turnover": p * 200000.0,
            "turnover_sma_20": p * 200000.0,
            "sma_20": p - 10.0, # fast SMA below price
            "sma_50": p - 30.0, # slow SMA below fast SMA
            "rsi_14": 55.0, # sweet spot
            "atr_14": 20.0,
            "vol_sma_20": 150000.0,
        })
    return pd.DataFrame(rows)


def test_baseline_strategy_entry_signal():
    df = build_mock_indicators_df(65, 1500.0)
    # Configure row 64 (last row) so low tests near SMA20
    sma20 = df.iloc[-1]["sma_20"]
    df.loc[df.index[-1], "low"] = sma20 * 1.005 # touches near SMA20

    strategy = BaselineSwingStrategy()
    sig = strategy.evaluate_entry(df)

    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert sig.symbol == "RELIANCE"
    assert sig.suggested_stop_loss is not None
    assert sig.suggested_stop_loss < sig.reference_close
    assert sig.suggested_target is not None
    assert sig.suggested_target > sig.reference_close


def test_baseline_strategy_exits():
    strategy = BaselineSwingStrategy(max_holding_candles=10)
    df = build_mock_indicators_df(60, 2000.0)

    # 1. Stop loss exit
    df.loc[df.index[-1], "low"] = 1940.0
    sig_stop = strategy.evaluate_exit(df, entry_price=2000.0, stop_loss=1950.0, target=2100.0, holding_candles=3)
    assert sig_stop is not None
    assert sig_stop.signal_type == SignalType.SELL
    assert "Stop loss" in sig_stop.reason

    # 2. Target exit
    df.loc[df.index[-1], "high"] = 2120.0
    sig_target = strategy.evaluate_exit(df, entry_price=2000.0, stop_loss=1900.0, target=2100.0, holding_candles=3)
    assert sig_target is not None
    assert "target" in sig_target.reason.lower()

    # 3. Holding period exit
    df.loc[df.index[-1], "low"] = 1980.0
    df.loc[df.index[-1], "high"] = 2050.0
    sig_time = strategy.evaluate_exit(df, entry_price=2000.0, stop_loss=1900.0, target=2200.0, holding_candles=10)
    assert sig_time is not None
    assert "Max holding period" in sig_time.reason

