"""
validate_data.py
----------------
CLI script to validate raw datasets against schema, physical boundaries,
and identity constraints. Produces quarantine outputs and data-quality reports.
"""

import os
import sys
import json
import pandas as pd

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from pump_pm.ingestion.loaders import load_raw_csv, standardize_telemetry_columns
from pump_pm.ingestion.validation import validate_and_quarantine_telemetry


def main():
    print("=" * 60)
    print("AI Predictive Maintenance — Data Quality & Validation Engine")
    print("=" * 60)

    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    quarantine_dir = os.path.join(PROJECT_ROOT, "data", "quarantine")
    outputs_dir = os.path.join(PROJECT_ROOT, "outputs", "reports")
    os.makedirs(outputs_dir, exist_ok=True)

    files_to_validate = [
        ("daily_telemetry.csv", "raw_daily_telemetry"),
        ("high_readings_telemetry.csv", "raw_high_readings_telemetry"),
    ]

    summary_reports = {}

    for fname, src_tag in files_to_validate:
        fpath = os.path.join(raw_dir, fname)
        if not os.path.exists(fpath):
            print(f"Skipping {fname}: file not found.")
            continue

        print(f"\n[Validating] {fname}...")
        df_raw = load_raw_csv(fpath)
        df_std = standardize_telemetry_columns(df_raw)

        valid_df, quarantined_df, report = validate_and_quarantine_telemetry(
            df=df_std,
            source_name=src_tag,
            quarantine_dir=quarantine_dir
        )

        rep_dict = report.to_dict()
        summary_reports[fname] = rep_dict

        print(f"  Total records:      {rep_dict['total_records']}")
        print(f"  Valid records:      {rep_dict['valid_records']}")
        print(f"  Quarantined rows:   {rep_dict['quarantined_records']}")
        print(f"  Missing cells:      {rep_dict['missing_cells']} ({rep_dict['missing_percentage']}%)")
        print(f"  Missing Machine IDs:{rep_dict['missing_machine_ids']}")
        print(f"  Missing Timestamps: {rep_dict['missing_timestamps']}")
        print(f"  Quarantine reasons: {rep_dict['quarantine_reasons']}")
        print(f"  Machines present:   {rep_dict['machines_present']}")
        print(f"  Date range:         {rep_dict['date_start']} to {rep_dict['date_end']}")

    # Save summary report JSON
    rep_json_path = os.path.join(outputs_dir, "data_quality_report.json")
    with open(rep_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_reports, f, indent=2)
    print(f"\n[OK] Data quality report saved to: {rep_json_path}")


if __name__ == "__main__":
    main()
