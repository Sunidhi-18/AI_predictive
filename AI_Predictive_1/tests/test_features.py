"""
test_features.py
----------------
Automated unit tests for signal feature extraction, rolling trend calculations,
directional ratios, and spectral order analysis.
"""

import unittest
import numpy as np
import pandas as pd
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.features.telemetry_features import (
    calculate_rolling_telemetry_features,
    calculate_directional_ratios
)
from pump_pm.features.spectrum_features import (
    calculate_rms_spectrum,
    extract_spectral_order_features,
    generate_time_waveform
)


class TestFeatures(unittest.TestCase):

    def test_rolling_telemetry_features(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "machine_id": ["M1201"] * 10,
            "timestamp": dates,
            "location_id": ["P1"] * 10,
            "location_name": ["P-NDE"] * 10,
            "direction": ["V"] * 10,
            "vibration_rms": [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8],
            "temperature_c": [45.0 + i for i in range(10)],
            "provenance": ["TEST"] * 10,
            "quality_flag": ["VALID"] * 10
        })

        res = calculate_rolling_telemetry_features(df, window_days=5)
        self.assertIn("vib_rolling_mean_7d", res.columns)
        self.assertIn("vib_rolling_std_7d", res.columns)
        self.assertIn("vib_rate_of_change_1d", res.columns)
        # Check rate of change: consecutive diff is 0.2
        self.assertAlmostEqual(res["vib_rate_of_change_1d"].iloc[1], 0.2, places=3)

    def test_directional_ratios(self):
        df = pd.DataFrame({
            "Machine_number": ["M1201"],
            "time stamp": ["2024-01-01"],
            "P1-H": [8.0],
            "P1-V": [6.0],
            "P1-A": [2.0],
            "P2-A": [6.0],
            "P3-A": [3.0]
        })
        res = calculate_directional_ratios(df)
        # Radial avg = (8.0 + 6.0) / 2 = 7.0; Axial = 2.0 -> Ratio ~ 3.5
        self.assertAlmostEqual(res["P1_radial_to_axial_ratio"].iloc[0], 3.5, places=1)
        # H / V ratio = 8.0 / 6.0 = 1.333
        self.assertAlmostEqual(res["P1_h_to_v_ratio"].iloc[0], 1.333, places=2)
        # Coupling axial ratio = 6.0 / 3.0 = 2.0
        self.assertAlmostEqual(res["coupling_axial_ratio"].iloc[0], 2.0, places=1)

    def test_spectrum_and_order_extraction(self):
        # 3000 RPM -> Running frequency = 50 Hz
        rpm = 3000.0
        sample_rate = 2048
        t, sig = generate_time_waveform("imbalance", rpm=rpm, duration_sec=2.0, sample_rate_hz=sample_rate, seed=42)

        freqs, rms_amp = calculate_rms_spectrum(sig, sample_rate_hz=sample_rate)
        self.assertTrue(len(freqs) > 0)
        self.assertEqual(len(freqs), len(rms_amp))

        orders = extract_spectral_order_features(freqs, rms_amp, rpm=rpm, tolerance_hz=1.0)
        self.assertEqual(orders["rpm"], 3000.0)
        self.assertEqual(orders["running_frequency_hz"], 50.0)
        # In imbalance scenario, 1x peak should be dominant (> 6.0 mm/s RMS)
        self.assertGreater(orders["amp_1x_mm_s"], 6.0)
        # 1x to overall ratio should be high (> 0.8)
        self.assertGreater(orders["ratio_1x_to_overall"], 0.8)

    def test_misalignment_2x_harmonic(self):
        # Misalignment scenario should have prominent 2x running speed component
        rpm = 3000.0
        sample_rate = 2048
        t, sig = generate_time_waveform("misalignment", rpm=rpm, duration_sec=2.0, sample_rate_hz=sample_rate, seed=42)
        freqs, rms_amp = calculate_rms_spectrum(sig, sample_rate_hz=sample_rate)
        orders = extract_spectral_order_features(freqs, rms_amp, rpm=rpm, tolerance_hz=1.0)

        # 2x component should be significant (> 2.5 mm/s)
        self.assertGreater(orders["amp_2x_mm_s"], 2.5)
        # ratio 2x to 1x should be > 0.4
        self.assertGreater(orders["ratio_2x_to_1x"], 0.4)


if __name__ == "__main__":
    unittest.main()
