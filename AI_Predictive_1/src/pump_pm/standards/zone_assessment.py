"""
zone_assessment.py
------------------
Standards-based vibration condition assessment compliant with ISO 10816-7:2009
and Europump Guideline Table 1 (page 9).

Enforces machine configuration completeness, decouples severity zones from alarm/trip limits,
and retains granular location/direction results.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

from ..config import get_config


NOT_EVALUABLE_MESSAGE = "Not evaluable — machine configuration or applicable criterion is incomplete"


@dataclass
class AssessmentResult:
    machine_id: str
    measurement_location: str
    measurement_direction: str
    measured_value: float
    unit: str
    severity_zone: str
    alarm_status: str  # NORMAL, ALARM, TRIP, UNKNOWN
    applicable_criterion: str
    configuration_status: str  # CONFIGURED, INCOMPLETE, UNREGISTERED
    source_reference: str
    zone_limits: Dict[str, float]
    alarm_limit: Optional[float]
    trip_limit: Optional[float]
    assessment_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "measurement_location": self.measurement_location,
            "measurement_direction": self.measurement_direction,
            "measured_value": round(float(self.measured_value), 3) if self.measured_value is not None else None,
            "unit": self.unit,
            "severity_zone": self.severity_zone,
            "alarm_status": self.alarm_status,
            "applicable_criterion": self.applicable_criterion,
            "configuration_status": self.configuration_status,
            "source_reference": self.source_reference,
            "zone_limits": self.zone_limits,
            "alarm_limit": self.alarm_limit,
            "trip_limit": self.trip_limit,
            "assessment_timestamp": self.assessment_timestamp,
        }


def assess_vibration_point(
    machine_id: str,
    measurement_location: str,
    measurement_direction: str,
    measured_value: float,
    operating_range: Optional[str] = None,
    assessment_timestamp: Optional[str] = None
) -> AssessmentResult:
    """
    Evaluates a single vibration velocity measurement (mm/s RMS) against ISO 10816-7 / Europump 2013.
    Refuses evaluation if machine configuration (category or rated power) is incomplete.
    """
    cfg = get_config()
    ts = assessment_timestamp or datetime.now().isoformat()
    unit = "mm/s RMS"

    # Handle missing or NaN measured value
    if measured_value is None or pd.isna(measured_value):
        return AssessmentResult(
            machine_id=machine_id,
            measurement_location=measurement_location,
            measurement_direction=measurement_direction,
            measured_value=np.nan,
            unit=unit,
            severity_zone="No Data — Measurement missing or corrupted",
            alarm_status="UNKNOWN",
            applicable_criterion="N/A",
            configuration_status="DATA_MISSING",
            source_reference="ISO 10816-7:2009",
            zone_limits={},
            alarm_limit=None,
            trip_limit=None,
            assessment_timestamp=ts
        )

    # 1. Lookup Machine Configuration
    machine_meta = cfg.get_machine(machine_id)
    if not machine_meta:
        return AssessmentResult(
            machine_id=machine_id,
            measurement_location=measurement_location,
            measurement_direction=measurement_direction,
            measured_value=float(measured_value),
            unit=unit,
            severity_zone=NOT_EVALUABLE_MESSAGE,
            alarm_status="UNKNOWN",
            applicable_criterion="Machine ID not found in equipment registry",
            configuration_status="UNREGISTERED",
            source_reference="ISO 10816-7:2009",
            zone_limits={},
            alarm_limit=None,
            trip_limit=None,
            assessment_timestamp=ts
        )

    category = machine_meta.get("category")
    nominal_power = machine_meta.get("nominal_power_kw")

    # Incomplete configuration validation
    if not category or nominal_power is None or pd.isna(nominal_power) or nominal_power <= 0:
        return AssessmentResult(
            machine_id=machine_id,
            measurement_location=measurement_location,
            measurement_direction=measurement_direction,
            measured_value=float(measured_value),
            unit=unit,
            severity_zone=NOT_EVALUABLE_MESSAGE,
            alarm_status="UNKNOWN",
            applicable_criterion="Missing category or rated power configuration",
            configuration_status="INCOMPLETE",
            source_reference="ISO 10816-7:2009 / Europump 2013 Table 1",
            zone_limits={},
            alarm_limit=None,
            trip_limit=None,
            assessment_timestamp=ts
        )

    # 2. Retrieve Applicable Standard Limits
    limits_meta = cfg.get_standards_limits(category, float(nominal_power))
    if not limits_meta:
        return AssessmentResult(
            machine_id=machine_id,
            measurement_location=measurement_location,
            measurement_direction=measurement_direction,
            measured_value=float(measured_value),
            unit=unit,
            severity_zone=NOT_EVALUABLE_MESSAGE,
            alarm_status="UNKNOWN",
            applicable_criterion=f"Limits definition missing for {category} at {nominal_power} kW",
            configuration_status="INCOMPLETE",
            source_reference="ISO 10816-7:2009",
            zone_limits={},
            alarm_limit=None,
            trip_limit=None,
            assessment_timestamp=ts
        )

    zones = limits_meta.get("zones", {})
    limit_a = float(zones.get("A", 2.5))
    limit_b = float(zones.get("B", 4.0))
    limit_c = float(zones.get("C", 6.6))
    alarm_limit = float(limits_meta.get("alarm_limit", limit_b * 1.25))
    trip_limit = float(limits_meta.get("trip_limit", limit_c * 1.25))
    source_ref = limits_meta.get("source_table", "Europump 2013 Table 1, p. 9")

    criterion_desc = f"{category.replace('_', ' ').title()}, {nominal_power} kW ({'<= 200 kW' if nominal_power <= 200 else '> 200 kW'})"

    # 3. Classify Severity Zone (Exact ISO Boundary logic)
    val = float(measured_value)
    if val <= limit_a:
        zone = "Zone A (Good / New commissioning)"
    elif val <= limit_b:
        zone = "Zone B (Acceptable / Unrestricted long-term)"
    elif val <= limit_c:
        zone = "Zone C (Unsatisfactory / Limited continuous operation)"
    else:
        zone = "Zone D (Hazardous / Damage risk)"

    # 4. Classify Alarm / Trip Status (Independent from Zone)
    if val >= trip_limit:
        alarm_status = "TRIP"
    elif val >= alarm_limit:
        alarm_status = "ALARM"
    else:
        alarm_status = "NORMAL"

    return AssessmentResult(
        machine_id=machine_id,
        measurement_location=measurement_location,
        measurement_direction=measurement_direction,
        measured_value=val,
        unit=unit,
        severity_zone=zone,
        alarm_status=alarm_status,
        applicable_criterion=criterion_desc,
        configuration_status="CONFIGURED",
        source_reference=source_ref,
        zone_limits={"A": limit_a, "B": limit_b, "C": limit_c},
        alarm_limit=alarm_limit,
        trip_limit=trip_limit,
        assessment_timestamp=ts
    )


def assess_machine_telemetry_row(
    row: pd.Series,
    locations: List[str] = ["P1", "P2", "P3", "P4"],
    directions: List[str] = ["V", "H", "A"]
) -> Dict[str, Any]:
    """
    Assesses all measurement points for a given machine telemetry record.
    Returns individual point assessments plus the governing machine condition.
    Does NOT average points; uses the worst-case governing point with full transparency.
    """
    mach_id = str(row.get("Machine_number", ""))
    ts = str(row.get("time stamp", datetime.now().isoformat()))

    point_assessments = []
    zone_ranks = {
        "Zone A (Good / New commissioning)": 1,
        "Zone B (Acceptable / Unrestricted long-term)": 2,
        "Zone C (Unsatisfactory / Limited continuous operation)": 3,
        "Zone D (Hazardous / Damage risk)": 4,
        NOT_EVALUABLE_MESSAGE: 0,
        "No Data — Measurement missing or corrupted": 0
    }

    max_rank = 0
    governing_zone = NOT_EVALUABLE_MESSAGE
    governing_location = "N/A"
    governing_direction = "N/A"
    max_vib_val = 0.0
    highest_alarm = "NORMAL"

    for loc in locations:
        for d in directions:
            col_name = f"{loc}-{d}"
            val = row.get(col_name, np.nan)
            res = assess_vibration_point(
                machine_id=mach_id,
                measurement_location=loc,
                measurement_direction=d,
                measured_value=val,
                assessment_timestamp=ts
            )
            point_assessments.append(res)

            # Check rank
            rank = zone_ranks.get(res.severity_zone, 0)
            if rank > max_rank:
                max_rank = rank
                governing_zone = res.severity_zone
                governing_location = loc
                governing_direction = d
                max_vib_val = res.measured_value or 0.0

            # Alarm hierarchy: TRIP > ALARM > NORMAL
            if res.alarm_status == "TRIP":
                highest_alarm = "TRIP"
            elif res.alarm_status == "ALARM" and highest_alarm != "TRIP":
                highest_alarm = "ALARM"

    return {
        "machine_id": mach_id,
        "timestamp": ts,
        "governing_zone": governing_zone,
        "governing_location": governing_location,
        "governing_direction": governing_direction,
        "max_vibration_rms": max_vib_val,
        "highest_alarm_status": highest_alarm,
        "points": [p.to_dict() for p in point_assessments]
    }
