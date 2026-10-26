"""
test_zone_assessment.py
-----------------------
Automated unit tests for ISO 10816-7 / Europump 2013 Table 1 zone assessment,
boundary conditions, alarm/trip separation, and incomplete configuration refusal.
"""

import unittest
import pandas as pd
import numpy as np

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.standards.zone_assessment import (
    assess_vibration_point,
    assess_machine_telemetry_row,
    NOT_EVALUABLE_MESSAGE
)


class TestZoneAssessment(unittest.TestCase):

    def test_category1_le_200kw_boundaries(self):
        """
        Machine M1201: Category 1, 160 kW (<= 200 kW)
        Zone A: <= 2.5
        Zone B: <= 4.0
        Zone C: <= 6.6
        Zone D: > 6.6
        Alarm: >= 5.0
        Trip: >= 8.3
        """
        # Exactly at Zone A upper boundary
        res_a = assess_vibration_point("M1201", "P1", "V", 2.50)
        self.assertIn("Zone A", res_a.severity_zone)
        self.assertEqual(res_a.alarm_status, "NORMAL")

        # Just crossing into Zone B
        res_b = assess_vibration_point("M1201", "P1", "V", 2.51)
        self.assertIn("Zone B", res_b.severity_zone)
        self.assertEqual(res_b.alarm_status, "NORMAL")

        # At Zone B upper boundary
        res_b_max = assess_vibration_point("M1201", "P1", "V", 4.00)
        self.assertIn("Zone B", res_b_max.severity_zone)
        self.assertEqual(res_b_max.alarm_status, "NORMAL")

        # Crossing into Zone C
        res_c = assess_vibration_point("M1201", "P1", "V", 4.01)
        self.assertIn("Zone C", res_c.severity_zone)

        # Triggering ALARM at 5.0 mm/s (inside Zone C)
        res_alarm = assess_vibration_point("M1201", "P1", "V", 5.00)
        self.assertIn("Zone C", res_alarm.severity_zone)
        self.assertEqual(res_alarm.alarm_status, "ALARM")

        # At Zone C upper boundary
        res_c_max = assess_vibration_point("M1201", "P1", "V", 6.60)
        self.assertIn("Zone C", res_c_max.severity_zone)

        # Crossing into Zone D
        res_d = assess_vibration_point("M1201", "P1", "V", 6.61)
        self.assertIn("Zone D", res_d.severity_zone)
        self.assertEqual(res_d.alarm_status, "ALARM")

        # Exceeding TRIP limit at 8.3 mm/s
        res_trip = assess_vibration_point("M1201", "P1", "V", 8.30)
        self.assertIn("Zone D", res_trip.severity_zone)
        self.assertEqual(res_trip.alarm_status, "TRIP")

    def test_category1_gt_200kw_boundaries(self):
        """
        Machine M1202: Category 1, 250 kW (> 200 kW)
        Zone A: <= 3.5, Zone B: <= 5.0, Zone C: <= 7.6, Zone D: > 7.6
        Alarm: 6.3, Trip: 9.5
        """
        res_a = assess_vibration_point("M1202", "P2", "H", 3.50)
        self.assertIn("Zone A", res_a.severity_zone)

        res_b = assess_vibration_point("M1202", "P2", "H", 5.00)
        self.assertIn("Zone B", res_b.severity_zone)

        res_c = assess_vibration_point("M1202", "P2", "H", 7.60)
        self.assertIn("Zone C", res_c.severity_zone)

        res_d = assess_vibration_point("M1202", "P2", "H", 7.61)
        self.assertIn("Zone D", res_d.severity_zone)

        res_trip = assess_vibration_point("M1202", "P2", "H", 9.55)
        self.assertEqual(res_trip.alarm_status, "TRIP")

    def test_incomplete_configuration_refusal(self):
        """
        Machine M1205 has category=null and nominal_power_kw=null.
        Must refuse assessment with exact standard prompt message.
        """
        res = assess_vibration_point("M1205", "P1", "V", 4.5)
        self.assertEqual(res.severity_zone, NOT_EVALUABLE_MESSAGE)
        self.assertEqual(res.configuration_status, "INCOMPLETE")
        self.assertEqual(res.alarm_status, "UNKNOWN")

    def test_unregistered_machine(self):
        res = assess_vibration_point("M9999", "P1", "V", 3.0)
        self.assertEqual(res.severity_zone, NOT_EVALUABLE_MESSAGE)
        self.assertEqual(res.configuration_status, "UNREGISTERED")

    def test_assess_machine_telemetry_row(self):
        row = pd.Series({
            "Machine_number": "M1201",
            "time stamp": "2024-05-01",
            "P1-V": 2.1, "P1-H": 2.2, "P1-A": 1.9,
            "P2-V": 2.4, "P2-H": 2.3, "P2-A": 2.0,
            "P3-V": 8.5, "P3-H": 2.1, "P3-A": 1.8,  # P3-V is in Zone D and triggers TRIP
            "P4-V": 2.0, "P4-H": 1.9, "P4-A": 1.7,
        })
        assessment = assess_machine_telemetry_row(row)
        self.assertIn("Zone D", assessment["governing_zone"])
        self.assertEqual(assessment["governing_location"], "P3")
        self.assertEqual(assessment["governing_direction"], "V")
        self.assertEqual(assessment["highest_alarm_status"], "TRIP")
        self.assertEqual(len(assessment["points"]), 12)


if __name__ == "__main__":
    unittest.main()
