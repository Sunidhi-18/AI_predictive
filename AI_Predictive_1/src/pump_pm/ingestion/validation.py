"""
validation.py
-------------
Data quality enforcement, schema validation, physical range checking,
and quarantine isolation for invalid records.
"""

import os
from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime

from .schemas import (
    RAW_TELEMETRY_COLUMNS,
    PHYSICAL_LIMITS,
    DataQualityReport,
)


def validate_and_quarantine_telemetry(
    df: pd.DataFrame,
    source_name: str = "raw_telemetry",
    quarantine_dir: str = "data/quarantine"
) -> Tuple[pd.DataFrame, pd.DataFrame, DataQualityReport]:
    """
    Validates raw telemetry records.
    Separates valid records from quarantined records (missing Machine ID, missing timestamp,
    corrupted dates, or physically impossible numbers).
    Produces a detailed DataQualityReport.
    """
    os.makedirs(quarantine_dir, exist_ok=True)
    report = DataQualityReport(source_file=source_name)

    report.total_records = len(df)
    report.total_cells = int(df.size)
    report.missing_cells = int(df.isnull().sum().sum())
    report.missing_percentage = (report.missing_cells / report.total_cells * 100) if report.total_cells > 0 else 0.0
    report.missing_by_column = {col: int(df[col].isnull().sum()) for col in df.columns}
    report.duplicate_rows = int(df.duplicated().sum())

    # Check for missing Machine_number
    mach_col = "Machine_number" if "Machine_number" in df.columns else None
    time_col = "time stamp" if "time stamp" in df.columns else None

    quarantine_mask = pd.Series(False, index=df.index)
    reasons = []

    if mach_col is None:
        raise ValueError(f"Schema error: Missing '{mach_col}' column in telemetry data.")
    if time_col is None:
        raise ValueError(f"Schema error: Missing '{time_col}' column in telemetry data.")

    # 1. Check Missing Machine ID
    missing_id_mask = df[mach_col].isnull() | (df[mach_col].astype(str).str.strip() == "") | (df[mach_col].astype(str).str.lower() == "nan")
    report.missing_machine_ids = int(missing_id_mask.sum())

    # 2. Check Missing / Corrupt Timestamp
    missing_time_mask = df[time_col].isnull()
    parsed_timestamps = pd.to_datetime(df[time_col], errors="coerce")
    corrupt_time_mask = parsed_timestamps.isnull() & (~missing_time_mask)
    report.missing_timestamps = int((missing_time_mask | corrupt_time_mask).sum())

    # 3. Check Physical Range Violations
    out_of_range_mask = pd.Series(False, index=df.index)
    vibration_cols = [c for c in df.columns if any(c.endswith(f"-{d}") for d in ["V", "H", "A"])]
    temp_cols = [c for c in df.columns if c.endswith("-T")]

    for v_col in vibration_cols:
        val = pd.to_numeric(df[v_col], errors="coerce")
        bad = (val < PHYSICAL_LIMITS["vibration_rms_min"]) | (val > PHYSICAL_LIMITS["vibration_rms_max"])
        out_of_range_mask |= bad

    for t_col in temp_cols:
        val = pd.to_numeric(df[t_col], errors="coerce")
        bad = (val < PHYSICAL_LIMITS["temperature_c_min"]) | (val > PHYSICAL_LIMITS["temperature_c_max"])
        out_of_range_mask |= bad

    report.out_of_range_values = int(out_of_range_mask.sum())

    # Combine quarantine criteria
    quarantine_mask = missing_id_mask | missing_time_mask | corrupt_time_mask | out_of_range_mask

    # Document quarantine reasons
    quarantined_df = df[quarantine_mask].copy()
    valid_df = df[~quarantine_mask].copy()

    q_reasons = []
    for idx, row in quarantined_df.iterrows():
        reason_list = []
        if missing_id_mask.loc[idx]:
            reason_list.append("MISSING_MACHINE_ID")
        if missing_time_mask.loc[idx]:
            reason_list.append("MISSING_TIMESTAMP")
        elif corrupt_time_mask.loc[idx]:
            reason_list.append("CORRUPT_TIMESTAMP_FORMAT")
        if out_of_range_mask.loc[idx]:
            reason_list.append("PHYSICAL_RANGE_VIOLATION")
        q_reasons.append("; ".join(reason_list))

    quarantined_df["quarantine_reason"] = q_reasons
    quarantined_df["quarantined_at"] = datetime.now().isoformat()

    # Track reasons count in report
    for r in q_reasons:
        for single_r in r.split("; "):
            report.quarantine_reasons[single_r] = report.quarantine_reasons.get(single_r, 0) + 1

    report.valid_records = len(valid_df)
    report.quarantined_records = len(quarantined_df)

    if not valid_df.empty:
        valid_df["parsed_timestamp"] = pd.to_datetime(valid_df[time_col])
        report.machines_present = sorted([str(m) for m in valid_df[mach_col].unique()])
        report.date_start = str(valid_df["parsed_timestamp"].min().date())
        report.date_end = str(valid_df["parsed_timestamp"].max().date())
        valid_df = valid_df.drop(columns=["parsed_timestamp"])

    # Persist quarantine records
    if not quarantined_df.empty:
        q_csv_path = os.path.join(quarantine_dir, "quarantined_records.csv")
        # Append or write
        write_header = not os.path.exists(q_csv_path)
        quarantined_df.to_csv(q_csv_path, mode="a", index=False, header=write_header)

        # Log entries
        log_rows = []
        for idx, row in quarantined_df.iterrows():
            log_rows.append({
                "source_file": source_name,
                "original_row_index": idx,
                "machine_id": str(row.get("Machine_number", "MISSING")),
                "timestamp": str(row.get("time stamp", "MISSING")),
                "reason": row["quarantine_reason"],
                "quarantined_at": row["quarantined_at"]
            })
        log_df = pd.DataFrame(log_rows)
        log_path = os.path.join(quarantine_dir, "quarantine_log.csv")
        log_header = not os.path.exists(log_path)
        log_df.to_csv(log_path, mode="a", index=False, header=log_header)

    return valid_df, quarantined_df, report
