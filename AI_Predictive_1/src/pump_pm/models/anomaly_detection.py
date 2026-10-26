"""
anomaly_detection.py
--------------------
Unsupervised anomaly detection baseline using Scikit-Learn IsolationForest.
Detects multivariate statistical outliers across vibration and temperature channels.
"""

import os
import pickle
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURE_COLUMNS = [
    "P1-V", "P1-H", "P1-A", "P1-T",
    "P2-V", "P2-H", "P2-A", "P2-T",
    "P3-V", "P3-H", "P3-A", "P3-T",
    "P4-V", "P4-H", "P4-A", "P4-T"
]


class AnomalyDetector:
    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state
        )
        self.feature_columns = FEATURE_COLUMNS
        self.is_fitted = False
        self.baseline_stats: Dict[str, Dict[str, float]] = {}

    def fit(self, train_df: pd.DataFrame) -> "AnomalyDetector":
        """
        Fits IsolationForest on training telemetry feature matrix.
        Calculates baseline means and stds for feature contribution explanations.
        """
        # Ensure all feature columns exist and are numeric
        X = self._prepare_features(train_df)
        self.model.fit(X)
        self.is_fitted = True

        # Calculate baseline means and stds for XAI fallback
        for col in self.feature_columns:
            vals = X[col].dropna()
            self.baseline_stats[col] = {
                "mean": float(vals.mean()),
                "std": float(vals.std()) if vals.std() > 0 else 1.0
            }

        return self

    def predict_scores(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predicts anomaly scores and binary outlier indicators.
        Returns:
            scores: float array where more negative indicates higher abnormality
            is_anomaly: boolean array where True indicates anomaly
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector model must be fitted before predict_scores.")

        X = self._prepare_features(df)
        # decision_function: average anomaly score. Lower is more abnormal.
        decision_scores = self.model.decision_function(X)
        preds = self.model.predict(X)  # -1 for anomaly, 1 for inlier
        is_anomaly = (preds == -1)

        return decision_scores, is_anomaly

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df.copy()
        # Impute any remaining NaNs with column median for model stability
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0.0
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(X[col].median())
        return X[self.feature_columns]

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: str) -> "AnomalyDetector":
        with open(filepath, "rb") as f:
            return pickle.load(f)
