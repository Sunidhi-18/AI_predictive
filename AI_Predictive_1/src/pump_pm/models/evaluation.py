"""
evaluation.py
-------------
Rigorous model evaluation using machine-wise holdout splits to prevent temporal leakage.
Calculates precision, recall, F1, confusion matrix, and exports evaluation summaries.
"""

import os
import json
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

from .anomaly_detection import AnomalyDetector


def evaluate_anomaly_detector_holdout(
    telemetry_path: str,
    events_metadata_path: str,
    output_dir: str = "outputs/evaluation"
) -> Dict[str, Any]:
    """
    Evaluates AnomalyDetector using Machine-Wise Holdout:
    - Train split: Machines M1201 through M1214 (Baseline & first wave faults)
    - Test holdout: Machines M1215 through M1220 (Unseen machines)
    """
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(telemetry_path):
        raise FileNotFoundError(f"Telemetry dataset not found at {telemetry_path}")
    if not os.path.exists(events_metadata_path):
        raise FileNotFoundError(f"Events metadata not found at {events_metadata_path}")

    df_telemetry = pd.read_csv(telemetry_path)
    df_events = pd.read_csv(events_metadata_path)

    # Construct Ground Truth Labels from documented fault event windows
    df_telemetry["is_ground_truth_fault"] = False
    for _, ev in df_events.iterrows():
        m_id = ev["machine_id"]
        start_d = str(ev["start_date"])
        end_d = str(ev["end_date"])
        mask = (df_telemetry["Machine_number"] == m_id) & (df_telemetry["time stamp"] >= start_d) & (df_telemetry["time stamp"] <= end_d)
        df_telemetry.loc[mask, "is_ground_truth_fault"] = True

    # Machine-wise split
    holdout_machines = ["M1215", "M1216", "M1217", "M1218", "M1219", "M1220"]
    train_df = df_telemetry[~df_telemetry["Machine_number"].isin(holdout_machines)].copy()
    test_df = df_telemetry[df_telemetry["Machine_number"].isin(holdout_machines)].copy()

    # Train only on baseline healthy rows from train machines
    train_healthy = train_df[~train_df["is_ground_truth_fault"]].copy()

    detector = AnomalyDetector(contamination=0.08, random_state=42)
    detector.fit(train_healthy)

    # Save trained model
    model_path = os.path.join(output_dir, "isolation_forest_model.pkl")
    detector.save(model_path)

    # Predict on unseen holdout machines
    scores, preds = detector.predict_scores(test_df)
    y_true = test_df["is_ground_truth_fault"].to_numpy().astype(int)
    y_pred = preds.astype(int)

    # Calculate metrics
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    report = {
        "evaluation_strategy": "Machine-Wise Holdout (Unseen Machines)",
        "train_machines_count": len(train_df["Machine_number"].unique()),
        "test_holdout_machines": holdout_machines,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "test_ground_truth_anomalies": int(y_true.sum()),
        "test_predicted_anomalies": int(y_pred.sum()),
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn)
        },
        "academic_disclosure": (
            "These metrics evaluate the ML workflow on synthetically simulated degradation events. "
            "Model performance on synthetic data MUST NOT be interpreted as certified physical detection accuracy on industrial plant equipment."
        )
    }

    report_path = os.path.join(output_dir, "model_evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
