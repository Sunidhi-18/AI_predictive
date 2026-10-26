"""
telemetry_features.py
---------------------
Feature engineering for time-series telemetry.
Calculates rolling window statistics, trend slopes, temperature differentials,
and directional vibration ratios.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


def calculate_rolling_telemetry_features(
    long_df: pd.DataFrame,
    window_days: int = 7
) -> pd.DataFrame:
    """
    Computes rolling statistics for normalized long-form telemetry:
    - rolling mean (7-day)
    - rolling std (7-day)
    - rolling slope (rate of change over window)
    - acceleration / jerk indicators
    """
    df = long_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by=["machine_id", "location_id", "direction", "timestamp"]).reset_index(drop=True)

    # Group by machine, location, direction
    groups = df.groupby(["machine_id", "location_id", "direction"])

    df["vib_rolling_mean_7d"] = groups["vibration_rms"].transform(
        lambda s: s.rolling(window=window_days, min_periods=1).mean()
    )
    df["vib_rolling_std_7d"] = groups["vibration_rms"].transform(
        lambda s: s.rolling(window=window_days, min_periods=1).std().fillna(0.0)
    )
    df["vib_rate_of_change_1d"] = groups["vibration_rms"].transform(
        lambda s: s.diff().fillna(0.0)
    )

    # Temperature rolling features
    df["temp_rolling_mean_7d"] = groups["temperature_c"].transform(
        lambda s: s.rolling(window=window_days, min_periods=1).mean()
    )
    df["temp_rate_of_change_1d"] = groups["temperature_c"].transform(
        lambda s: s.diff().fillna(0.0)
    )

    return df


def calculate_directional_ratios(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes physical directional ratios from wide daily telemetry:
    - Radial to Axial ratio: mean(H, V) / A for each location P1..P4
    - Horizontal to Vertical ratio: H / V for each location P1..P4
    - Coupling asymmetry ratio: P2_vib / P3_vib
    """
    df = wide_df.copy()
    locations = ["P1", "P2", "P3", "P4"]

    for loc in locations:
        h_col = f"{loc}-H"
        v_col = f"{loc}-V"
        a_col = f"{loc}-A"

        if h_col in df.columns and v_col in df.columns and a_col in df.columns:
            radial_avg = (df[h_col] + df[v_col]) / 2.0
            # Radial / Axial ratio (High radial ratio is characteristic of Imbalance)
            df[f"{loc}_radial_to_axial_ratio"] = radial_avg / (df[a_col] + 1e-4)
            # H / V ratio (Extreme deviation from 1.0 indicates Looseness or Directional Resonance)
            df[f"{loc}_h_to_v_ratio"] = df[h_col] / (df[v_col] + 1e-4)

    # Coupling cross-ratio (P2: Pump-DE vs P3: Motor-DE)
    if "P2-A" in df.columns and "P3-A" in df.columns:
        df["coupling_axial_ratio"] = df["P2-A"] / (df["P3-A"] + 1e-4)

    return df
