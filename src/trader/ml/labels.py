"""Forward-Return Labeling and Purging Engine.
Computes future horizon returns and enforces purge/embargo gaps to prevent label leakage.
Supports single chronological train/test splits and rolling/expanding walk-forward cross-validation.
"""

from typing import Tuple, List, Optional
import numpy as np
import pandas as pd


def generate_forward_labels(
    df: pd.DataFrame,
    horizon_bars: int = 5,
    return_threshold: float = 0.015,  # 1.5% forward gain
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


def generate_walk_forward_splits(
    df: pd.DataFrame,
    n_splits: int = 3,
    train_bars: int = 50,
    test_bars: int = 15,
    purge_gap_bars: int = 5,
    expanding: bool = True,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Generates strictly chronological walk-forward train/test windows with purge gaps."""
    clean_df = df.dropna(subset=["label"]).sort_values("timestamp").reset_index(drop=True)
    n = len(clean_df)
    splits = []

    step = (n - train_bars - purge_gap_bars) // n_splits
    if step <= 0:
        train_df, test_df = chronological_train_test_split(clean_df, train_ratio=0.7, purge_gap_bars=purge_gap_bars)
        return [(train_df, test_df)]

    for i in range(n_splits):
        if expanding:
            train_start = 0
            train_end = train_bars + (i * step)
        else:
            train_start = i * step
            train_end = train_start + train_bars

        test_start = train_end + purge_gap_bars
        test_end = min(n, test_start + test_bars)

        if test_start < n:
            t_train = clean_df.iloc[train_start:train_end].copy()
            t_test = clean_df.iloc[test_start:test_end].copy()
            if len(t_train) >= 20 and len(t_test) >= 5:
                splits.append((t_train, t_test))

    if not splits:
        t_train, t_test = chronological_train_test_split(clean_df, train_ratio=0.7, purge_gap_bars=purge_gap_bars)
        splits.append((t_train, t_test))

    return splits
