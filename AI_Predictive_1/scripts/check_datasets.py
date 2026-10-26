import os
import pandas as pd

paths = [
    "data/raw/daily_telemetry.csv",
    "data/raw/high_readings_telemetry.csv",
    "data/generated/synthetic_daily_telemetry.csv",
    "data/features/wide_directional_features.csv",
    "data/generated/synthetic_fault_events.csv"
]

print("=== CHECKING DATASETS ===")
for p in paths:
    if os.path.exists(p):
        df = pd.read_csv(p)
        print(f"\nFile: {p}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        date_col = "time stamp" if "time stamp" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
        mach_col = "Machine_number" if "Machine_number" in df.columns else ("machine_id" if "machine_id" in df.columns else None)
        if date_col:
            clean_dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            print(f"Date col: {date_col}, Min: {clean_dates.min() if not clean_dates.empty else 'N/A'}, Max: {clean_dates.max() if not clean_dates.empty else 'N/A'}, Nulls: {df[date_col].isnull().sum()}")
        if mach_col:
            machs = df[mach_col].dropna().astype(str).unique().tolist()
            print(f"Machine col: {mach_col}, Unique count: {len(machs)}, Sample: {machs[:10]}")
        print(f"Total nulls: {df.isnull().sum().sum()}")
    else:
        print(f"NOT FOUND: {p}")

