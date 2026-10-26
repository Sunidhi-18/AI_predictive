"""
spectrum_features.py
--------------------
Digital signal processing and spectral feature extraction for vibration analysis.
Calculates FFT, running speed orders (1x, 2x, 3x, 0.5x), spectral energy ratios,
and bearing defect frequency markers.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd


def calculate_rms_spectrum(
    signal: np.ndarray,
    sample_rate_hz: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes single-sided RMS amplitude spectrum from a discrete time-domain velocity signal.
    """
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    freqs_hz = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)

    # Convert to single-sided peak amplitude
    peak_amp = 2.0 * np.abs(fft_vals) / n
    peak_amp[0] /= 2.0
    if n % 2 == 0:
        peak_amp[-1] /= 2.0

    # Convert peak to RMS (for sinusoidal components: RMS = Peak / sqrt(2))
    rms_amp = peak_amp / np.sqrt(2.0)
    return freqs_hz, rms_amp


def extract_spectral_order_features(
    freqs_hz: np.ndarray,
    rms_amp: np.ndarray,
    rpm: float,
    tolerance_hz: float = 1.0
) -> Dict[str, float]:
    """
    Extracts vibration harmonic order amplitudes and energy ratios from an RMS spectrum.
    - 1x (Running speed)
    - 2x (Misalignment / non-linearity)
    - 3x (Harmonics)
    - 0.5x (Subharmonic / looseness / oil whirl)
    - Total Integrated RMS
    """
    running_freq = rpm / 60.0
    if running_freq <= 0:
        return {}

    overall_rms = np.sqrt(np.sum(rms_amp ** 2))

    def get_order_amplitude(target_order: float) -> float:
        target_f = target_order * running_freq
        mask = np.abs(freqs_hz - target_f) <= tolerance_hz
        if np.any(mask):
            return float(np.max(rms_amp[mask]))
        return 0.0

    amp_1x = get_order_amplitude(1.0)
    amp_2x = get_order_amplitude(2.0)
    amp_3x = get_order_amplitude(3.0)
    amp_sub_half = get_order_amplitude(0.5)

    # High frequency energy (> 3.5x running frequency)
    hf_mask = freqs_hz > (3.5 * running_freq)
    hf_rms = float(np.sqrt(np.sum(rms_amp[hf_mask] ** 2))) if np.any(hf_mask) else 0.0

    # Key diagnostic ratios
    ratio_1x_to_overall = (amp_1x / (overall_rms + 1e-4)) if overall_rms > 0 else 0.0
    ratio_2x_to_1x = (amp_2x / (amp_1x + 1e-4)) if amp_1x > 0 else 0.0
    ratio_hf_to_overall = (hf_rms / (overall_rms + 1e-4)) if overall_rms > 0 else 0.0

    return {
        "rpm": float(rpm),
        "running_frequency_hz": round(float(running_freq), 2),
        "overall_rms_mm_s": round(float(overall_rms), 3),
        "amp_1x_mm_s": round(float(amp_1x), 3),
        "amp_2x_mm_s": round(float(amp_2x), 3),
        "amp_3x_mm_s": round(float(amp_3x), 3),
        "amp_subharmonic_0_5x_mm_s": round(float(amp_sub_half), 3),
        "high_freq_rms_mm_s": round(float(hf_rms), 3),
        "ratio_1x_to_overall": round(float(ratio_1x_to_overall), 3),
        "ratio_2x_to_1x": round(float(ratio_2x_to_1x), 3),
        "ratio_hf_to_overall": round(float(ratio_hf_to_overall), 3)
    }


def generate_time_waveform(
    scenario: str,
    rpm: float = 3000.0,
    duration_sec: float = 2.0,
    sample_rate_hz: int = 2048,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthesizes reproducible raw vibration time-domain velocity waveforms (mm/s)
    under documented engineering scenarios.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(0, duration_sec, 1.0 / sample_rate_hz)
    f1 = rpm / 60.0  # 1x fundamental (e.g. 50 Hz at 3000 RPM)
    signal = np.zeros_like(t)

    if scenario == "healthy":
        # Low 1x baseline (1.8 mm/s peak) + mild background noise
        signal += (1.8 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t + rng.uniform(0, 2 * np.pi))
        signal += (0.2 * np.sqrt(2)) * np.sin(2 * np.pi * (2 * f1) * t)
        signal += rng.normal(0, 0.05, size=len(t))

    elif scenario == "imbalance":
        # Pronounced sinusoidal 1x radial velocity (7.5 mm/s RMS = 10.6 mm/s peak)
        signal += (7.5 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t + rng.uniform(0, 2 * np.pi))
        signal += (0.4 * np.sqrt(2)) * np.sin(2 * np.pi * (2 * f1) * t)
        signal += rng.normal(0, 0.08, size=len(t))

    elif scenario == "misalignment":
        # Prominent 1x (4.5 mm/s) + strong 2x (3.8 mm/s) harmonic
        signal += (4.5 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t + rng.uniform(0, 2 * np.pi))
        signal += (3.8 * np.sqrt(2)) * np.sin(2 * np.pi * (2 * f1) * t + rng.uniform(0, 2 * np.pi))
        signal += (1.2 * np.sqrt(2)) * np.sin(2 * np.pi * (3 * f1) * t)
        signal += rng.normal(0, 0.08, size=len(t))

    elif scenario == "bearing_defect":
        # Mild 1x + sharp high-frequency impacts at BPFO (3.58x = 179 Hz) & BPFI (5.42x = 271 Hz)
        bpfo = 3.58 * f1
        bpfi = 5.42 * f1
        signal += (2.2 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t)
        signal += (1.8 * np.sqrt(2)) * np.sin(2 * np.pi * bpfo * t)
        signal += (1.5 * np.sqrt(2)) * np.sin(2 * np.pi * bpfi * t)
        # Transient repetitive shock impacts
        impact_interval = int(sample_rate_hz / bpfo)
        impacts = np.zeros_like(t)
        for idx in range(0, len(t), impact_interval):
            if idx < len(t):
                decay_len = min(64, len(t) - idx)
                impacts[idx:idx + decay_len] += 2.5 * np.exp(-np.linspace(0, 5, decay_len))
        signal += impacts
        signal += rng.normal(0, 0.15, size=len(t))

    elif scenario == "mechanical_looseness":
        # Multiple synchronous harmonics (1x..8x) + subharmonics (0.5x, 1.5x)
        for h in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]:
            amp = 3.5 / h
            signal += (amp * np.sqrt(2)) * np.sin(2 * np.pi * (h * f1) * t + rng.uniform(0, 2 * np.pi))
        signal += rng.normal(0, 0.12, size=len(t))

    elif scenario == "cavitation":
        # Moderate 1x + wide broadband random high-frequency acoustic noise carpet
        signal += (2.5 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t)
        # Add high-frequency filtered noise (simulated by bandpass-like noise)
        broadband_noise = rng.normal(0, 1.2, size=len(t))
        signal += broadband_noise

    else:
        # Default baseline
        signal += (2.0 * np.sqrt(2)) * np.sin(2 * np.pi * f1 * t)
        signal += rng.normal(0, 0.05, size=len(t))

    return t, signal
