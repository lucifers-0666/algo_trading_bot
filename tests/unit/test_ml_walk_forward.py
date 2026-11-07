import pytest
import pandas as pd
from datetime import datetime, timedelta

from tests.fixtures.synthetic_fixture import generate_synthetic_candles
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.ml.dataset import extract_features
from trader.ml.labels import generate_forward_labels, generate_walk_forward_splits
from trader.ml.train import train_model
from trader.ml.evaluate import evaluate_model_performance


@pytest.fixture
def sample_feature_df():
    candles = generate_synthetic_candles("RELIANCE", num_days=150, seed=42)
    df = candles_to_dataframe(candles)
    df_ind = compute_all_indicators(df)
    feat_df = extract_features(df_ind)
    labeled_df = generate_forward_labels(feat_df, horizon_bars=5)
    return labeled_df


def test_walk_forward_splits_no_overlap(sample_feature_df):
    """Verify walk-forward splits maintain purge gaps between train and test."""
    splits = generate_walk_forward_splits(
        sample_feature_df,
        n_splits=3,
        train_bars=40,
        test_bars=15,
        purge_gap_bars=5,
    )

    assert len(splits) >= 2
    for train_df, test_df in splits:
        train_max_ts = train_df["timestamp"].max()
        test_min_ts = test_df["timestamp"].min()
        # Test start must be strictly greater than train end
        assert test_min_ts > train_max_ts
        # No overlapping rows
        assert len(set(train_df.index).intersection(set(test_df.index))) == 0


def test_reject_unsupported_model_type(sample_feature_df):
    """Verify train_model raises ValueError when given an unsupported model name."""
    with pytest.raises(ValueError, match="Unsupported model_type: 'deep_neural_net'"):
        train_model(sample_feature_df, model_type="deep_neural_net")


def test_train_gradient_boosting_model(sample_feature_df, tmp_path):
    """Verify training Gradient Boosting model with valid metrics."""
    save_dir = tmp_path / "models"
    model, metadata = train_model(
        sample_feature_df,
        model_type="gradient_boosting",
        save_dir=str(save_dir),
    )

    assert metadata.model_type == "gradient_boosting"
    assert "accuracy" in metadata.metrics
    assert "precision_at_k" in metadata.metrics
    assert "brier_score" in metadata.metrics


def test_model_evaluation_metrics_and_calibration(sample_feature_df, tmp_path):
    """Verify evaluate_model_performance computes brier score, calibration and precision@k."""
    save_dir = tmp_path / "models"
    model, metadata = train_model(
        sample_feature_df,
        model_type="random_forest",
        save_dir=str(save_dir),
    )

    clean_test = sample_feature_df.dropna(subset=["label"]).iloc[-25:]
    eval_res = evaluate_model_performance(model, clean_test)

    assert "confusion_matrix" in eval_res
    assert "brier_score" in eval_res
    assert "precision_at_20pct" in eval_res
    assert "cumulative_ml_return_pct" in eval_res
