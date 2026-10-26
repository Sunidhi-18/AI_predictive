"""
run_local_pipeline.py
---------------------
End-to-end local data engineering, feature calculation, standards assessment,
ML anomaly detection, and SQLite event generation pipeline.
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

from pump_pm.config import get_config
from pump_pm.ingestion.loaders import load_raw_csv, standardize_telemetry_columns
from pump_pm.ingestion.validation import validate_and_quarantine_telemetry
from pump_pm.processing.cleaning import clean_telemetry
from pump_pm.processing.transformations import normalize_to_long_form, save_processed_telemetry
from pump_pm.features.telemetry_features import calculate_rolling_telemetry_features, calculate_directional_ratios
from pump_pm.standards.zone_assessment import assess_machine_telemetry_row
from pump_pm.diagnostics.rule_engine import MultiEvidenceRuleEngine
from pump_pm.models.anomaly_detection import AnomalyDetector
from pump_pm.storage.repository import MaintenanceRepository


def run_pipeline():
    start_time = datetime.now()
    print("=" * 70)
    print("AI Predictive Maintenance — End-to-End Local Execution Pipeline")
    print(f"Started at: {start_time.isoformat()}")
    print("=" * 70)

    cfg = get_config()
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
    features_dir = os.path.join(PROJECT_ROOT, "data", "features")
    quarantine_dir = os.path.join(PROJECT_ROOT, "data", "quarantine")
    db_path = os.path.join(PROJECT_ROOT, "data", "database", "maintenance.db")
    reports_dir = os.path.join(PROJECT_ROOT, "outputs", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    repo = MaintenanceRepository(db_path=db_path)
    rule_engine = MultiEvidenceRuleEngine()

    # 1. Ingestion: load both baseline and coordinated high-reading datasets
    print("\n[Step 1/6] Ingesting and Validating Raw Telemetry Datasets...")
    daily_file = os.path.join(raw_dir, "daily_telemetry.csv")
    high_file = os.path.join(raw_dir, "high_readings_telemetry.csv")

    raw_dfs = []
    if os.path.exists(daily_file):
        df1 = load_raw_csv(daily_file)
        raw_dfs.append((df1, "daily_telemetry.csv"))
    if os.path.exists(high_file):
        df2 = load_raw_csv(high_file)
        raw_dfs.append((df2, "high_readings_telemetry.csv"))

    # Also ingest synthetic fleet machines M1206-M1220 for full 20-machine fleet coverage
    synth_file = os.path.join(PROJECT_ROOT, "data", "generated", "synthetic_daily_telemetry.csv")
    if os.path.exists(synth_file):
        df3 = load_raw_csv(synth_file)
        # Filter for machines M1206 to M1220 to complement M1201 to M1205
        df3_extra = df3[df3["Machine_number"].isin([f"M{i}" for i in range(1206, 1221)])]
        if not df3_extra.empty:
            raw_dfs.append((df3_extra, "synthetic_daily_telemetry.csv"))

    if not raw_dfs:
        raise FileNotFoundError("No raw telemetry datasets found in data/raw/.")

    all_valid = []
    total_quarantined = 0

    for df_raw, tag in raw_dfs:
        df_std = standardize_telemetry_columns(df_raw)
        valid_df, quarantined_df, rep = validate_and_quarantine_telemetry(
            df=df_std,
            source_name=tag,
            quarantine_dir=quarantine_dir
        )
        all_valid.append(valid_df)
        total_quarantined += len(quarantined_df)
        print(f"  Loaded {tag}: {len(valid_df):,} valid rows, {len(quarantined_df):,} quarantined rows")


    combined_valid = pd.concat(all_valid, ignore_index=True)
    print(f"  Combined valid records: {len(combined_valid):,}")

    # 2. Cleaning and Quality-Aware Imputation
    print("\n[Step 2/6] Cleaning Telemetry and Deduplicating...")
    cleaned_df, clean_metrics = clean_telemetry(combined_valid)
    print(f"  Deduplicated records: {len(cleaned_df):,} (Removed {clean_metrics['duplicate_rows_removed']} duplicates)")
    print(f"  Sensor missing cells before imputation: {clean_metrics['sensor_missing_cells_before']} ({clean_metrics['sensor_missing_pct_before']}%)")

    # 3. Normalization to Long-Form Schema
    print("\n[Step 3/6] Normalizing to Long-Form Schema...")
    long_df = normalize_to_long_form(cleaned_df, provenance="RAW_CANONICAL")
    save_processed_telemetry(long_df, output_dir=processed_dir, base_filename="normalized_telemetry")
    print(f"  Saved normalized telemetry: {len(long_df):,} point-direction rows")

    # 4. Feature Engineering
    print("\n[Step 4/6] Computing Rolling Statistics & Directional Ratios...")
    featured_long = calculate_rolling_telemetry_features(long_df, window_days=7)
    save_processed_telemetry(featured_long, output_dir=features_dir, base_filename="telemetry_features")

    featured_wide = calculate_directional_ratios(cleaned_df)
    save_processed_telemetry(featured_wide, output_dir=features_dir, base_filename="wide_directional_features")
    print(f"  Engineered rolling features: mean_7d, std_7d, diff_1d, R/A ratio, H/V ratio, coupling ratio")

    # 5. Fit Anomaly Detector Baseline on Normal Data
    print("\n[Step 5/6] Fitting Anomaly Detector Baseline...")
    detector = AnomalyDetector(contamination=0.06, random_state=42)
    # Fit on lower vibration rows (vibration < 5.0)
    low_vib_rows = featured_wide[featured_wide["P1-V"] < 5.0]
    if len(low_vib_rows) < 100:
        low_vib_rows = featured_wide
    detector.fit(low_vib_rows)
    detector.save(os.path.join(PROJECT_ROOT, "outputs", "evaluation", "isolation_forest_model.pkl"))

    scores, is_anom = detector.predict_scores(featured_wide)
    featured_wide["anomaly_score"] = scores
    featured_wide["is_anomaly"] = is_anom
    print(f"  Detected {int(is_anom.sum()):,} statistical anomalies out of {len(featured_wide):,} rows")

    # 6. Standards Severity Assessment & Rule Engine Event Population
    print("\n[Step 6/6] Assessing ISO 10816-7 Severity Zones and Populating Database...")
    events_to_record = []
    zone_distribution = {}

    for idx, row in featured_wide.iterrows():
        assessment = assess_machine_telemetry_row(row)
        gov_zone = assessment["governing_zone"]
        zone_distribution[gov_zone] = zone_distribution.get(gov_zone, 0) + 1

        is_abnormal = ("Zone C" in gov_zone) or ("Zone D" in gov_zone) or bool(row["is_anomaly"])

        # Populate events table for significant occurrences
        if is_abnormal:
            m_id = str(row["Machine_number"])
            eval_res = rule_engine.evaluate(
                machine_id=m_id,
                telemetry_row=row,
                governing_zone=gov_zone
            )

            c_dicts = [c.to_dict() for c in eval_res.candidates]
            sup_ev = eval_res.dominant_hypothesis.supporting_evidence if eval_res.dominant_hypothesis else []
            miss_ev = eval_res.dominant_hypothesis.missing_evidence if eval_res.dominant_hypothesis else []

            event_payload = {
                "machine_id": m_id,
                "timestamp": str(row["time stamp"]),
                "source": "PIPELINE_STANDARDS_AND_RULES",
                "severity_zone": gov_zone,
                "alarm_status": assessment["highest_alarm_status"],
                "max_vibration": assessment["max_vibration_rms"],
                "dominant_location": assessment["governing_location"],
                "candidate_faults": c_dicts,
                "supporting_evidence": sup_ev,
                "missing_evidence": miss_ev,
                "anomaly_score": float(row["anomaly_score"]),
                "model_version": "1.0.0",
                "status": "OPEN"
            }
            events_to_record.append(event_payload)

    events_recorded = repo.record_events_batch(events_to_record)
    print(f"  Populated SQLite database: {events_recorded:,} actionable events recorded")
    print(f"  Zone distribution: {zone_distribution}")


    # Generate pipeline summary report
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    pipeline_report = {
        "pipeline_version": "1.0.0",
        "timestamp_start": start_time.isoformat(),
        "timestamp_end": end_time.isoformat(),
        "duration_seconds": round(duration, 2),
        "total_valid_records": len(cleaned_df),
        "total_quarantined_records": total_quarantined,
        "anomalies_detected": int(is_anom.sum()),
        "events_recorded": events_recorded,
        "zone_distribution": zone_distribution,
        "database_file": db_path,
        "data_features_saved": [
            "data/processed/normalized_telemetry.parquet",
            "data/features/telemetry_features.parquet",
            "data/features/wide_directional_features.parquet"
        ]
    }

    report_path = os.path.join(reports_dir, "pipeline_run_summary.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_report, f, indent=2)

    print(f"\n[SUCCESS] Pipeline execution finished in {duration:.1f}s. Report: {report_path}")
    return pipeline_report


if __name__ == "__main__":
    run_pipeline()
