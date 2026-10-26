"""Frequency-based diagnosis for the project's three target conditions.

This module generates explicitly synthetic waveforms for demonstration/testing,
extracts FFT features, and applies transparent heuristic rules. It is not a
substitute for measured vibration waveforms or a validated fault classifier.
"""
from __future__ import annotations

from typing import Dict, Tuple, Any
import numpy as np

from ..features.spectrum_features import (
    calculate_rms_spectrum,
    extract_spectral_order_features,
)

TARGET_SCENARIOS = {
    "healthy": "Healthy / no target fault pattern",
    "rotor_imbalance": "Rotor imbalance",
    "shaft_misalignment": "Shaft misalignment",
    "high_frequency_high_temperature": "High-frequency vibration + high temperature",
}

EVENT_SCENARIO_MAP = {
    "rotor_imbalance": "rotor_imbalance",
    "shaft_misalignment": "shaft_misalignment",
    "bearing_defect_thermal": "high_frequency_high_temperature",
    "bearing_defect": "high_frequency_high_temperature",
}


def map_event_to_target_scenario(event_name: str) -> str | None:
    """Map known synthetic event labels to the three project target scenarios.

    Returns None when an event is outside the three target classes.
    """
    return EVENT_SCENARIO_MAP.get(str(event_name).strip().lower())


def generate_target_waveform(
    scenario: str,
    rpm: float,
    location: str = "P2",
    direction: str = "H",
    sample_rate_hz: int = 4096,
    duration_sec: float = 2.0,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a repeatable synthetic vibration velocity waveform in mm/s.

    The signal is deliberately simulated to demonstrate the workflow. It is not
    reconstructed from daily RMS readings and must not be represented as field data.
    """
    if rpm <= 0:
        raise ValueError("rpm must be positive")
    if sample_rate_hz < 2 * (15 * rpm / 60):
        raise ValueError("sample rate is too low for the synthetic high-frequency components")
    if scenario not in TARGET_SCENARIOS:
        raise ValueError(f"Unsupported scenario: {scenario}")

    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration_sec, 1.0 / sample_rate_hz)
    f1 = rpm / 60.0
    sig = np.zeros_like(t)

    # Location and direction scaling simulates propagation through the coupled set.
    loc = location.upper()
    direction = direction.upper()
    loc_scale = {
        "P1": 1.05, "P2": 1.20, "P3": 1.15, "P4": 0.90
    }.get(loc, 1.0)

    if scenario == "healthy":
        amp1, amp2, amp3 = 1.6, 0.25, 0.12
        hf_scale = 0.12
    elif scenario == "rotor_imbalance":
        # Radial 1x is deliberately dominant; stronger on pump-side locations.
        loc_scale *= 1.15 if loc in {"P1", "P2"} else 0.60
        amp1, amp2, amp3 = 6.5, 0.45, 0.18
        hf_scale = 0.12
    elif scenario == "shaft_misalignment":
        # Both 1x and 2x are present; axial vibration is enhanced.
        loc_scale *= 1.25 if loc in {"P2", "P3"} else 0.75
        amp1, amp2, amp3 = 3.6, 3.0, 0.75
        if direction == "A":
            amp1, amp2, amp3 = 2.8, 4.2, 0.9
        hf_scale = 0.15
    else:  # high_frequency_high_temperature
        amp1, amp2, amp3 = 1.5, 0.45, 0.20
        hf_scale = 1.0
        if loc == "P2":
            hf_scale *= 1.25

    # Axial 1x from imbalance is much weaker than radial 1x.
    if scenario == "rotor_imbalance" and direction == "A":
        amp1 *= 0.22
        amp2 *= 0.60
    elif scenario == "rotor_imbalance" and direction in {"H", "V"}:
        amp1 *= 1.0
    elif scenario == "healthy" and direction == "A":
        amp1 *= 0.70

    phase1, phase2, phase3 = rng.uniform(0, 2 * np.pi, size=3)
    sig += amp1 * np.sqrt(2) * np.sin(2 * np.pi * f1 * t + phase1)
    sig += amp2 * np.sqrt(2) * np.sin(2 * np.pi * 2 * f1 * t + phase2)
    sig += amp3 * np.sqrt(2) * np.sin(2 * np.pi * 3 * f1 * t + phase3)

    if scenario == "high_frequency_high_temperature":
        # Broad synthetic high-frequency content above the 3.5x order band.
        for order, amp in [(8.0, 0.95), (10.0, 0.80), (13.0, 0.65), (16.0, 0.45)]:
            sig += amp * hf_scale * np.sqrt(2) * np.sin(
                2 * np.pi * order * f1 * t + rng.uniform(0, 2 * np.pi)
            )
        # Low-level broadband component simulates irregular impacts/noise.
        sig += rng.normal(0, 0.32 * hf_scale, size=len(t))
    else:
        sig += rng.normal(0, 0.06, size=len(t))

    return t, sig * loc_scale


def analyse_waveform(
    scenario: str,
    rpm: float,
    location: str,
    direction: str,
    temperature_c: float,
    temperature_warning_c: float = 65.0,
    sample_rate_hz: int = 4096,
    duration_sec: float = 2.0,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generate a demo waveform, calculate FFT features, and diagnose its pattern."""
    t, signal = generate_target_waveform(
        scenario=scenario,
        rpm=rpm,
        location=location,
        direction=direction,
        sample_rate_hz=sample_rate_hz,
        duration_sec=duration_sec,
        seed=seed,
    )
    freqs, amps = calculate_rms_spectrum(signal, sample_rate_hz=sample_rate_hz)
    features = extract_spectral_order_features(freqs, amps, rpm=rpm, tolerance_hz=1.0)
    diagnosis = diagnose_features(
        features,
        temperature_c=temperature_c,
        direction=direction,
        temperature_warning_c=temperature_warning_c,
    )
    return {
        "time_seconds": t,
        "signal_mm_s": signal,
        "frequencies_hz": freqs,
        "amplitudes_rms_mm_s": amps,
        "features": features,
        "diagnosis": diagnosis,
        "scenario_used_for_simulation": scenario,
        "temperature_c": float(temperature_c),
        "temperature_warning_c": float(temperature_warning_c),
        "provenance": "SYNTHETIC_SIMULATION",
        "sample_rate_hz": int(sample_rate_hz),
    }


def diagnose_features(
    features: Dict[str, float],
    temperature_c: float,
    direction: str,
    temperature_warning_c: float = 65.0,
) -> Dict[str, Any]:
    """Transparent rule-based classifier for the three target patterns.

    Thresholds are demonstration heuristics, not standards-based fault limits.
    The ISO vibration zones apply to suitable overall vibration measurements,
    not to these individual FFT amplitudes.
    """
    amp1 = float(features.get("amp_1x_mm_s", 0.0))
    amp2 = float(features.get("amp_2x_mm_s", 0.0))
    ratio1 = float(features.get("ratio_1x_to_overall", 0.0))
    ratio21 = float(features.get("ratio_2x_to_1x", 0.0))
    hf = float(features.get("high_freq_rms_mm_s", 0.0))
    hfr = float(features.get("ratio_hf_to_overall", 0.0))
    direction = direction.upper()
    evidence = []

    # Combined condition requires both the thermal and spectral evidence.
    if temperature_c >= temperature_warning_c and (hf >= 1.0 or hfr >= 0.25):
        evidence.append(
            f"Temperature {temperature_c:.1f}°C is at/above the configured "
            f"warning value {temperature_warning_c:.1f}°C."
        )
        evidence.append(
            f"High-frequency RMS is {hf:.2f} mm/s (HF/overall ratio {hfr:.2f})."
        )
        return {
            "condition": TARGET_SCENARIOS["high_frequency_high_temperature"],
            "status": "TARGET PATTERN DETECTED",
            "confidence": "Rule match; not a calibrated probability",
            "evidence": evidence,
            "rule": "High-frequency vibration AND high temperature",
        }

    if ratio21 >= 0.50 and amp2 >= 1.5:
        evidence.append(f"2x amplitude is {amp2:.2f} mm/s; 2x/1x ratio is {ratio21:.2f}.")
        if direction == "A":
            evidence.append("The selected measurement is axial, which can support a misalignment investigation.")
        else:
            evidence.append("Elevated 2x rotational harmonic supports checking for misalignment; other faults can also cause it.")
        return {
            "condition": TARGET_SCENARIOS["shaft_misalignment"],
            "status": "TARGET PATTERN DETECTED",
            "confidence": "Rule match; not a calibrated probability",
            "evidence": evidence,
            "rule": "Elevated 2x component relative to 1x",
        }

    if direction in {"H", "V"} and ratio1 >= 0.65 and amp1 >= 3.0:
        evidence.append(f"1x amplitude is {amp1:.2f} mm/s.")
        evidence.append(f"1x/overall ratio is {ratio1:.2f}, indicating a dominant running-speed component.")
        evidence.append("A dominant radial 1x component is consistent with an imbalance hypothesis.")
        return {
            "condition": TARGET_SCENARIOS["rotor_imbalance"],
            "status": "TARGET PATTERN DETECTED",
            "confidence": "Rule match; not a calibrated probability",
            "evidence": evidence,
            "rule": "Dominant radial 1x component",
        }

    return {
        "condition": "No target condition detected / insufficient evidence",
        "status": "NO TARGET RULE MATCH",
        "confidence": "Not applicable",
        "evidence": [
            f"1x/overall={ratio1:.2f}; 2x/1x={ratio21:.2f}; "
            f"high-frequency RMS={hf:.2f} mm/s; temperature={temperature_c:.1f}°C.",
            "Review additional sensor directions, other locations, operating conditions and measured spectra before concluding the machine is healthy.",
        ],
        "rule": "None of the three target patterns met the demo rules",
    }
