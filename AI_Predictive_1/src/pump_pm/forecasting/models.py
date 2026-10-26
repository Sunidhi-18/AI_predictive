"""
models.py
---------
ML forecasting models for next-day sensor predictions:
1. SensorForecaster (RandomForestRegressor multi-output)
2. PersistenceBaseline (y_hat = y_t)
3. RidgeRegressionBaseline (L2 regularized linear model)

Evaluates MAE, RMSE, and R2 on unseen test data without data leakage.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import json
import pickle
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score



def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, target_names: List[str]) -> Dict[str, Any]:
    """
    Computes overall and per-channel MAE, RMSE, and R2 metrics.
    """
    overall_mae = float(mean_absolute_error(y_true, y_pred))
    overall_rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    overall_r2 = float(r2_score(y_true, y_pred))

    per_channel = {}
    for i, name in enumerate(target_names):
        true_col = y_true[:, i]
        pred_col = y_pred[:, i]
        c_mae = float(mean_absolute_error(true_col, pred_col))
        c_rmse = float(np.sqrt(mean_squared_error(true_col, pred_col)))
        c_r2 = float(r2_score(true_col, pred_col))
        per_channel[name] = {
            "mae": round(c_mae, 4),
            "rmse": round(c_rmse, 4),
            "r2": round(c_r2, 4)
        }

    return {
        "overall_mae": round(overall_mae, 4),
        "overall_rmse": round(overall_rmse, 4),
        "overall_r2": round(overall_r2, 4),
        "per_channel": per_channel
    }


class PersistenceBaseline:
    """
    Persistence forecasting baseline:
    Predicts tomorrow's sensor readings using today's current sensor readings:
    y_hat(t+1) = y(t)
    """
    def __init__(self, target_names: List[str]):
        self.target_names = target_names
        # Clean channel names: target_P1-V -> P1-V_curr
        self.current_cols = [name.replace("target_", "") + "_curr" for name in target_names]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Extracts current reading columns from feature matrix X.
        """
        pred_cols = []
        for c in self.current_cols:
            if c in X.columns:
                pred_cols.append(X[c].values)
            else:
                # Fallback to bare channel name if _curr not found
                bare_ch = c.replace("_curr", "")
                if bare_ch in X.columns:
                    pred_cols.append(X[bare_ch].values)
                else:
                    raise KeyError(f"Neither '{c}' nor '{bare_ch}' found in feature matrix.")

        return np.column_stack(pred_cols)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.DataFrame) -> Dict[str, Any]:
        y_pred = self.predict(X_test)
        y_true = y_test.values
        metrics = calculate_metrics(y_true, y_pred, self.target_names)
        metrics["model_name"] = "Persistence Baseline (Today = Tomorrow)"
        return metrics


class RidgeRegressionBaseline:
    """
    Linear Ridge regression baseline for multi-output forecasting comparison.
    """
    def __init__(self, target_names: List[str], alpha: float = 1.0):
        self.target_names = target_names
        self.alpha = alpha
        self.model = Ridge(alpha=alpha, random_state=42)

    def fit(self, X_train: pd.DataFrame, y_train: pd.DataFrame):
        self.model.fit(X_train.values, y_train.values)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X.values)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.DataFrame) -> Dict[str, Any]:
        y_pred = self.predict(X_test)
        y_true = y_test.values
        metrics = calculate_metrics(y_true, y_pred, self.target_names)
        metrics["model_name"] = "Ridge Linear Regression Baseline"
        return metrics


class SensorForecaster:
    """
    Multi-Output Random Forest Regressor for predicting next-day sensor telemetry.
    """
    def __init__(
        self,
        target_names: Optional[List[str]] = None,
        feature_names: Optional[List[str]] = None,
        n_estimators: int = 100,
        max_depth: Optional[int] = 12,
        min_samples_split: int = 4,
        random_state: int = 42,
        n_jobs: int = -1
    ):
        self.target_names = target_names or []
        self.feature_names = feature_names or []
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.random_state = random_state
        self.n_jobs = n_jobs

        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )
        self.is_fitted = False

    def fit(self, X_train: pd.DataFrame, y_train: pd.DataFrame):
        self.feature_names = list(X_train.columns)
        self.target_names = list(y_train.columns)
        self.model.fit(X_train.values, y_train.values)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("SensorForecaster is not fitted yet.")
        # Ensure correct column alignment
        X_aligned = X[self.feature_names] if self.feature_names else X
        return self.model.predict(X_aligned.values)

    def predict_dataframe(self, X: pd.DataFrame) -> pd.DataFrame:
        preds = self.predict(X)
        clean_target_cols = [name.replace("target_", "pred_") for name in self.target_names]
        return pd.DataFrame(preds, columns=clean_target_cols, index=X.index)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.DataFrame) -> Dict[str, Any]:
        y_pred = self.predict(X_test)
        y_true = y_test.values
        metrics = calculate_metrics(y_true, y_pred, self.target_names)
        metrics["model_name"] = "Random Forest Regressor (Multi-Output)"
        metrics["hyperparameters"] = {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "random_state": self.random_state
        }
        return metrics

    def save(self, model_path: str, config_path: Optional[str] = None):
        """
        Persists the trained model and feature metadata.
        """
        os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)

        if config_path:
            os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
            config_data = {
                "model_type": "RandomForestRegressor",
                "feature_names": self.feature_names,
                "target_names": self.target_names,
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "min_samples_split": self.min_samples_split,
                "random_state": self.random_state,
                "saved_at": datetime.now().isoformat()
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)

    @classmethod
    def load(cls, model_path: str, config_path: Optional[str] = None) -> "SensorForecaster":
        """
        Loads a trained model and configuration.
        """
        feature_names = []
        target_names = []
        hp = {}

        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                config_data = json.load(f)
                feature_names = config_data.get("feature_names", [])
                target_names = config_data.get("target_names", [])
                hp = {
                    "n_estimators": config_data.get("n_estimators", 100),
                    "max_depth": config_data.get("max_depth", 12),
                    "min_samples_split": config_data.get("min_samples_split", 4),
                    "random_state": config_data.get("random_state", 42)
                }

        forecaster = cls(feature_names=feature_names, target_names=target_names, **hp)

        with open(model_path, "rb") as f:
            forecaster.model = pickle.load(f)
            forecaster.is_fitted = True

        return forecaster
