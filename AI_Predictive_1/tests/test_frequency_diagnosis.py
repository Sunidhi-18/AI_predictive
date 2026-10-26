import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.diagnostics.frequency_diagnosis import (
    analyse_waveform,
    map_event_to_target_scenario,
)


class TestFrequencyDiagnosis(unittest.TestCase):
    def test_imbalance_pattern(self):
        result = analyse_waveform("rotor_imbalance", 3000, "P2", "H", 48, 65, seed=11)
        self.assertEqual(result["diagnosis"]["condition"], "Rotor imbalance")
        self.assertGreater(result["features"]["amp_1x_mm_s"], result["features"]["amp_2x_mm_s"])

    def test_misalignment_pattern(self):
        result = analyse_waveform("shaft_misalignment", 3000, "P2", "A", 48, 65, seed=12)
        self.assertEqual(result["diagnosis"]["condition"], "Shaft misalignment")
        self.assertGreater(result["features"]["amp_2x_mm_s"], result["features"]["amp_1x_mm_s"])

    def test_high_frequency_and_temperature_both_required(self):
        hot = analyse_waveform("high_frequency_high_temperature", 3000, "P2", "H", 80, 65, seed=13)
        cool = analyse_waveform("high_frequency_high_temperature", 3000, "P2", "H", 50, 65, seed=13)
        self.assertEqual(hot["diagnosis"]["condition"], "High-frequency vibration + high temperature")
        self.assertNotEqual(cool["diagnosis"]["condition"], "High-frequency vibration + high temperature")

    def test_event_mapping(self):
        self.assertEqual(map_event_to_target_scenario("rotor_imbalance"), "rotor_imbalance")
        self.assertEqual(map_event_to_target_scenario("shaft_misalignment"), "shaft_misalignment")
        self.assertEqual(map_event_to_target_scenario("bearing_defect_thermal"), "high_frequency_high_temperature")
        self.assertIsNone(map_event_to_target_scenario("hydraulic_cavitation"))


if __name__ == "__main__":
    unittest.main()
