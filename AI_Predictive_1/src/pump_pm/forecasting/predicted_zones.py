"""
predicted_zones.py
------------------
Standards-based severity assessment for ML-predicted future vibration values.
Passes forecasted vibration readings to the exact same ISO 10816-7 / Europump 2013
rule engine used for current telemetry.

Enforces:
1. Reuses existing configurable standards limits (no ad-hoc threshold invention).
2. Separate reporting of current zones vs predicted future zones.
3. Strict refusal with NOT_EVALUABLE_MESSAGE if machine configuration is incomplete.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

from ..standards.zone_assessment import (
    assess_machine_telemetry_row,
    assess_vibration_point,
    NOT_EVALUABLE_MESSAGE
)


ZONE_RANKS = {
    "Zone A (Good / New commissioning)": 1,
    "Zone B (Acceptable / Unrestricted long-term)": 2,
    "Zone C (Unsatisfactory / Limited continuous operation)": 3,
    "Zone D (Hazardous / Damage risk)": 4,
    NOT_EVALUABLE_MESSAGE: 0,
    "No Data — Measurement missing or corrupted": 0
}


def assess_predicted_telemetry(
    machine_id: str,
    predicted_sensor_values: Dict[str, float],
    forecast_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates ML-predicted vibration values against ISO 10816-7 standards.
    Reuses assess_machine_telemetry_row with zero duplicate threshold definitions.

    Parameters:
    -----------
    machine_id : str
        Target machine ID (e.g. 'M1201').
    predicted_sensor_values : Dict[str, float]
        Dictionary of predicted sensor channels, e.g. {'P1-V': 2.4, 'P2-H': 7.1, ...}
        or with 'pred_' prefix {'pred_P1-V': 2.4, ...}.
    forecast_timestamp : Optional[str]
        Timestamp of the forecasted cycle (t+1).

    Returns:
    --------
    Dict[str, Any] containing predicted governing zone, governing location,
    highest alarm status, and individual point evaluations.
    """
    ts = forecast_timestamp or datetime.now().isoformat()

    # Normalize channel keys (strip 'pred_' or 'target_' prefix if present)
    clean_row = {
        "Machine_number": machine_id,
        "time stamp": ts
    }
    for k, v in predicted_sensor_values.items():
        clean_k = k.replace("pred_", "").replace("target_", "")
        clean_row[clean_k] = float(v) if v is not None and not pd.isna(v) else np.nan

    pred_series = pd.Series(clean_row)
    result = assess_machine_telemetry_row(pred_series)
    result["is_forecast"] = True
    result["assessment_type"] = "PREDICTED_NEXT_DAY_STANDARD_ZONE"

    return result


def get_short_zone_name(z_str: str) -> str:
    """Extracts 'Zone A', 'Zone B', 'Zone C', or 'Zone D' from full standard string."""
    if not z_str or z_str == NOT_EVALUABLE_MESSAGE:
        return "Not Evaluable"
    for z in ["Zone A", "Zone B", "Zone C", "Zone D"]:
        if z in z_str:
            return z
    return z_str.split(' (')[0] if ' (' in z_str else z_str


def compare_current_and_predicted_zones(
    machine_id: str,
    current_row: pd.Series,
    predicted_readings: Dict[str, float],
    forecast_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compares the current observed ISO severity zone with the predicted next-day zone.
    Detects early degradation transitions (e.g. Zone B -> Zone C).
    """
    current_assessment = assess_machine_telemetry_row(current_row)
    predicted_assessment = assess_predicted_telemetry(
        machine_id=machine_id,
        predicted_sensor_values=predicted_readings,
        forecast_timestamp=forecast_timestamp
    )

    curr_zone = current_assessment["governing_zone"]
    pred_zone = predicted_assessment["governing_zone"]

    curr_short = get_short_zone_name(curr_zone)
    pred_short = get_short_zone_name(pred_zone)

    curr_rank = ZONE_RANKS.get(curr_zone, 0)
    pred_rank = ZONE_RANKS.get(pred_zone, 0)

    is_evaluable = (curr_zone != NOT_EVALUABLE_MESSAGE) and (pred_zone != NOT_EVALUABLE_MESSAGE)
    is_degradation = is_evaluable and (pred_rank > curr_rank)
    is_improvement = is_evaluable and (pred_rank < curr_rank)
    is_hazardous = is_evaluable and (pred_rank == 4)

    # Transition alert message
    if not is_evaluable:
        alert_msg = f"Assessment Refused: {NOT_EVALUABLE_MESSAGE}"
        alert_level = "WARNING"
    elif is_hazardous:
        alert_msg = f"CRITICAL EARLY WARNING: Machine is projected to reach Zone D (Hazardous) in next cycle! (Predicted peak: {predicted_assessment['max_vibration_rms']:.2f} mm/s at {predicted_assessment['governing_location']})"
        alert_level = "CRITICAL"
    elif is_degradation:
        alert_msg = f"PREDICTIVE DEGRADATION ALERT: Machine projected to transition from {curr_short} to {pred_short} in next daily cycle."
        alert_level = "WARNING"
    elif is_improvement:
        alert_msg = f"Condition projected to improve from {curr_short} to {pred_short}."
        alert_level = "INFO"
    else:
        alert_msg = f"Operational stability projected: Machine remains in {curr_short}."
        alert_level = "NORMAL"

    return {
        "machine_id": machine_id,
        "is_evaluable": is_evaluable,
        "current_zone": curr_zone,
        "current_zone_short": curr_short,
        "current_peak_vib": current_assessment["max_vibration_rms"],
        "current_location": current_assessment["governing_location"],
        "current_alarm": current_assessment["highest_alarm_status"],
        "predicted_zone": pred_zone,
        "predicted_zone_short": pred_short,
        "predicted_peak_vib": predicted_assessment["max_vibration_rms"],
        "predicted_location": predicted_assessment["governing_location"],
        "predicted_alarm": predicted_assessment["highest_alarm_status"],
        "is_degradation": is_degradation,
        "is_hazardous": is_hazardous,
        "transition_alert": alert_msg,
        "alert_level": alert_level,
        "current_assessment": current_assessment,
        "predicted_assessment": predicted_assessment
    }
