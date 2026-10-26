"""
generate_synthetic_data.py
--------------------------
Reproducible multi-machine synthetic fleet generator for predictive maintenance.
Generates 20 industrial pump/motor units across 3 years (2023-2025) with documented
degradation scenarios, raw time-domain waveforms, FFT spectra, and ground-truth metadata.
"""

import os
import sys
import argparse
import json
from datetime import datetime
import numpy as np
import pandas as pd

# Path setup
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from pump_pm.features.spectrum_features import (
    generate_time_waveform,
    calculate_rms_spectrum,
    extract_spectral_order_features
)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic predictive maintenance fleet data.")
    parser.add_argument("--machines", type=int, default=20, help="Number of machines to simulate (default 20)")
    parser.add_argument("--start-date", type=str, default="2023-01-01", help="Simulation start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2025-12-31", help="Simulation end date (YYYY-MM-DD)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--missing-pct", type=float, default=5.0, help="Target percentage of realistic missing cells")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 65)
    print(f"Synthetic Fleet Generator: {args.machines} Machines | Seed {args.seed}")
    print("=" * 65)

    rng = np.random.default_rng(args.seed)
    gen_dir = os.path.join(PROJECT_ROOT, "data", "generated")
    waveform_dir = os.path.join(gen_dir, "synthetic_waveforms")
    os.makedirs(waveform_dir, exist_ok=True)

    date_range = pd.date_range(start=args.start_date, end=args.end_date, freq="D")
    total_days = len(date_range)
    print(f"Simulation timeline: {args.start_date} to {args.end_date} ({total_days} days)")

    machine_ids = [f"M{1201 + i:04d}" for i in range(args.machines)]
    locations = ["P1", "P2", "P3", "P4"]
    directions = ["V", "H", "A"]

    # Assign distinct operating scenarios to machines
    scenario_assignment = {
        "healthy_baseline": machine_ids[0:5],      # M1201 - M1205
        "rotor_imbalance": machine_ids[5:8],       # M1206 - M1208
        "shaft_misalignment": machine_ids[8:11],   # M1209 - M1211
        "bearing_defect_thermal": machine_ids[11:14], # M1212 - M1214
        "mechanical_looseness": machine_ids[14:16],# M1215 - M1216
        "hydraulic_cavitation": machine_ids[16:18],# M1217 - M1218
        "sensor_stale_quality": [machine_ids[18]], # M1219
        "incomplete_config": [machine_ids[19]],    # M1220
    }

    event_records = []
    telemetry_rows = []

    # Fault event windows
    event_specs = [
        {"scenario": "rotor_imbalance", "machines": machine_ids[5:8], "start": "2024-04-10", "end": "2024-05-05", "desc": "Progressive mass loss on impeller creating 1x radial unbalance"},
        {"scenario": "shaft_misalignment", "machines": machine_ids[8:11], "start": "2024-08-15", "end": "2024-09-10", "desc": "Thermal growth / foundation shift creating 2x vibration & high coupling axial P2/P3"},
        {"scenario": "bearing_defect_thermal", "machines": machine_ids[11:14], "start": "2025-02-01", "end": "2025-03-01", "desc": "Outer race microspall with lubrication starvation leading to thermal runaway > 80C"},
        {"scenario": "mechanical_looseness", "machines": machine_ids[14:16], "start": "2025-06-10", "end": "2025-07-05", "desc": "Loose baseplate hold-down bolts causing strong directional asymmetry and harmonics"},
        {"scenario": "hydraulic_cavitation", "machines": machine_ids[16:18], "start": "2025-09-01", "end": "2025-09-25", "desc": "Suction strainer blockage causing NPSH deficit and turbulent broadband vibration"},
    ]

    for ev in event_specs:
        for m_id in ev["machines"]:
            event_records.append({
                "machine_id": m_id,
                "fault_scenario": ev["scenario"],
                "start_date": ev["start"],
                "end_date": ev["end"],
                "description": ev["desc"],
                "provenance": "SYNTHETIC_SIMULATION",
                "random_seed": args.seed,
                "generator_version": "1.0.0"
            })

    print(f"Generating telemetry for {len(machine_ids)} machines...")

    for m_id in machine_ids:
        # Determine machine RPM and nominal vibration baseline
        rpm = 3000 if int(m_id[1:]) % 2 == 1 else 1500
        baseline_vib = rng.uniform(2.0, 3.2)
        baseline_temp = rng.uniform(42.0, 50.0)

        # Check which fault events apply
        machine_events = [e for e in event_records if e["machine_id"] == m_id]

        for d_idx, dt in enumerate(date_range):
            dt_str = dt.strftime("%Y-%m-%d")
            seasonal = 2.5 * np.sin(2 * np.pi * d_idx / 365.25)

            # Check if current day falls into an active fault window
            active_scenario = "healthy"
            for ev in machine_events:
                if ev["start_date"] <= dt_str <= ev["end_date"]:
                    active_scenario = ev["fault_scenario"]
                    break

            row = {
                "Machine_number": m_id,
                "time stamp": dt_str,
            }

            for loc in locations:
                # Base temperature with location gradient
                loc_idx = locations.index(loc)
                loc_temp = baseline_temp + seasonal + (loc_idx * 0.8) + rng.normal(0, 0.8)

                if active_scenario == "healthy":
                    v_val = baseline_vib + rng.normal(0, 0.15)
                    h_val = baseline_vib + rng.normal(0, 0.15)
                    a_val = (baseline_vib * 0.75) + rng.normal(0, 0.12)

                elif active_scenario == "rotor_imbalance":
                    # Elevated radial (H and V) on pump bearings (P1, P2)
                    if loc in ["P1", "P2"]:
                        v_val = 7.8 + rng.normal(0, 0.3)
                        h_val = 8.4 + rng.normal(0, 0.35)
                        a_val = 2.8 + rng.normal(0, 0.2)
                    else:
                        v_val = baseline_vib + 1.5 + rng.normal(0, 0.2)
                        h_val = baseline_vib + 1.8 + rng.normal(0, 0.2)
                        a_val = baseline_vib * 0.8

                elif active_scenario == "shaft_misalignment":
                    # Elevated 1x/2x and high axial across coupling (P2, P3)
                    if loc in ["P2", "P3"]:
                        v_val = 6.8 + rng.normal(0, 0.25)
                        h_val = 7.2 + rng.normal(0, 0.25)
                        a_val = 7.5 + rng.normal(0, 0.3)  # Prominent axial
                    else:
                        v_val = baseline_vib + 1.0 + rng.normal(0, 0.2)
                        h_val = baseline_vib + 1.0 + rng.normal(0, 0.2)
                        a_val = baseline_vib + 0.8

                elif active_scenario == "bearing_defect_thermal":
                    # Localized to P2 bearing with thermal runaway
                    if loc == "P2":
                        v_val = 8.5 + rng.normal(0, 0.4)
                        h_val = 8.8 + rng.normal(0, 0.4)
                        a_val = 5.2 + rng.normal(0, 0.3)
                        loc_temp = 84.5 + rng.normal(0, 1.5)  # Thermal runaway > 80C
                    else:
                        v_val = baseline_vib + rng.normal(0, 0.15)
                        h_val = baseline_vib + rng.normal(0, 0.15)
                        a_val = (baseline_vib * 0.75) + rng.normal(0, 0.1)

                elif active_scenario == "mechanical_looseness":
                    # Strong H/V ratio asymmetry
                    if loc in ["P1", "P4"]:
                        v_val = 3.2 + rng.normal(0, 0.2)
                        h_val = 7.9 + rng.normal(0, 0.35)  # H much greater than V
                        a_val = 3.0 + rng.normal(0, 0.2)
                    else:
                        v_val = baseline_vib + rng.normal(0, 0.15)
                        h_val = baseline_vib + rng.normal(0, 0.15)
                        a_val = baseline_vib * 0.75

                elif active_scenario == "hydraulic_cavitation":
                    # Pump side elevated turbulence
                    if loc in ["P1", "P2"]:
                        v_val = 7.2 + rng.normal(0, 0.45)
                        h_val = 7.4 + rng.normal(0, 0.45)
                        a_val = 5.8 + rng.normal(0, 0.4)
                    else:
                        v_val = baseline_vib + rng.normal(0, 0.2)
                        h_val = baseline_vib + rng.normal(0, 0.2)
                        a_val = baseline_vib * 0.8

                else:
                    v_val = baseline_vib + rng.normal(0, 0.15)
                    h_val = baseline_vib + rng.normal(0, 0.15)
                    a_val = (baseline_vib * 0.75) + rng.normal(0, 0.12)

                # Clamp to realistic physical range
                v_val = float(np.clip(round(v_val, 2), 0.5, 25.0))
                h_val = float(np.clip(round(h_val, 2), 0.5, 25.0))
                a_val = float(np.clip(round(a_val, 2), 0.5, 25.0))
                loc_temp = float(np.clip(round(loc_temp, 2), 20.0, 110.0))

                row[f"{loc}-V"] = v_val
                row[f"{loc}-H"] = h_val
                row[f"{loc}-A"] = a_val
                row[f"{loc}-T"] = loc_temp

            telemetry_rows.append(row)

    df_telemetry = pd.DataFrame(telemetry_rows)

    # Inject realistic missing values (~5%) without hiding missingness
    if args.missing_pct > 0:
        total_sensor_cells = df_telemetry.shape[0] * (len(locations) * 4)
        missing_count = int(total_sensor_cells * (args.missing_pct / 100.0))
        sensor_columns = [f"{loc}-{d}" for loc in locations for d in ["V", "H", "A", "T"]]

        print(f"Injecting ~{args.missing_pct}% missing sensor values ({missing_count} cells)...")
        for _ in range(missing_count):
            r_idx = rng.integers(0, len(df_telemetry))
            c_name = rng.choice(sensor_columns)
            df_telemetry.iat[r_idx, df_telemetry.columns.get_loc(c_name)] = np.nan

    # Save synthetic daily telemetry
    telemetry_path = os.path.join(gen_dir, "synthetic_daily_telemetry.csv")
    df_telemetry.to_csv(telemetry_path, index=False)
    print(f"[1/4] Saved daily telemetry: {telemetry_path} ({len(df_telemetry):,} rows)")

    # Save synthetic fault events metadata
    events_df = pd.DataFrame(event_records)
    events_path = os.path.join(gen_dir, "synthetic_fault_events.csv")
    events_df.to_csv(events_path, index=False)
    print(f"[2/4] Saved ground-truth events metadata: {events_path} ({len(events_df)} scenarios)")

    # Generate sample raw waveforms and calculate spectrum features
    print("Generating raw waveforms and calculating FFT spectrum features...")
    spectrum_records = []

    demonstration_scenarios = [
        ("M1201", "healthy", 3000.0, "2024-06-01T10:00:00"),
        ("M1206", "imbalance", 3000.0, "2024-04-20T10:00:00"),
        ("M1209", "misalignment", 3000.0, "2024-08-25T10:00:00"),
        ("M1212", "bearing_defect", 3000.0, "2025-02-15T10:00:00"),
        ("M1215", "mechanical_looseness", 1500.0, "2025-06-20T10:00:00"),
        ("M1217", "cavitation", 1500.0, "2025-09-10T10:00:00"),
    ]

    for m_id, scn, rpm, ts_iso in demonstration_scenarios:
        t_arr, sig = generate_time_waveform(scenario=scn, rpm=rpm, duration_sec=2.0, sample_rate_hz=2048, seed=args.seed)

        # Save waveform CSV for machine and scenario
        wf_df = pd.DataFrame({"time_seconds": t_arr, "velocity_mm_s": sig})
        wf_path = os.path.join(waveform_dir, f"{m_id}_{scn}_waveform.csv")
        wf_df.to_csv(wf_path, index=False)

        # Compute FFT spectrum
        freqs, rms_amp = calculate_rms_spectrum(sig, sample_rate_hz=2048)
        running_freq = rpm / 60.0
        overall_rms = np.sqrt(np.sum(rms_amp ** 2))

        # Store spectrum points up to 500 Hz
        for f, amp in zip(freqs, rms_amp):
            if f <= 500.0:
                order = f / running_freq if running_freq > 0 else 0.0
                spectrum_records.append({
                    "Machine_number": m_id,
                    "Timestamp": ts_iso,
                    "RPM": rpm,
                    "Running_frequency_Hz": running_freq,
                    "Location": "P2",
                    "Direction": "H" if scn != "misalignment" else "A",
                    "Frequency_Hz": round(float(f), 3),
                    "Frequency_Order": round(float(order), 3),
                    "Velocity_RMS_mm_s": round(float(amp), 5),
                    "Overall_RMS_mm_s": round(float(overall_rms), 3),
                    "Scenario": scn,
                    "Provenance": "SYNTHETIC_SIMULATION"
                })

    df_spectrum = pd.DataFrame(spectrum_records)
    spectrum_path = os.path.join(gen_dir, "synthetic_spectrum.csv")
    df_spectrum.to_csv(spectrum_path, index=False)
    print(f"[3/4] Saved synthetic spectrum features: {spectrum_path} ({len(df_spectrum):,} bins)")

    # Data generation report
    gen_report = {
        "generator_version": "1.0.0",
        "random_seed": args.seed,
        "machines_count": args.machines,
        "date_range": [args.start_date, args.end_date],
        "total_days": total_days,
        "total_telemetry_rows": len(df_telemetry),
        "total_cells": int(df_telemetry.size),
        "missing_cells": int(df_telemetry.isnull().sum().sum()),
        "missing_percentage": round(float(df_telemetry.isnull().sum().sum() / df_telemetry.size * 100), 2),
        "fault_scenarios_demonstrated": list(scenario_assignment.keys()),
        "total_event_windows": len(event_records),
        "waveforms_saved": len(demonstration_scenarios),
        "simulation_assumptions": [
            "Sinusoidal 1x fundamental with Gaussian perturbation for baseline rotation",
            "Harmonic orders 1x, 2x, 3x for misalignment and imbalance based on engineering rotor dynamics",
            "BPFO/BPFI defect frequency impulses simulated with exponential decay damping",
            "All synthetic records explicitly tagged with provenance: SYNTHETIC_SIMULATION",
            "Holdout evaluation recommendation: Machine-wise holdout (train on M1201-M1214, test on M1215-M1220) to prevent temporal data leakage"
        ]
    }

    report_path = os.path.join(PROJECT_ROOT, "outputs", "reports", "synthetic_data_generation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(gen_report, f, indent=2)
    print(f"[4/4] Saved generation report: {report_path}")
    print("\n[SUCCESS] Phase 4 Synthetic generation complete.")


if __name__ == "__main__":
    main()
