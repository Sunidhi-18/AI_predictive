"""
schemas.py
----------
Data schemas and contract definitions for raw and processed ingestion.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


RAW_TELEMETRY_COLUMNS = [
    "Machine_number", "time stamp",
    "P1-V", "P1-H", "P1-A", "P1-T",
    "P2-V", "P2-H", "P2-A", "P2-T",
    "P3-V", "P3-H", "P3-A", "P3-T",
    "P4-V", "P4-H", "P4-A", "P4-T"
]

SPECTRUM_COLUMNS = [
    "Machine_number", "Timestamp", "RPM", "Running_frequency_Hz",
    "Location", "Direction", "Frequency_Hz", "Frequency_Order",
    "Velocity_RMS_mm_s", "Overall_RMS_mm_s"
]

PHYSICAL_LIMITS = {
    "vibration_rms_min": 0.0,
    "vibration_rms_max": 50.0,    # mm/s RMS
    "temperature_c_min": -10.0,
    "temperature_c_max": 150.0,   # deg C
}


@dataclass
class DataQualityReport:
    source_file: str
    total_records: int = 0
    valid_records: int = 0
    quarantined_records: int = 0
    total_cells: int = 0
    missing_cells: int = 0
    missing_percentage: float = 0.0
    missing_machine_ids: int = 0
    missing_timestamps: int = 0
    out_of_range_values: int = 0
    duplicate_rows: int = 0
    missing_by_column: Dict[str, int] = field(default_factory=dict)
    quarantine_reasons: Dict[str, int] = field(default_factory=dict)
    machines_present: List[str] = field(default_factory=list)
    date_start: Optional[str] = None
    date_end: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "quarantined_records": self.quarantined_records,
            "total_cells": self.total_cells,
            "missing_cells": self.missing_cells,
            "missing_percentage": round(self.missing_percentage, 2),
            "missing_machine_ids": self.missing_machine_ids,
            "missing_timestamps": self.missing_timestamps,
            "out_of_range_values": self.out_of_range_values,
            "duplicate_rows": self.duplicate_rows,
            "missing_by_column": self.missing_by_column,
            "quarantine_reasons": self.quarantine_reasons,
            "machines_present": self.machines_present,
            "date_start": self.date_start,
            "date_end": self.date_end
        }
