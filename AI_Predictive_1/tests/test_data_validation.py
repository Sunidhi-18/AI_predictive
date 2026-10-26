"""
test_data_validation.py
-----------------------
Automated unit tests for data ingestion, schema validation, quarantine handling,
cleaning, and long-form transformation. Compatible with both pytest and unittest.
"""

import os
import unittest
import tempfile
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.ingestion.loaders import standardize_telemetry_columns
from pump_pm.ingestion.validation import validate_and_quarantine_telemetry
from pump_pm.processing.cleaning import clean_telemetry
from pump_pm.processing.transformations import normalize_to_long_form


class TestDataValidation(unittest.TestCase):

    def setUp(self):
        self.sample_telemetry_df = pd.DataFrame({
            "Machine_number": ["M1201", "M1201", np.nan, "M1202", "M1203"],
            "time stamp": ["2024-01-01", "2024-01-02", "2024-01-03", None, "2024-01-05"],
            "P1-V": [3.5, 4.2, 5.1, 4.0, 99.0],  # 99.0 violates physical range <= 50.0
            "P1-H": [3.6, 4.1, 5.0, 4.2, 3.8],
            "P1-A": [3.0, 3.8, 4.5, 3.5, 3.2],
            "P1-T": [45.0, 48.0, 50.0, 44.0, 46.0],
            "P2-V": [3.7, 4.0, 5.2, 4.1, 3.9],
            "P2-H": [3.8, 4.2, 5.3, 4.3, 4.0],
            "P2-A": [3.1, 3.9, 4.6, 3.6, 3.3],
            "P2-T": [46.0, 49.0, 51.0, 45.0, 47.0],
            "P3-V": [3.4, 3.9, 5.0, 3.8, 3.6],
            "P3-H": [3.5, 4.0, 5.1, 4.0, 3.7],
            "P3-A": [2.9, 3.7, 4.4, 3.4, 3.1],
            "P3-T": [44.0, 47.0, 49.0, 43.0, 45.0],
            "P4-V": [3.3, 3.8, 4.9, 3.7, 3.5],
            "P4-H": [3.4, 3.9, 5.0, 3.9, 3.6],
            "P4-A": [2.8, 3.6, 4.3, 3.3, 3.0],
            "P4-T": [43.0, 46.0, 48.0, 42.0, 44.0],
        })

    def test_standardize_telemetry_columns(self):
        df = pd.DataFrame({
            "machine_number": ["M1201"],
            "timestamp": ["2024-01-01"],
            "p1-v": [3.5]
        })
        res = standardize_telemetry_columns(df)
        self.assertIn("Machine_number", res.columns)
        self.assertIn("time stamp", res.columns)
        self.assertIn("P1-V", res.columns)

    def test_validate_and_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            q_dir = os.path.join(tmp_dir, "quarantine")
            valid_df, quarantined_df, report = validate_and_quarantine_telemetry(
                self.sample_telemetry_df, source_name="test_source", quarantine_dir=q_dir
            )

            # In sample_telemetry_df:
            # Row 0: Valid
            # Row 1: Valid
            # Row 2: Missing Machine_number -> Quarantined
            # Row 3: Missing time stamp -> Quarantined
            # Row 4: P1-V is 99.0 (exceeds physical 50.0 mm/s limit) -> Quarantined
            self.assertEqual(len(valid_df), 2)
            self.assertEqual(len(quarantined_df), 3)
            self.assertEqual(report.total_records, 5)
            self.assertEqual(report.valid_records, 2)
            self.assertEqual(report.quarantined_records, 3)
            self.assertEqual(report.missing_machine_ids, 1)
            self.assertEqual(report.missing_timestamps, 1)
            self.assertEqual(report.out_of_range_values, 1)

            # Check quarantine log file created
            self.assertTrue(os.path.exists(os.path.join(q_dir, "quarantined_records.csv")))
            self.assertTrue(os.path.exists(os.path.join(q_dir, "quarantine_log.csv")))

    def test_clean_telemetry(self):
        df = pd.DataFrame({
            "Machine_number": ["M1201", "M1201", "M1201"],
            "time stamp": ["2024-01-01", "2024-01-01", "2024-01-02"],  # Duplicate row 0 & 1
            "P1-V": [3.5, 3.5, np.nan],  # row 2 has missing P1-V
            "P1-H": [3.2, 3.2, 3.4],
            "P1-A": [2.9, 2.9, 3.0],
            "P1-T": [45.0, 45.0, 46.0]
        })
        imputed_df, metrics = clean_telemetry(df)
        self.assertEqual(metrics["duplicate_rows_removed"], 1)
        self.assertEqual(len(imputed_df), 2)
        # Check that missing P1-V was imputed
        self.assertFalse(np.isnan(imputed_df.iloc[1]["P1-V"]))

    def test_normalize_to_long_form(self):
        df = pd.DataFrame({
            "Machine_number": ["M1201"],
            "time stamp": ["2024-01-01"],
            "P1-V": [3.5], "P1-H": [3.2], "P1-A": [2.9], "P1-T": [45.0],
            "P2-V": [3.8], "P2-H": [3.4], "P2-A": [3.1], "P2-T": [47.0],
            "P3-V": [3.3], "P3-H": [3.0], "P3-A": [2.7], "P3-T": [43.0],
            "P4-V": [3.1], "P4-H": [2.8], "P4-A": [2.5], "P4-T": [41.0],
        })
        long_df = normalize_to_long_form(df, provenance="TEST")
        # 4 locations (P1-P4) x 3 directions (V, H, A) = 12 rows
        self.assertEqual(len(long_df), 12)
        self.assertEqual(set(long_df["location_id"].unique()), {"P1", "P2", "P3", "P4"})
        self.assertEqual(set(long_df["direction"].unique()), {"V", "H", "A"})
        self.assertEqual(long_df["provenance"].iloc[0], "TEST")


if __name__ == "__main__":
    unittest.main()
