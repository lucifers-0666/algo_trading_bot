"""Forward-Return Labeling and Purging Engine.
Computes future horizon returns and enforces purge/embargo gaps to prevent label leakage.
"""

from typing import Tuple, List, Optional
import numpy as np
import pandas as pd


def generate_forward_labels(
    df: pd.DataFrame,
    horizon_bars: int = 5,
    return_threshold: float = 0.015, # 1.5% forward gain
) -> pd.DataFrame:
    """Computes future return labels.
    CRITICAL: The resulting 'label' column is strictly FUTURE information.
    It must ONLY be used as the target (y) during training/testing, NEVER as an input feature (X).
    """
    out = df.copy()
    close = out["close"]

    # Future return over horizon
    future_close = close.shift(-horizon_bars)
    forward_return = (future_close - close) / close

    out["forward_return"] = forward_return
    # Binary classification: 1 if return exceeds threshold, else 0
    out["label"] = (forward_return > return_threshold).astype(int)

    # The last `horizon_bars` rows cannot compute forward return without looking beyond the dataset
    out.iloc[-horizon_bars:, out.columns.get_loc("label")] = np.nan
    out.iloc[-horizon_bars:, out.columns.get_loc("forward_return")] = np.nan
    return out


def chronological_train_test_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    purge_gap_bars: int = 5,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits time-series chronologically with an embargo/purge gap
    to guarantee zero horizon overlap leakage between training and testing sets.
    """
    clean_df = df.dropna(subset=["label"]).sort_values("timestamp").reset_index(drop=True)
    n = len(clean_df)
    if n < 30:
        raise ValueError(f"Insufficient samples ({n}) for chronological split")

    train_end_idx = int(n * train_ratio)
    test_start_idx = train_end_idx + purge_gap_bars

    if test_start_idx >= n:
        raise ValueError("Purge gap leaves zero test samples. Provide more historical data or reduce horizon.")

    train_df = clean_df.iloc[:train_end_idx].copy()
    test_df = clean_df.iloc[test_start_idx:].copy()

    return train_df, test_df

