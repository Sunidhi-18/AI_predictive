"""
test_reports.py
---------------
Automated unit tests for CSV and PDF report generation.
"""

import unittest
import tempfile
import os, sys
import pymupdf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.reporting.report_generator import generate_csv_summary, generate_pdf_report


class TestReports(unittest.TestCase):

    def setUp(self):
        self.sample_events = [
            {
                "event_id": 101,
                "machine_id": "M1201",
                "timestamp": "2024-04-15",
                "severity_zone": "Zone D (Hazardous / Damage risk)",
                "alarm_status": "TRIP",
                "max_vibration": 8.8,
                "dominant_location": "P1",
                "candidate_faults": [{"fault_name": "Rotor Imbalance", "confidence_score": 0.85}],
                "supporting_evidence": ["Dominant 1x radial velocity"],
                "missing_evidence": ["Phase survey"],
                "anomaly_score": -0.15,
                "status": "OPEN",
                "acknowledged_by": None,
                "action_taken": None
            }
        ]
        self.machine_meta = {
            "name": "Boiler Feed Pump #1",
            "category": "category_1",
            "nominal_power_kw": 160.0,
            "rated_speed_rpm": 3000
        }

    def test_generate_csv_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "test_summary.csv")
            csv_str = generate_csv_summary(self.sample_events, output_path=csv_path)

            self.assertTrue(os.path.exists(csv_path))
            self.assertIn("M1201", csv_str)
            self.assertIn("Rotor Imbalance", csv_str)
            self.assertIn("Zone D", csv_str)
            self.assertIn("ACADEMIC_PROTOTYPE_SIMULATION", csv_str)

    def test_generate_pdf_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test_report.pdf")
            res_path = generate_pdf_report("M1201", self.machine_meta, self.sample_events, pdf_path)

            self.assertTrue(os.path.exists(res_path))
            self.assertGreater(os.path.getsize(res_path), 1000)

            # Open with pymupdf and verify contents
            doc = pymupdf.open(res_path)
            try:
                self.assertEqual(len(doc), 1)
                text = doc[0].get_text()
                self.assertIn("CONDITION MONITORING REPORT", text)
                self.assertIn("ACADEMIC ENGINEERING PROTOTYPE", text)
                self.assertIn("M1201", text)
                self.assertIn("Rotor Imbalance", text)
            finally:
                doc.close()


if __name__ == "__main__":
    unittest.main()
