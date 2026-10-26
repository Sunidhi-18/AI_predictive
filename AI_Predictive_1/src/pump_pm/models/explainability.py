"""
explainability.py
-----------------
Explainable AI (XAI) engine providing feature attributions for detected anomalies.
Uses SHAP (SHapley Additive exPlanations) with robust statistical deviation fallback.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from .anomaly_detection import AnomalyDetector, FEATURE_COLUMNS


class ModelExplainer:
    def __init__(self, detector: AnomalyDetector):
        self.detector = detector
        self.shap_explainer = None
        self._init_shap()

    def _init_shap(self):
        try:
            import shap
            # For tree-based IsolationForest, TreeExplainer is ideal
            self.shap_explainer = shap.TreeExplainer(self.detector.model)
        except Exception as e:
            # SHAP unavailable or tree structure incompatible; graceful fallback
            self.shap_explainer = None

    def explain_instance(
        self,
        row: pd.Series,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Produces top-k feature contributions for a single telemetry record.
        Returns list of dicts with feature name, value, baseline mean, contribution score,
        and human-readable explanation.
        """
        # Prepare single row DataFrame
        single_df = pd.DataFrame([row])
        X = self.detector._prepare_features(single_df)

        attributions = []

        # Attempt SHAP explanation
        if self.shap_explainer is not None:
            try:
                shap_values = self.shap_explainer.shap_values(X)
                # For IsolationForest, shap_values is a 1D array of length n_features
                if isinstance(shap_values, list):
                    vals = shap_values[0][0]
                else:
                    vals = shap_values[0]

                for col, s_val in zip(FEATURE_COLUMNS, vals):
                    actual_val = float(X[col].iloc[0])
                    base_mean = self.detector.baseline_stats.get(col, {}).get("mean", 0.0)
                    attributions.append({
                        "feature": col,
                        "actual_value": round(actual_val, 2),
                        "baseline_mean": round(base_mean, 2),
                        "contribution_score": float(np.abs(s_val)),
                        "method": "SHAP_TreeExplainer",
                        "explanation": f"{col} value ({actual_val:.2f}) deviated from baseline ({base_mean:.2f}), contributing strongly to the anomaly score."
                    })
            except Exception:
                attributions = []

        # Fallback to Z-score deviation if SHAP was not initialized or encountered an error
        if not attributions:
            for col in FEATURE_COLUMNS:
                actual_val = float(X[col].iloc[0])
                stats = self.detector.baseline_stats.get(col, {"mean": 0.0, "std": 1.0})
                mean = stats["mean"]
                std = stats["std"] if stats["std"] > 0 else 1.0
                z_score = abs(actual_val - mean) / std

                attributions.append({
                    "feature": col,
                    "actual_value": round(actual_val, 2),
                    "baseline_mean": round(mean, 2),
                    "contribution_score": round(float(z_score), 3),
                    "method": "Normalized_Feature_Deviation",
                    "explanation": f"{col} is at {actual_val:.2f} ({z_score:.1f} standard deviations from baseline mean {mean:.2f})."
                })

        # Sort by contribution score descending
        attributions.sort(key=lambda x: x["contribution_score"], reverse=True)
        return attributions[:top_k]
