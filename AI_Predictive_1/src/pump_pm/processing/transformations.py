"""
transformations.py
------------------
Normalizes wide daily telemetry matrices into a tidy long-form tabular structure.
Maps location codes (P1..P4) to engineering physical names (P-NDE, P-DE, M-DE, M-NDE).
"""

import os
from typing import Optional, Tuple
import pandas as pd
import numpy as np

LOCATION_NAMES = {
    "P1": "P-NDE (Pump Non-Drive End)",
    "P2": "P-DE (Pump Drive End)",
    "P3": "M-DE (Motor Drive End)",
    "P4": "M-NDE (Motor Non-Drive End)"
}


def normalize_to_long_form(
    df: pd.DataFrame,
    provenance: str = "RAW_BASELINE"
) -> pd.DataFrame:
    """
    Transforms wide daily telemetry format:
      [Machine_number, time stamp, P1-V, P1-H, P1-A, P1-T, P2-V...]
    into tidy long-form:
      [machine_id, timestamp, location_id, location_name, direction, vibration_rms, temperature_c, provenance, quality_flag]
    """
    mach_col = "Machine_number"
    time_col = "time stamp"

    locations = ["P1", "P2", "P3", "P4"]
    directions = ["V", "H", "A"]

    rows = []
    for _, row in df.iterrows():
        m_id = str(row[mach_col])
        t_val = pd.to_datetime(row[time_col])

        for loc in locations:
            loc_name = LOCATION_NAMES.get(loc, loc)
            temp_val = row.get(f"{loc}-T", np.nan)
            temp_is_null = pd.isna(temp_val)

            for d in directions:
                vib_col = f"{loc}-{d}"
                vib_val = row.get(vib_col, np.nan)
                vib_is_null = pd.isna(vib_val)

                quality_flag = "MISSING" if (vib_is_null or temp_is_null) else "VALID"

                rows.append({
                    "machine_id": m_id,
                    "timestamp": t_val,
                    "location_id": loc,
                    "location_name": loc_name,
                    "direction": d,
                    "vibration_rms": float(vib_val) if not vib_is_null else np.nan,
                    "temperature_c": float(temp_val) if not temp_is_null else np.nan,
                    "provenance": provenance,
                    "quality_flag": quality_flag
                })

    long_df = pd.DataFrame(rows)
    return long_df


def save_processed_telemetry(
    df: pd.DataFrame,
    output_dir: str = "data/processed",
    base_filename: str = "normalized_telemetry"
) -> Tuple[str, str]:
    """
    Saves normalized telemetry to both Parquet and CSV for maximum local compatibility.
    """
    os.makedirs(output_dir, exist_ok=True)
    parquet_path = os.path.join(output_dir, f"{base_filename}.parquet")
    csv_path = os.path.join(output_dir, f"{base_filename}.csv")

    try:
        df.to_parquet(parquet_path, index=False)
    except Exception as e:
        print(f"Notice: Parquet export encountered {e}. Saving to CSV as primary format.")

    df.to_csv(csv_path, index=False)
    return parquet_path, csv_path
