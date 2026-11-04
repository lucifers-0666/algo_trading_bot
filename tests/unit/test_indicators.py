"""Unit tests for Technical Indicators."""

import pandas as pd
import numpy as np
import pytest

from trader.features.technical import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_rvol,
    compute_all_indicators,
    candles_to_dataframe,
)
from trader.data.synthetic import generate_synthetic_candles


def test_sma_and_ema_calculation():
    s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma3 = calculate_sma(s, 3)
    assert np.isnan(sma3.iloc[0])
    assert np.isnan(sma3.iloc[1])
    assert sma3.iloc[2] == 20.0
    assert sma3.iloc[4] == 40.0

    ema3 = calculate_ema(s, 3)
    assert len(ema3) == 5
    assert ema3.iloc[-1] > ema3.iloc[0]


def test_rsi_bounds():
    # Constant uptrend -> RSI should be high
    uptrend = pd.Series([100 + i * 2 for i in range(30)], dtype=float)
    rsi_up = calculate_rsi(uptrend, 14)
    assert rsi_up.iloc[-1] > 90.0

    # Constant downtrend -> RSI should be low
    downtrend = pd.Series([200 - i * 2 for i in range(30)], dtype=float)
    rsi_down = calculate_rsi(downtrend, 14)
    assert rsi_down.iloc[-1] < 10.0


def test_compute_all_indicators_on_synthetic():
    candles = generate_synthetic_candles("RELIANCE", num_days=100, seed=42)
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)

    assert "sma_20" in df_ind.columns
    assert "sma_50" in df_ind.columns
    assert "rsi_14" in df_ind.columns
    assert "atr_14" in df_ind.columns
    assert "rvol" in df_ind.columns
    assert "pct_change_1d" in df_ind.columns

    # Verify no lookahead in sma_20: first 19 rows must be NaN
    assert df_ind["sma_20"].iloc[:19].isna().all()
    assert not pd.isna(df_ind["sma_20"].iloc[19])

