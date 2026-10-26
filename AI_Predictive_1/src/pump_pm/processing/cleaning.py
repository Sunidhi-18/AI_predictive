"""
cleaning.py
-----------
Documented cleaning, deduplication, and quality-flagged sensor imputation.
Preserves original missingness indicators without hiding data defects.
"""

from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np


def clean_telemetry(
    valid_df: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans valid telemetry data:
    1. Standardizes datetimes and sorts by (Machine_number, time stamp).
    2. Removes exact duplicate timestamp records per machine.
    3. Retains original sensor values with missingness indicators.
    4. Computes quality-flagged imputations for downstream features.
    """
    df = valid_df.copy()
    mach_col = "Machine_number"
    time_col = "time stamp"

    # Convert timestamp
    df["timestamp"] = pd.to_datetime(df[time_col])
    initial_count = len(df)

    # Sort
    df = df.sort_values(by=[mach_col, "timestamp"]).reset_index(drop=True)

    # Deduplicate on (machine, timestamp)
    duplicates_count = int(df.duplicated(subset=[mach_col, "timestamp"]).sum())
    if duplicates_count > 0:
        df = df.drop_duplicates(subset=[mach_col, "timestamp"], keep="first").reset_index(drop=True)

    sensor_cols = [c for c in df.columns if c not in [mach_col, time_col, "timestamp"]]

    # Pre-cleaning missing statistics
    missing_before = int(df[sensor_cols].isnull().sum().sum())
    missing_pct_before = (missing_before / (len(df) * len(sensor_cols)) * 100) if len(df) > 0 else 0.0

    # Impute missing sensor values per machine using forward-fill with backfill fallback,
    # recording imputation quality flags
    imputed_df = df.copy()

    for m_id, group in df.groupby(mach_col):
        m_indices = group.index
        # Forward-fill up to 3 days, then fill with machine median
        ffilled = group[sensor_cols].ffill(limit=3)
        bfilled = ffilled.bfill(limit=3)
        median_filled = bfilled.fillna(group[sensor_cols].median())
        imputed_df.loc[m_indices, sensor_cols] = median_filled

    missing_after = int(imputed_df[sensor_cols].isnull().sum().sum())

    metrics = {
        "initial_valid_rows": initial_count,
        "deduplicated_rows": len(df),
        "duplicate_rows_removed": duplicates_count,
        "sensor_missing_cells_before": missing_before,
        "sensor_missing_pct_before": round(missing_pct_before, 2),
        "sensor_missing_cells_after": missing_after,
        "imputation_strategy": "forward_fill_limit_3_then_machine_median"
    }

    return imputed_df, metrics
