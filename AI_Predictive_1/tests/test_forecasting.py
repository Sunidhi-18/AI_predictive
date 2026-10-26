"""
test_forecasting.py
-------------------
Unit tests for data engineering, leak-free target generation, machine separation,
time gap validation, forecasting models, and predicted ISO 10816-7 zone assessment.
"""

import unittest
import os
import sys
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.forecasting.data_engineering import (
    prepare_forecasting_dataset,
    split_chronological,
    DEFAULT_TARGET_CHANNELS
)

from pump_pm.forecasting.models import (
    SensorForecaster,
    PersistenceBaseline,
    RidgeRegressionBaseline
)
from pump_pm.forecasting.predicted_zones import (
    assess_predicted_telemetry,
    compare_current_and_predicted_zones,
    NOT_EVALUABLE_MESSAGE
)


class TestForecasting(unittest.TestCase):

    def setUp(self):
        # Build synthetic 2-machine dataset for testing
        dates_m1 = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(15)]
        dates_m2 = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(15)]

        rows = []
        for d in dates_m1:
            row = {"Machine_number": "M1201", "time stamp": d.strftime("%Y-%m-%d")}
            for ch in DEFAULT_TARGET_CHANNELS:
                row[ch] = 2.0 + np.sin(d.day) * 0.5
            rows.append(row)

        for d in dates_m2:
            row = {"Machine_number": "M1202", "time stamp": d.strftime("%Y-%m-%d")}
            for ch in DEFAULT_TARGET_CHANNELS:
                row[ch] = 3.0 + np.cos(d.day) * 0.5
            rows.append(row)

        self.df_sample = pd.DataFrame(rows)

    def test_machine_separation_no_leakage(self):
        """
        Target for the final day of Machine M1201 must NEVER be the first day of M1202.
        It must be NaN and filtered out.
        """
        X, y, feats, targets, meta = prepare_forecasting_dataset(
            self.df_sample,
            target_channels=DEFAULT_TARGET_CHANNELS,
            max_gap_days=1.0,
            lags=[1, 2],
            rolling_windows=[3]
        )

        # In meta, check the last sample for M1201
        m1_meta = meta[meta["Machine_number"] == "M1201"]
        m2_meta = meta[meta["Machine_number"] == "M1202"]

        # Max timestamp for M1201 in meta must be Jan 14 (Jan 15 has no target, so dropped)
        self.assertEqual(m1_meta["timestamp"].max(), pd.to_datetime("2024-01-14"))
        self.assertEqual(m1_meta["next_timestamp"].max(), pd.to_datetime("2024-01-15"))

        # Verify next_timestamp for M1201 is NEVER an M1202 date or cross-machine record
        self.assertTrue(all(t < pd.to_datetime("2024-01-16") for t in m1_meta["next_timestamp"]))

    def test_time_gaps_invalidation(self):
        """
        If there is an irregular time gap (> 1 day), no target must be created
        across the missing interval.
        """
        # Create dataset with intentional 4-day gap between Jan 5 and Jan 10
        dates_with_gap = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
            datetime(2024, 1, 5),
            # Gap! Next date is Jan 10
            datetime(2024, 1, 10),
            datetime(2024, 1, 11),
            datetime(2024, 1, 12)
        ]
        rows = []
        for d in dates_with_gap:
            row = {"Machine_number": "M1201", "time stamp": d.strftime("%Y-%m-%d")}
            for ch in DEFAULT_TARGET_CHANNELS:
                row[ch] = 2.5
            rows.append(row)
        gap_df = pd.DataFrame(rows)

        X, y, feats, targets, meta = prepare_forecasting_dataset(
            gap_df,
            target_channels=DEFAULT_TARGET_CHANNELS,
            max_gap_days=1.0,
            lags=[1],
            rolling_windows=[2]
        )

        # Jan 5 must NOT appear in meta['timestamp'] because its next date is Jan 10 (gap = 5 days)
        timestamps = meta["timestamp"].tolist()
        self.assertNotIn(pd.to_datetime("2024-01-05"), timestamps)

        # All time_gap_days in meta must be exactly 1.0 day
        for gap in meta["time_gap_days"]:
            self.assertEqual(gap, 1.0)

    def test_no_lookahead_data_leakage(self):
        """
        Features at time t must only be functions of data <= t.
        """
        X, y, feats, targets, meta = prepare_forecasting_dataset(
            self.df_sample,
            target_channels=["P1-V"],
            max_gap_days=1.0,
            lags=[1, 2],
            rolling_windows=[3]
        )

        # Verify lag 1 is strictly previous day value
        for i in range(1, len(meta)):
            if meta.iloc[i]["Machine_number"] == meta.iloc[i-1]["Machine_number"]:
                prev_val = X.iloc[i-1]["P1-V_curr"]
                lag1_val = X.iloc[i]["P1-V_lag1"]
                self.assertAlmostEqual(prev_val, lag1_val, places=4)

    def test_persistence_baseline(self):
        """
        Persistence baseline must return y_hat = y_t.
        """
        X, y, feats, targets, meta = prepare_forecasting_dataset(
            self.df_sample,
            target_channels=["P1-V", "P2-H"],
            max_gap_days=1.0,
            lags=[1],
            rolling_windows=[2]
        )
        baseline = PersistenceBaseline(target_names=targets)
        preds = baseline.predict(X)

        self.assertEqual(preds.shape, (len(X), 2))
        np.testing.assert_array_almost_equal(preds[:, 0], X["P1-V_curr"].values)
        np.testing.assert_array_almost_equal(preds[:, 1], X["P2-H_curr"].values)

        metrics = baseline.evaluate(X, y)
        self.assertIn("overall_mae", metrics)
        self.assertIn("overall_rmse", metrics)

    def test_random_forest_forecaster(self):
        """
        SensorForecaster must train, predict, evaluate, and serialize cleanly.
        """
        X, y, feats, targets, meta = prepare_forecasting_dataset(
            self.df_sample,
            target_channels=["P1-V", "P2-H", "P3-A"],
            max_gap_days=1.0,
            lags=[1],
            rolling_windows=[2]
        )
        forecaster = SensorForecaster(
            target_names=targets,
            feature_names=feats,
            n_estimators=10,
            max_depth=4,
            random_state=42
        )
        forecaster.fit(X, y)
        preds = forecaster.predict(X)
        self.assertEqual(preds.shape, (len(X), 3))

        metrics = forecaster.evaluate(X, y)
        self.assertLess(metrics["overall_mae"], 1.5)

        # Test save & load in a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            m_path = os.path.join(tmp_dir, "model.pkl")
            c_path = os.path.join(tmp_dir, "config.json")
            forecaster.save(m_path, c_path)

            loaded = SensorForecaster.load(m_path, c_path)
            loaded_preds = loaded.predict(X)
            np.testing.assert_array_almost_equal(preds, loaded_preds)

    def test_predicted_zone_assessment(self):
        """
        Passing high predicted vibration to assess_predicted_telemetry
        must trigger ISO Zone C/D assessment under machine M1201 rules.
        """
        # M1201 is Cat 1, 160 kW (<= 200 kW): Zone B limit is 4.0 mm/s, Zone C limit is 6.6 mm/s
        normal_preds = {"P1-V": 2.2, "P2-H": 2.5, "P3-V": 2.1, "P4-H": 2.0}
        res_norm = assess_predicted_telemetry("M1201", normal_preds)
        self.assertIn("Zone A", res_norm["governing_zone"])

        # High vibration prediction (7.8 mm/s on P2-H -> Zone D)
        high_preds = {"P1-V": 2.2, "P2-H": 7.8, "P3-V": 2.1, "P4-H": 2.0}
        res_high = assess_predicted_telemetry("M1201", high_preds)
        self.assertIn("Zone D", res_high["governing_zone"])
        self.assertEqual(res_high["governing_location"], "P2")

    def test_missing_config_refusal_for_forecast(self):
        """
        For machine M1205 (category: null, nominal_power_kw: null),
        predicted zone assessment must refuse evaluation with NOT_EVALUABLE_MESSAGE.
        """
        high_preds = {"P1-V": 2.2, "P2-H": 7.8, "P3-V": 2.1, "P4-H": 2.0}
        res = assess_predicted_telemetry("M1205", high_preds)
        self.assertEqual(res["governing_zone"], NOT_EVALUABLE_MESSAGE)


if __name__ == "__main__":
    unittest.main()
