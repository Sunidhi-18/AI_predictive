"""
train_forecaster.py
-------------------
End-to-end training and evaluation script for the hybrid forecasting model.
Prepares leak-free forecasting data, fits Random Forest, Persistence, and Ridge baselines,
evaluates on unseen chronological test splits, assesses predicted ISO severity zones,
and exports model artifacts and comparison reports.
"""

import os
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Path setup
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from pump_pm.forecasting import (
    prepare_forecasting_dataset,
    split_chronological,
    SensorForecaster,
    PersistenceBaseline,
    RidgeRegressionBaseline,
    compare_current_and_predicted_zones,
    DEFAULT_TARGET_CHANNELS
)


def run_training_pipeline():
    start_time = datetime.now()
    print("=" * 75)
    print("AI Predictive Maintenance — Hybrid Forecasting & Predicted Zone Pipeline")
    print(f"Started at: {start_time.isoformat()}")
    print("=" * 75)

    data_path = os.path.join(PROJECT_ROOT, "data", "features", "wide_directional_features.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Telemetry feature dataset not found at {data_path}. Run scripts/run_local_pipeline.py first.")

    print(f"\n[Step 1/5] Loading historical telemetry dataset from {data_path}...")
    raw_df = pd.read_csv(data_path)
    print(f"  Loaded {len(raw_df):,} rows across machines: {raw_df['Machine_number'].unique().tolist()}")

    # 1. Data Engineering for Forecasting
    print("\n[Step 2/5] Preparing leak-free dataset with time gap validation & machine separation...")
    X, y, feature_names, target_names, meta_df = prepare_forecasting_dataset(
        df=raw_df,
        target_channels=DEFAULT_TARGET_CHANNELS,
        max_gap_days=1.0,
        lags=[1, 2, 3, 7],
        rolling_windows=[3, 7]
    )
    print(f"  Valid forecast sample pairs: {len(X):,} rows")
    print(f"  Engineered feature count: {len(feature_names)} features")
    print(f"  Target channels: {len(target_names)} channels ({', '.join(target_names[:6])}...)")

    # 2. Chronological Split
    print("\n[Step 3/5] Performing chronological train/test split (80% train / 20% test per machine)...")
    X_train, y_train, meta_train, X_test, y_test, meta_test = split_chronological(
        X, y, meta_df, train_ratio=0.8
    )
    print(f"  Training set: {len(X_train):,} samples ({meta_train['timestamp'].min().date()} to {meta_train['timestamp'].max().date()})")
    print(f"  Unseen test set: {len(X_test):,} samples ({meta_test['timestamp'].min().date()} to {meta_test['timestamp'].max().date()})")

    # 3. Model Training & Comparison
    print("\n[Step 4/5] Training and Evaluating Forecasting Models on Unseen Test Data...")

    # A. Persistence Baseline
    persistence = PersistenceBaseline(target_names=target_names)
    persistence_metrics = persistence.evaluate(X_test, y_test)
    print(f"\n  [Model 1] Persistence Baseline (y_hat = y_t):")
    print(f"    Overall MAE:  {persistence_metrics['overall_mae']:.4f}")
    print(f"    Overall RMSE: {persistence_metrics['overall_rmse']:.4f}")
    print(f"    Overall R2:   {persistence_metrics['overall_r2']:.4f}")

    # B. Ridge Linear Regression Baseline
    ridge = RidgeRegressionBaseline(target_names=target_names, alpha=1.0)
    ridge.fit(X_train, y_train)
    ridge_metrics = ridge.evaluate(X_test, y_test)
    print(f"\n  [Model 2] Ridge Linear Regression Baseline:")
    print(f"    Overall MAE:  {ridge_metrics['overall_mae']:.4f}")
    print(f"    Overall RMSE: {ridge_metrics['overall_rmse']:.4f}")
    print(f"    Overall R2:   {ridge_metrics['overall_r2']:.4f}")

    # C. Random Forest Regressor (Primary Model)
    rf = SensorForecaster(
        target_names=target_names,
        feature_names=feature_names,
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    print(f"\n  [Model 3] Training Random Forest Regressor (100 trees, max_depth=12)...")
    rf.fit(X_train, y_train)
    rf_metrics = rf.evaluate(X_test, y_test)
    print(f"    Overall MAE:  {rf_metrics['overall_mae']:.4f}")
    print(f"    Overall RMSE: {rf_metrics['overall_rmse']:.4f}")
    print(f"    Overall R2:   {rf_metrics['overall_r2']:.4f}")

    # Comparison Table
    print("\n" + "=" * 60)
    print(f"{'Model':<35} | {'MAE':<8} | {'RMSE':<8} | {'R2':<8}")
    print("-" * 60)
    print(f"{'1. Persistence Baseline':<35} | {persistence_metrics['overall_mae']:<8.4f} | {persistence_metrics['overall_rmse']:<8.4f} | {persistence_metrics['overall_r2']:<8.4f}")
    print(f"{'2. Ridge Linear Regression':<35} | {ridge_metrics['overall_mae']:<8.4f} | {ridge_metrics['overall_rmse']:<8.4f} | {ridge_metrics['overall_r2']:<8.4f}")
    print(f"{'3. Random Forest Regressor (Ours)':<35} | {rf_metrics['overall_mae']:<8.4f} | {rf_metrics['overall_rmse']:<8.4f} | {rf_metrics['overall_r2']:<8.4f}")
    print("=" * 60)

    # 4. Save Models & Reports
    print("\n[Step 5/5] Persisting Model Artifacts & Predicted Zone Validation...")
    model_dir = os.path.join(PROJECT_ROOT, "outputs", "models")
    reports_dir = os.path.join(PROJECT_ROOT, "outputs", "reports")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    model_path = os.path.join(model_dir, "forecaster_model.pkl")
    config_path = os.path.join(model_dir, "forecaster_config.json")
    rf.save(model_path=model_path, config_path=config_path)
    print(f"  Saved trained Random Forest model to: {model_path}")
    print(f"  Saved model config to: {config_path}")

    # Generate Test Predictions and evaluate Predicted Zones sample
    test_preds_df = rf.predict_dataframe(X_test)
    sample_evals = []
    zone_transitions_count = 0

    for i in range(min(500, len(test_preds_df))):
        m_id = meta_test.iloc[i]["Machine_number"]
        cur_ts = str(meta_test.iloc[i]["timestamp"])
        nxt_ts = str(meta_test.iloc[i]["next_timestamp"])

        # Reconstruct current row
        cur_row_data = {"Machine_number": m_id, "time stamp": cur_ts}
        for ch in DEFAULT_TARGET_CHANNELS:
            cur_row_data[ch] = X_test.iloc[i].get(f"{ch}_curr", np.nan)
        cur_row_series = pd.Series(cur_row_data)

        # Predicted values
        pred_dict = test_preds_df.iloc[i].to_dict()

        comp = compare_current_and_predicted_zones(
            machine_id=m_id,
            current_row=cur_row_series,
            predicted_readings=pred_dict,
            forecast_timestamp=nxt_ts
        )
        if comp["is_degradation"]:
            zone_transitions_count += 1
        sample_evals.append({
            "machine_id": m_id,
            "current_date": cur_ts[:10],
            "forecast_date": nxt_ts[:10],
            "current_zone": comp["current_zone"].split(" ")[0],
            "predicted_zone": comp["predicted_zone"].split(" ")[0],
            "current_peak": comp["current_peak_vib"],
            "predicted_peak": comp["predicted_peak_vib"],
            "is_degradation": comp["is_degradation"],
            "transition_alert": comp["transition_alert"]
        })

    print(f"  Evaluated {len(sample_evals)} test samples against ISO 10816-7 rules.")
    print(f"  Detected {zone_transitions_count} predictive zone degradation transitions.")

    # Save comprehensive evaluation report
    report_data = {
        "report_generated_at": datetime.now().isoformat(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_count": len(feature_names),
        "target_channels": target_names,
        "models_evaluated": {
            "random_forest": rf_metrics,
            "persistence_baseline": persistence_metrics,
            "ridge_regression": ridge_metrics
        },
        "sample_zone_transitions_detected": zone_transitions_count,
        "sample_evaluations": sample_evals[:20]
    }
    report_path = os.path.join(reports_dir, "forecasting_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"  Saved evaluation report to: {report_path}")

    # Also save test predictions sample CSV for fast dashboard inspection
    preds_export = pd.concat([
        meta_test.reset_index(drop=True),
        test_preds_df.reset_index(drop=True),
        y_test.reset_index(drop=True)
    ], axis=1)
    sample_preds_path = os.path.join(reports_dir, "forecasting_test_predictions.csv")
    preds_export.head(2000).to_csv(sample_preds_path, index=False)
    print(f"  Saved test predictions sample CSV to: {sample_preds_path}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n[SUCCESS] Pipeline finished in {duration:.1f}s.")


if __name__ == "__main__":
    run_training_pipeline()
