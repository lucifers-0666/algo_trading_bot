"""Technical Indicators Engine for Indian Equities.
Vectorized, mathematically verified calculations of SMA, RSI, ATR, RVOL, and price momentum.
Strictly guards against look-ahead bias by calculating strictly on past and current bar data.
"""

from typing import List, Optional
import numpy as np
import pandas as pd

from trader.domain.models import Candle


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculates Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index using Wilder's exponential smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -1.0 * delta.clip(upper=0.0)

    # Wilder's smoothing alpha = 1 / period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Where loss was 0, RSI is 100; where gain was 0, RSI is 0
    rsi = rsi.fillna(100.0 * (avg_gain > 0))
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def calculate_rvol(volume: pd.Series, period: int = 20) -> pd.Series:
    """Calculates Relative Volume: current volume divided by 20-period volume SMA."""
    vol_sma = calculate_sma(volume, period)
    return volume / vol_sma.replace(0.0, np.nan)


def candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    """Converts a list of Candles into a sorted Pandas DataFrame."""
    if not candles:
        return pd.DataFrame()

    records = [
        {
            "symbol": c.symbol,
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "turnover": c.turnover or (c.close * c.volume),
            "source": c.source.value,
        }
        for c in candles
    ]
    df = pd.DataFrame.from_records(records)
    df = df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)
    return df


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Computes full suite of canonical indicators on a symbol DataFrame."""
    if df.empty or len(df) < 5:
        return df

    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"]

    # Moving averages
    out["sma_20"] = calculate_sma(close, 20)
    out["sma_50"] = calculate_sma(close, 50)
    out["sma_200"] = calculate_sma(close, 200)

    # Momentum and Oscillators
    out["rsi_14"] = calculate_rsi(close, 14)
    out["atr_14"] = calculate_atr(high, low, close, 14)
    out["atr_pct"] = out["atr_14"] / close

    # Volume and Liquidity
    out["vol_sma_20"] = calculate_sma(volume, 20)
    out["rvol"] = calculate_rvol(volume, 20)
    out["turnover_sma_20"] = calculate_sma(out["turnover"], 20)

    # Multi-period returns
    out["pct_change_1d"] = close.pct_change(1)
    out["pct_change_5d"] = close.pct_change(5)
    out["pct_change_20d"] = close.pct_change(20)

    # Trend distances
    out["dist_sma_20"] = (close - out["sma_20"]) / out["sma_20"]
    out["dist_sma_50"] = (close - out["sma_50"]) / out["sma_50"]

    return out
