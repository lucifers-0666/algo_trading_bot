"""Feature Generation & Dataset Builder for Machine Learning.
Produces stationary, normalized technical features calculated strictly from past/current bar data.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd

from trader.domain.models import Candle
from trader.features.technical import (
    candles_to_dataframe,
    calculate_sma,
    calculate_rsi,
    calculate_atr,
    calculate_rvol,
)
from trader.ml.labels import generate_forward_labels

CANONICAL_FEATURE_COLUMNS = [
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "dist_sma20",
    "dist_sma50",
    "sma20_slope_3d",
    "rsi_14",
    "rsi_delta_3d",
    "atr_pct",
    "spread_pct",
    "rvol",
    "vol_trend_5d",
]


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes pure leak-free feature vectors for each row in the DataFrame."""
    if len(df) < 55:
        return pd.DataFrame()

    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"]

    # 1. Multi-period past returns
    out["ret_1d"] = close.pct_change(1)
    out["ret_3d"] = close.pct_change(3)
    out["ret_5d"] = close.pct_change(5)
    out["ret_10d"] = close.pct_change(10)
    out["ret_20d"] = close.pct_change(20)

    # 2. Moving average distances and slopes
    sma20 = calculate_sma(close, 20)
    sma50 = calculate_sma(close, 50)
    out["dist_sma20"] = (close - sma20) / sma20
    out["dist_sma50"] = (close - sma50) / sma50
    out["sma20_slope_3d"] = sma20.pct_change(3)

    # 3. Oscillators
    rsi14 = calculate_rsi(close, 14)
    out["rsi_14"] = rsi14 / 100.0 # scale to [0, 1]
    out["rsi_delta_3d"] = out["rsi_14"].diff(3)

    # 4. Volatility & Spreads
    atr14 = calculate_atr(high, low, close, 14)
    out["atr_pct"] = atr14 / close
    out["spread_pct"] = (high - low) / close

    # 5. Volume dynamics
    vol_sma20 = calculate_sma(volume, 20)
    out["rvol"] = calculate_rvol(volume, 20)
    out["vol_trend_5d"] = (volume - vol_sma20) / vol_sma20.replace(0.0, np.nan)

    return out


def prepare_ml_dataset(
    candles: List[Candle],
    horizon_bars: int = 5,
    return_threshold: float = 0.015,
) -> Tuple[pd.DataFrame, List[str]]:
    """Builds a complete ML-ready dataset with features and target labels."""
    df_raw = candles_to_dataframe(candles)
    if len(df_raw) < 60:
        return pd.DataFrame(), CANONICAL_FEATURE_COLUMNS

    df_feat = extract_features(df_raw)
    df_labeled = generate_forward_labels(
        df_feat,
        horizon_bars=horizon_bars,
        return_threshold=return_threshold,
    )

    # Drop warm-up NaNs in features
    clean_df = df_labeled.dropna(subset=CANONICAL_FEATURE_COLUMNS).copy()
    clean_df = clean_df.reset_index(drop=True)
    return clean_df, CANONICAL_FEATURE_COLUMNS
