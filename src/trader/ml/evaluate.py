"""Model Evaluation & Benchmark Comparison Engine.
Evaluates out-of-sample predictions, ranks candidates by model probability,
and computes benchmark comparison without overlapping label compounding.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, brier_score_loss, average_precision_score
from sklearn.calibration import calibration_curve

from trader.ml.dataset import CANONICAL_FEATURE_COLUMNS


def evaluate_model_performance(
    model: Any,
    test_df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
    horizon_bars: int = 5,
) -> Dict[str, Any]:
    """Generates classification report, calibration stats, and non-overlapping simulation."""
    feats = feature_columns or CANONICAL_FEATURE_COLUMNS
    X_test = test_df[feats].values
    y_test = test_df["label"].values.astype(int)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    cm = confusion_matrix(y_test, y_pred).tolist()
    cr = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Strategy simulation on NON-OVERLAPPING steps with statutory cost drag (~0.35%)
    long_signals = (y_prob > 0.55)
    fwd_returns = test_df["forward_return"].values

    step = max(1, horizon_bars)
    sampled_indices = list(range(0, len(test_df), step))
    sampled_signals = long_signals[sampled_indices]
    sampled_returns = fwd_returns[sampled_indices]

    cost_drag = 0.0035  # ~0.35% round-trip delivery taxes & brokerage
    ml_discrete_returns = [
        float(ret - cost_drag) if sig else 0.0
        for sig, ret in zip(sampled_signals, sampled_returns)
    ]
    cum_ml = float(np.prod([1.0 + r for r in ml_discrete_returns]) - 1.0) if ml_discrete_returns else 0.0
    cum_bh = float(np.prod([1.0 + float(r) for r in sampled_returns]) - 1.0) if len(sampled_returns) > 0 else 0.0

    # Calibration error & Brier score
    brier = round(float(brier_score_loss(y_test, y_prob)), 4)
    try:
        prob_true, prob_pred = calibration_curve(y_test, y_prob, n_bins=5)
        cal_err = round(float(np.mean(np.abs(prob_true - prob_pred))), 4) if len(prob_true) > 0 else 0.0
    except Exception:
        cal_err = 0.0

    # Precision@K (Top 20% probabilities)
    k_count = max(1, int(len(y_prob) * 0.20))
    top_k_indices = np.argsort(y_prob)[-k_count:]
    p_at_k = round(float(np.mean(y_test[top_k_indices])), 4)

    return {
        "confusion_matrix": cm,
        "classification_report": cr,
        "brier_score": brier,
        "calibration_error": cal_err,
        "precision_at_20pct": p_at_k,
        "cumulative_ml_return_pct": round(cum_ml * 100.0, 2),
        "cumulative_buy_and_hold_pct": round(cum_bh * 100.0, 2),
        "trade_opportunities_count": int(np.sum(long_signals)),
        "total_test_samples": len(test_df),
    }


def rank_symbols_by_ml_score(
    model: Any,
    symbol_feature_rows: Dict[str, pd.Series],
    feature_columns: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Ranks candidate symbols by model upward probability for the next horizon."""
    feats = feature_columns or CANONICAL_FEATURE_COLUMNS
    rankings = []

    for sym, row in symbol_feature_rows.items():
        if all(f in row.index and pd.notna(row[f]) for f in feats):
            X = np.array([row[f] for f in feats]).reshape(1, -1)
            prob_up = float(model.predict_proba(X)[0, 1]) if hasattr(model, "predict_proba") else 0.5
            rankings.append({
                "symbol": sym,
                "ml_probability": round(prob_up, 4),
                "is_ml_approved": prob_up >= 0.55,
                "latest_price": float(row.get("close", 0.0)),
            })

    rankings.sort(key=lambda r: r["ml_probability"], reverse=True)
    return rankings
