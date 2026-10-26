"""
test_diagnostics.py
-------------------
Automated unit tests for multi-evidence diagnostic rule engine,
unknown outcome fallbacks, anomaly detection baseline, and model explainability.
"""

import unittest
import pandas as pd
import numpy as np
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.diagnostics.rule_engine import MultiEvidenceRuleEngine
from pump_pm.models.anomaly_detection import AnomalyDetector
from pump_pm.models.explainability import ModelExplainer


class TestDiagnostics(unittest.TestCase):

    def setUp(self):
        self.engine = MultiEvidenceRuleEngine()

    def test_imbalance_candidate(self):
        row = pd.Series({
            "Machine_number": "M1201",
            "time stamp": "2024-04-15",
            "P1-H": 8.5, "P1-V": 8.0, "P1-A": 2.2, "P1-T": 48.0,
            "P2-H": 8.8, "P2-V": 8.2, "P2-A": 2.4, "P2-T": 50.0,
            "P3-H": 3.0, "P3-V": 2.8, "P3-A": 2.0, "P3-T": 46.0,
            "P4-H": 2.5, "P4-V": 2.4, "P4-A": 1.8, "P4-T": 44.0,
        })
        spec = {"ratio_1x_to_overall": 0.85, "ratio_2x_to_1x": 0.05}
        eval_res = self.engine.evaluate("M1201", row, spectrum_features=spec, governing_zone="Zone D")

        self.assertIsNotNone(eval_res.dominant_hypothesis)
        self.assertEqual(eval_res.dominant_hypothesis.fault_name, "Rotor Imbalance")
        self.assertEqual(eval_res.dominant_hypothesis.fault_family, "mechanical")
        self.assertGreater(eval_res.dominant_hypothesis.confidence_score, 0.70)
        self.assertIn("P1", eval_res.dominant_hypothesis.relevant_locations)

    def test_misalignment_candidate(self):
        row = pd.Series({
            "Machine_number": "M1202",
            "time stamp": "2024-08-20",
            "P1-H": 4.0, "P1-V": 3.8, "P1-A": 3.0, "P1-T": 52.0,
            "P2-H": 6.8, "P2-V": 6.5, "P2-A": 7.6, "P2-T": 55.0,  # High coupling axial
            "P3-H": 6.5, "P3-V": 6.2, "P3-A": 7.4, "P3-T": 54.0,  # High coupling axial
            "P4-H": 3.5, "P4-V": 3.2, "P4-A": 2.8, "P4-T": 48.0,
        })
        spec = {"ratio_1x_to_overall": 0.50, "ratio_2x_to_1x": 0.45}
        eval_res = self.engine.evaluate("M1202", row, spectrum_features=spec, governing_zone="Zone C")

        self.assertIsNotNone(eval_res.dominant_hypothesis)
        self.assertEqual(eval_res.dominant_hypothesis.fault_name, "Shaft or Coupling Misalignment")
        self.assertIn("P2", eval_res.dominant_hypothesis.relevant_locations)
        self.assertIn("P3", eval_res.dominant_hypothesis.relevant_locations)

    def test_bearing_thermal_candidate(self):
        row = pd.Series({
            "Machine_number": "M1201",
            "time stamp": "2025-02-15",
            "P1-H": 3.0, "P1-V": 2.8, "P1-A": 2.0, "P1-T": 48.0,
            "P2-H": 8.5, "P2-V": 8.0, "P2-A": 5.0, "P2-T": 86.5,  # Temperature > 85 C alarm
            "P3-H": 3.2, "P3-V": 3.0, "P3-A": 2.2, "P3-T": 50.0,
            "P4-H": 2.8, "P4-V": 2.6, "P4-A": 1.9, "P4-T": 46.0,
        })
        spec = {"high_freq_rms_mm_s": 4.2, "ratio_hf_to_overall": 0.40}
        eval_res = self.engine.evaluate("M1201", row, spectrum_features=spec, governing_zone="Zone D")

        self.assertIsNotNone(eval_res.dominant_hypothesis)
        self.assertIn("Bearing", eval_res.dominant_hypothesis.fault_name)
        self.assertEqual(eval_res.dominant_hypothesis.relevant_locations, ["P2"])

    def test_unknown_insufficient_evidence_outcome(self):
        # Machine in Zone D, but vibration is diffuse without clear imbalance, misalignment or thermal rise
        row = pd.Series({
            "Machine_number": "M1203",
            "time stamp": "2025-05-10",
            "P1-H": 8.8, "P1-V": 8.7, "P1-A": 8.6, "P1-T": 50.0,
            "P2-H": 8.8, "P2-V": 8.7, "P2-A": 8.6, "P2-T": 50.0,
            "P3-H": 8.8, "P3-V": 8.7, "P3-A": 8.6, "P3-T": 50.0,
            "P4-H": 8.8, "P4-V": 8.7, "P4-A": 8.6, "P4-T": 50.0,
        })
        # Empty spectrum context
        eval_res = self.engine.evaluate("M1203", row, spectrum_features={}, governing_zone="Zone D (Hazardous)")

        # Candidate list must contain unknown / inspection required
        candidate_names = [c.fault_name for c in eval_res.candidates]
        self.assertTrue(any("Unknown" in name for name in candidate_names))

    def test_anomaly_detector_and_explainer(self):
        # Create training baseline with sufficient samples for IsolationForest (250 samples)
        np.random.seed(42)
        train_data = []
        for _ in range(250):
            train_data.append({
                "P1-V": np.random.normal(2.5, 0.2), "P1-H": np.random.normal(2.5, 0.2), "P1-A": np.random.normal(2.0, 0.2), "P1-T": np.random.normal(45.0, 1.0),
                "P2-V": np.random.normal(2.6, 0.2), "P2-H": np.random.normal(2.6, 0.2), "P2-A": np.random.normal(2.1, 0.2), "P2-T": np.random.normal(46.0, 1.0),
                "P3-V": np.random.normal(2.4, 0.2), "P3-H": np.random.normal(2.4, 0.2), "P3-A": np.random.normal(1.9, 0.2), "P3-T": np.random.normal(44.0, 1.0),
                "P4-V": np.random.normal(2.3, 0.2), "P4-H": np.random.normal(2.3, 0.2), "P4-A": np.random.normal(1.8, 0.2), "P4-T": np.random.normal(43.0, 1.0),
            })
        df_train = pd.DataFrame(train_data)

        detector = AnomalyDetector(contamination=0.1, random_state=42)
        detector.fit(df_train)
        self.assertTrue(detector.is_fitted)

        # Test an extreme outlier
        outlier_row = pd.Series({
            "P1-V": 2.5, "P1-H": 2.5, "P1-A": 2.0, "P1-T": 45.0,
            "P2-V": 9.5, "P2-H": 10.2, "P2-A": 8.0, "P2-T": 88.0,  # Extreme anomaly
            "P3-V": 2.4, "P3-H": 2.4, "P3-A": 1.9, "P3-T": 44.0,
            "P4-V": 2.3, "P4-H": 2.3, "P4-A": 1.8, "P4-T": 43.0,
        })
        scores, is_anom = detector.predict_scores(pd.DataFrame([outlier_row]))
        self.assertTrue(is_anom[0])

        # Test explainer
        explainer = ModelExplainer(detector)
        attributions = explainer.explain_instance(outlier_row, top_k=3)
        self.assertGreater(len(attributions), 0)
        # Top features should include P2-H, P2-V, or P2-T
        top_feature_names = [a["feature"] for a in attributions]
        self.assertTrue(any(f.startswith("P2-") for f in top_feature_names))


if __name__ == "__main__":
    unittest.main()
