"""Model Evaluation & Benchmark Comparison Engine.
Evaluates out-of-sample predictions, ranks candidates by model probability,
and computes benchmark comparison against deterministic and buy-and-hold baselines.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from trader.ml.dataset import CANONICAL_FEATURE_COLUMNS


def evaluate_model_performance(
    model: Any,
    test_df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generates classification report and confusion matrix on holdout set."""
    feats = feature_columns or CANONICAL_FEATURE_COLUMNS
    X_test = test_df[feats].values
    y_test = test_df["label"].values.astype(int)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    cm = confusion_matrix(y_test, y_pred).tolist()
    cr = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Strategy simulation: Buy when probability > 0.55
    long_signals = (y_prob > 0.55)
    fwd_returns = test_df["forward_return"].values

    ml_returns = np.where(long_signals, fwd_returns, 0.0)
    bh_returns = fwd_returns

    cum_ml = float(np.prod(1.0 + ml_returns) - 1.0)
    cum_bh = float(np.prod(1.0 + bh_returns) - 1.0)

    return {
        "confusion_matrix": cm,
        "classification_report": cr,
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
