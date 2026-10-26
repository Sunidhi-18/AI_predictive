"""
loaders.py
----------
Robust local file loaders for raw CSV datasets with encoding detection and schema validation.
"""

import os
from typing import Optional, Tuple
import pandas as pd
from .schemas import RAW_TELEMETRY_COLUMNS, SPECTRUM_COLUMNS


def load_raw_csv(filepath: str) -> pd.DataFrame:
    """
    Loads raw CSV file with fallback encoding detection.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(filepath, encoding=enc)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise IOError(f"Error reading {filepath} with encoding {enc}: {e}")

    raise ValueError(f"Unable to decode {filepath} using standard encodings.")


def standardize_telemetry_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes raw telemetry columns to match the canonical schema.
    """
    rename_map = {}
    for col in df.columns:
        c_clean = col.strip()
        if c_clean.lower() in ["machine_number", "machine_id", "machinenumber", "machine"]:
            rename_map[col] = "Machine_number"
        elif c_clean.lower() in ["time stamp", "timestamp", "date", "datetime"]:
            rename_map[col] = "time stamp"
        else:
            # Check for P1-V, P1-H, etc.
            rename_map[col] = c_clean.upper()

    df_renamed = df.rename(columns=rename_map)
    return df_renamed
