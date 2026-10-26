"""
pump_pm.forecasting
-------------------
Hybrid predictive maintenance forecasting combining multi-output machine learning
with ISO 10816-7 / Europump 2013 standards severity assessment.
"""

from .data_engineering import (
    prepare_forecasting_dataset,
    split_chronological,
    DEFAULT_TARGET_CHANNELS,
    DEFAULT_VIBRATION_CHANNELS
)
from .models import (
    SensorForecaster,
    PersistenceBaseline,
    RidgeRegressionBaseline,
    calculate_metrics
)
from .predicted_zones import (
    assess_predicted_telemetry,
    compare_current_and_predicted_zones,
    get_short_zone_name,
    ZONE_RANKS
)

__all__ = [
    "prepare_forecasting_dataset",
    "split_chronological",
    "DEFAULT_TARGET_CHANNELS",
    "DEFAULT_VIBRATION_CHANNELS",
    "SensorForecaster",
    "PersistenceBaseline",
    "RidgeRegressionBaseline",
    "calculate_metrics",
    "assess_predicted_telemetry",
    "compare_current_and_predicted_zones",
    "get_short_zone_name",
    "ZONE_RANKS"
]
