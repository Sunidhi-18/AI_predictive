"""
data_engineering.py
-------------------
Leakage-free data engineering and feature preparation for next-day sensor forecasting.

Enforces:
1. Strict machine separation (targets and lag/rolling features never cross machine boundaries).
2. Time gap validation (targets are invalidated if time delta > 1 day / missing data gap).
3. No lookahead leakage (features at time t only use historical observations <= t).
4. Chronological train/test splitting.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ..config import get_config


DEFAULT_TARGET_CHANNELS = [
    "P1-V", "P1-H", "P1-A", "P1-T",
    "P2-V", "P2-H", "P2-A", "P2-T",
    "P3-V", "P3-H", "P3-A", "P3-T",
    "P4-V", "P4-H", "P4-A", "P4-T"
]

DEFAULT_VIBRATION_CHANNELS = [
    "P1-V", "P1-H", "P1-A",
    "P2-V", "P2-H", "P2-A",
    "P3-V", "P3-H", "P3-A",
    "P4-V", "P4-H", "P4-A"
]


def prepare_forecasting_dataset(
    df: pd.DataFrame,
    target_channels: Optional[List[str]] = None,
    max_gap_days: float = 1.0,
    lags: List[int] = [1, 2, 3, 7],
    rolling_windows: List[int] = [3, 7],
    include_metadata: bool = True,
    require_targets: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str], List[str], pd.DataFrame]:
    """
    Prepares a leak-free forecasting dataset from wide telemetry.

    Parameters:
    -----------
    df : pd.DataFrame
        Wide telemetry dataframe with Machine_number and time stamp/timestamp.
    target_channels : List[str]
        Sensor channels to forecast for the next valid day. Defaults to 16 channels.
    max_gap_days : float
        Maximum allowed time gap (in days) between row t and row t+1 to create a target.
        If next observation is > max_gap_days away, target is set to NaN.
    lags : List[int]
        Historical lag days to generate as features.
    rolling_windows : List[int]
        Rolling window sizes for summary statistics (mean, std, max).
    include_metadata : bool
        Whether to attach static machine engineering parameters (power, speed, category).

    Returns:
    --------
    X : pd.DataFrame
        Engineered feature matrix strictly using historical data <= t.
    y : pd.DataFrame
        Next-valid-daily-reading targets at time t+1.
    feature_names : List[str]
        List of feature column names.
    target_names : List[str]
        List of target column names.
    meta_df : pd.DataFrame
        Identification metadata (Machine_number, current timestamp, next timestamp, time gap).
    """
    cfg = get_config()
    targets = target_channels or DEFAULT_TARGET_CHANNELS

    # 1. Standardize timestamp and sort strictly
    data = df.copy()
    time_col = "time stamp" if "time stamp" in data.columns else "timestamp"
    data["timestamp"] = pd.to_datetime(data[time_col], errors="coerce")
    data = data.dropna(subset=["timestamp", "Machine_number"])
    data = data.sort_values(by=["Machine_number", "timestamp"]).reset_index(drop=True)

    # 2. Target Generation with Strict Machine Separation and Time Gap Validation
    target_cols = [f"target_{ch}" for ch in targets]
    targets_dict = {}

    # Next timestamp within the same machine
    data["next_timestamp"] = data.groupby("Machine_number")["timestamp"].shift(-1)
    data["time_gap_days"] = (data["next_timestamp"] - data["timestamp"]).dt.total_seconds() / 86400.0

    # Valid step mask: must have a next reading AND gap <= max_gap_days (strictly consecutive step)
    valid_step_mask = (data["next_timestamp"].notna()) & (data["time_gap_days"] <= max_gap_days) & (data["time_gap_days"] > 0)

    for ch in targets:
        if ch in data.columns:
            # Shift within machine group
            shifted = data.groupby("Machine_number")[ch].shift(-1)
            # Invalidate target if time gap is irregular / missing data gap
            shifted = shifted.where(valid_step_mask, np.nan)
            targets_dict[f"target_{ch}"] = shifted
        else:
            raise KeyError(f"Target channel '{ch}' not found in dataframe columns.")

    target_df = pd.DataFrame(targets_dict, index=data.index)

    # 3. Feature Generation (Strictly historical <= t)
    feature_dict = {}

    for m_id, group in data.groupby("Machine_number", sort=False):
        grp_idx = group.index

        # A. Current readings (time t)
        for ch in targets:
            feature_dict.setdefault(f"{ch}_curr", pd.Series(index=data.index, dtype=float))
            feature_dict[f"{ch}_curr"].loc[grp_idx] = group[ch].values

            # B. Lags: t - lag
            for l in lags:
                lag_col = f"{ch}_lag{l}"
                feature_dict.setdefault(lag_col, pd.Series(index=data.index, dtype=float))
                feature_dict[lag_col].loc[grp_idx] = group[ch].shift(l).values

            # C. 1-day rate of change: value(t) - value(t-1)
            diff_col = f"{ch}_diff1"
            feature_dict.setdefault(diff_col, pd.Series(index=data.index, dtype=float))
            feature_dict[diff_col].loc[grp_idx] = (group[ch] - group[ch].shift(1)).values

            # D. Rolling statistics (window closed on current day)
            for w in rolling_windows:
                r_mean_col = f"{ch}_roll_mean_{w}d"
                r_std_col = f"{ch}_roll_std_{w}d"
                r_max_col = f"{ch}_roll_max_{w}d"

                feature_dict.setdefault(r_mean_col, pd.Series(index=data.index, dtype=float))
                feature_dict.setdefault(r_std_col, pd.Series(index=data.index, dtype=float))
                feature_dict.setdefault(r_max_col, pd.Series(index=data.index, dtype=float))

                rolling_obj = group[ch].rolling(window=w, min_periods=1)
                feature_dict[r_mean_col].loc[grp_idx] = rolling_obj.mean().values
                feature_dict[r_std_col].loc[grp_idx] = rolling_obj.std().fillna(0.0).values
                feature_dict[r_max_col].loc[grp_idx] = rolling_obj.max().values

        # E. Directional Ratios at time t
        ratio_cols = [
            "P1_radial_to_axial_ratio", "P1_h_to_v_ratio",
            "P2_radial_to_axial_ratio", "P2_h_to_v_ratio",
            "P3_radial_to_axial_ratio", "P3_h_to_v_ratio",
            "P4_radial_to_axial_ratio", "P4_h_to_v_ratio",
            "coupling_axial_ratio"
        ]
        for r_col in ratio_cols:
            if r_col in group.columns:
                feature_dict.setdefault(r_col, pd.Series(index=data.index, dtype=float))
                feature_dict[r_col].loc[grp_idx] = group[r_col].values
            elif r_col == "P2_radial_to_axial_ratio" and "P2-A" in group.columns:
                p2_rad = np.maximum(group["P2-V"], group["P2-H"])
                feature_dict.setdefault(r_col, pd.Series(index=data.index, dtype=float))
                feature_dict[r_col].loc[grp_idx] = (p2_rad / np.maximum(group["P2-A"], 0.1)).values

        # F. Machine engineering metadata
        if include_metadata:
            mach_info = cfg.get_machine(m_id) or {}
            pwr = float(mach_info.get("nominal_power_kw") or 160.0)
            rpm = float(mach_info.get("rated_speed_rpm") or 3000.0)
            cat_code = 1.0 if mach_info.get("category") == "category_1" else 2.0

            feature_dict.setdefault("meta_nominal_power_kw", pd.Series(index=data.index, dtype=float))
            feature_dict.setdefault("meta_rated_speed_rpm", pd.Series(index=data.index, dtype=float))
            feature_dict.setdefault("meta_category_code", pd.Series(index=data.index, dtype=float))

            feature_dict["meta_nominal_power_kw"].loc[grp_idx] = pwr
            feature_dict["meta_rated_speed_rpm"].loc[grp_idx] = rpm
            feature_dict["meta_category_code"].loc[grp_idx] = cat_code

    features_df = pd.DataFrame(feature_dict, index=data.index)

    # 4. Filter to rows where features (and optionally targets) are valid
    # In training (require_targets=True), rows without next-day targets are dropped.
    # In inference (require_targets=False), features can be evaluated up to the latest observed record.
    if require_targets:
        valid_mask = target_df.notna().all(axis=1) & features_df.notna().all(axis=1)
    else:
        # Impute missing next_timestamp for the final row so downstream can project t+1
        missing_next = data["next_timestamp"].isna()
        data.loc[missing_next, "next_timestamp"] = data.loc[missing_next, "timestamp"] + pd.Timedelta(days=1)
        data.loc[missing_next, "time_gap_days"] = 1.0
        valid_mask = features_df.notna().all(axis=1)

    clean_X = features_df.loc[valid_mask].reset_index(drop=True)
    clean_y = target_df.loc[valid_mask].reset_index(drop=True)

    meta_cols = ["Machine_number", "timestamp", "next_timestamp", "time_gap_days"]
    clean_meta = data.loc[valid_mask, meta_cols].reset_index(drop=True)

    feature_names = list(clean_X.columns)
    target_names = list(clean_y.columns)

    return clean_X, clean_y, feature_names, target_names, clean_meta


def split_chronological(
    X: pd.DataFrame,
    y: pd.DataFrame,
    meta_df: pd.DataFrame,
    train_ratio: float = 0.8,
    split_date: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Performs strict chronological train/test split per machine or by calendar cutoff.
    Prevents lookahead leakage.

    Returns:
    --------
    X_train, y_train, meta_train, X_test, y_test, meta_test
    """
    if split_date is not None:
        cutoff = pd.to_datetime(split_date)
        train_mask = meta_df["timestamp"] < cutoff
        test_mask = meta_df["timestamp"] >= cutoff
    else:
        # Chronological per machine
        train_indices = []
        test_indices = []
        for m_id, grp in meta_df.groupby("Machine_number"):
            n_samples = len(grp)
            n_train = int(n_samples * train_ratio)
            sorted_indices = grp.sort_values("timestamp").index
            train_indices.extend(sorted_indices[:n_train])
            test_indices.extend(sorted_indices[n_train:])

        train_mask = meta_df.index.isin(train_indices)
        test_mask = meta_df.index.isin(test_indices)

    X_train = X.loc[train_mask].reset_index(drop=True)
    y_train = y.loc[train_mask].reset_index(drop=True)
    meta_train = meta_df.loc[train_mask].reset_index(drop=True)

    X_test = X.loc[test_mask].reset_index(drop=True)
    y_test = y.loc[test_mask].reset_index(drop=True)
    meta_test = meta_df.loc[test_mask].reset_index(drop=True)

    return X_train, y_train, meta_train, X_test, y_test, meta_test
