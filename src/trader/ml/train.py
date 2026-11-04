"""Model Training and Versioning Pipeline.
Trains scikit-learn models (Random Forest, Logistic Regression) using chronological splits with purge gaps.
Persists trained artifacts and maintains a model registry.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import json
import joblib
import pandas as pd
from pydantic import BaseModel
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
    brier_score_loss,
)

from trader.domain.models import IST
from trader.ml.dataset import CANONICAL_FEATURE_COLUMNS
from trader.ml.labels import chronological_train_test_split


class ModelMetadata(BaseModel):
    model_id: str
    model_type: str
    trained_at: str
    feature_names: List[str]
    train_samples: int
    test_samples: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    metrics: Dict[str, float]
    artifact_path: str


def train_model(
    df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
    model_type: str = "random_forest",
    train_ratio: float = 0.70,
    purge_gap_bars: int = 5,
    save_dir: str = "models/saved",
) -> Tuple[Any, ModelMetadata]:
    """Trains a classifier on chronological splits and persists the model artifact."""
    feats = feature_columns or CANONICAL_FEATURE_COLUMNS

    # Chronological split with purge gap
    train_df, test_df = chronological_train_test_split(
        df,
        train_ratio=train_ratio,
        purge_gap_bars=purge_gap_bars,
    )

    X_train = train_df[feats].values
    y_train = train_df["label"].values.astype(int)

    X_test = test_df[feats].values
    y_test = test_df["label"].values.astype(int)

    # Instantiate model pipeline
    if model_type.lower() == "logistic_regression":
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")),
        ])
    else: # Default Random Forest
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                min_samples_leaf=5,
                random_state=42,
                class_weight="balanced",
            )),
        ])

    model.fit(X_train, y_train)

    # Out-of-sample predictions
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    # Compute evaluation metrics
    acc = round(float(accuracy_score(y_test, y_pred)), 4)
    prec = round(float(precision_score(y_test, y_pred, zero_division=0)), 4)
    rec = round(float(recall_score(y_test, y_pred, zero_division=0)), 4)
    try:
        auc = round(float(roc_auc_score(y_test, y_prob)), 4)
    except Exception:
        auc = 0.50
    brier = round(float(brier_score_loss(y_test, y_prob)), 4)

    eval_metrics = {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "roc_auc": auc,
        "brier_score": brier,
    }

    # Model ID and persistence
    now_ist = datetime.now(IST)
    timestamp_str = now_ist.strftime("%Y%m%d_%H%M%S")
    model_id = f"model_{model_type.lower()}_{timestamp_str}"

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    artifact_file = save_path / f"{model_id}.joblib"
    joblib.dump(model, artifact_file)

    train_start_str = str(train_df["timestamp"].iloc[0])
    train_end_str = str(train_df["timestamp"].iloc[-1])
    test_start_str = str(test_df["timestamp"].iloc[0])
    test_end_str = str(test_df["timestamp"].iloc[-1])

    metadata = ModelMetadata(
        model_id=model_id,
        model_type=model_type,
        trained_at=now_ist.isoformat(),
        feature_names=feats,
        train_samples=len(train_df),
        test_samples=len(test_df),
        train_start=train_start_str,
        train_end=train_end_str,
        test_start=test_start_str,
        test_end=test_end_str,
        metrics=eval_metrics,
        artifact_path=str(artifact_file),
    )

    # Update registry
    registry_file = save_path.parent / "registry.json"
    registry_data = []
    if registry_file.exists():
        try:
            registry_data = json.loads(registry_file.read_text(encoding="utf-8"))
        except Exception:
            registry_data = []
    registry_data.append(metadata.model_dump())
    registry_file.write_text(json.dumps(registry_data, indent=2), encoding="utf-8")

    return model, metadata
