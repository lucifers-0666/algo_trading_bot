"""Unit tests for Machine Learning Pipeline."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from trader.data.synthetic import generate_synthetic_candles
from trader.ml.labels import generate_forward_labels, chronological_train_test_split
from trader.ml.dataset import extract_features, prepare_ml_dataset, CANONICAL_FEATURE_COLUMNS
from trader.ml.train import train_model
from trader.ml.evaluate import evaluate_model_performance, rank_symbols_by_ml_score


def test_forward_labels_no_leakage():
    candles = generate_synthetic_candles("RELIANCE", num_days=50, seed=42)
    from trader.features.technical import candles_to_dataframe
    df = candles_to_dataframe(candles)

    horizon = 5
    labeled_df = generate_forward_labels(df, horizon_bars=horizon, return_threshold=0.01)

    assert "forward_return" in labeled_df.columns
    assert "label" in labeled_df.columns

    # The last `horizon` rows MUST be NaN to guarantee no future edge leakage
    assert labeled_df["label"].iloc[-horizon:].isna().all()
    assert labeled_df["forward_return"].iloc[-horizon:].isna().all()

    # The row before that must NOT be NaN
    assert not pd.isna(labeled_df["label"].iloc[-horizon - 1])


def test_chronological_split_with_purge_gap():
    candles = generate_synthetic_candles("TCS", num_days=100, seed=99)
    dataset, _ = prepare_ml_dataset(candles, horizon_bars=5)

    purge_gap = 5
    train_df, test_df = chronological_train_test_split(dataset, train_ratio=0.70, purge_gap_bars=purge_gap)

    # 1. Monotonic chronological separation: Train max date < Test min date
    assert train_df["timestamp"].max() < test_df["timestamp"].min()

    # 2. Embargo gap between index boundaries
    train_end_idx = train_df.index[-1]
    test_start_idx = test_df.index[0]
    assert test_start_idx - train_end_idx >= purge_gap


def test_train_and_evaluate_model():
    candles = generate_synthetic_candles("INFY", num_days=150, seed=123)
    dataset, feats = prepare_ml_dataset(candles, horizon_bars=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        model, meta = train_model(
            df=dataset,
            feature_columns=feats,
            model_type="random_forest",
            train_ratio=0.70,
            purge_gap_bars=5,
            save_dir=tmpdir,
        )

        assert meta.model_id.startswith("model_random_forest_")
        assert Path(meta.artifact_path).exists()
        assert "accuracy" in meta.metrics
        assert "roc_auc" in meta.metrics

        # Evaluate on test split
        _, test_df = chronological_train_test_split(dataset, train_ratio=0.70, purge_gap_bars=5)
        eval_res = evaluate_model_performance(model, test_df, feats)
        assert "confusion_matrix" in eval_res
        assert "cumulative_ml_return_pct" in eval_res

        # Rank candidates
        sample_row = test_df.iloc[-1]
        rankings = rank_symbols_by_ml_score(model, {"INFY": sample_row}, feats)
        assert len(rankings) == 1
        assert rankings[0]["symbol"] == "INFY"
        assert 0.0 <= rankings[0]["ml_probability"] <= 1.0

