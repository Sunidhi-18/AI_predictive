# Source Register and Workspace Audit

**Audit Date:** 2026-10-25
**Archive Destination:** `data/archive/original_inputs/`

## 1. Executive Summary

A total of **13 files** were discovered in the workspace root. All 13 original files have been safely archived to `data/archive/original_inputs/` with SHA-256 cryptographic hashes verified. Two byte-for-byte duplicate pairs were identified and isolated, and all original legacy scripts, notebooks, datasets, and standard specifications were inventoried and mapped to canonical project destinations.

### Key Findings:
- **Duplicate Files Identified:**
  - `Guidelines 0n Pump Vibration First edition Final July 2013 (2).pdf` is identical to `(1).pdf` (SHA-256: `8408b01270...`).
  - `ISO-10816-7-2009 (2).pdf` is identical to `(1).pdf` (SHA-256: `aa7b69121b...`).
- **Data Provenance:**
  - Both `pump_motor_vibration_2024_2025_daily (1).csv` and `high_reading_pump_motor_vibration_dataset_2024_2025 (1).csv` are synthetically generated datasets created by the legacy notebooks (`seed=42`). They contain ~8% random missing values scattered across IDs, timestamps, and sensor readings.
  - `pump_imbalance_frequency_spectrum (1).csv` is a single-timestamp simulation (`2026-10-16T09:12:54`) for machine `M1201` synthesized at 3000 RPM (50 Hz). It does not represent physical field acquisition.
  - `diagnosed_high_freq_high_temp_events.csv` contains 14 hardcoded threshold-filtered events labelled as Zone D.
- **Standards Status:**
  - `ISO-10816-7-2009 (1).pdf` provides the measurement framework.
  - Europump Guidelines (2013) Table 1 (page 9) provides the authoritative zone boundaries for Category 1 & 2 rotodynamic pumps (≤200 kW and >200 kW), plus Alarm (1.25× Zone B) and Trip (1.25× Zone C) multipliers.
  - ISO lists ISO 10816-7:2009 as published and currently under revision (with ISO/AWI 20816-7 in development as of October 2026). The draft standard is not yet published.

## 2. File-by-File Audit Table

| Original Filename | SHA-256 Hash | Size | Purpose & Dimensions | Date Range & Machine Coverage | Missing Data / Quality | Duplicate Status | Canonical Target | Action Taken |
|---|---|---|---|---|---|---|---|---|
| `Guidelines 0n Pump Vibration First edition Final July 2013 (1).pdf` | `8408b01270...` | 707,366 B | Europump Guideline on Pump Vibration First Edition (July 2013). <br>*17 pages* | N/A <br>Machines: N/A | N/A | Unique | `docs/reference/pump_vibration_guidelines.pdf` | Complete technical guide containing ISO 10816-7 Zone limits, Alarm/Trip formulas, POR/AOR (17 pages). |
| `Guidelines 0n Pump Vibration First edition Final July 2013 (2).pdf` | `8408b01270...` | 707,366 B | Byte-for-byte identical duplicate of Guidelines 0n Pump Vibration First edition Final July 2013 (1).pdf. <br>*17 pages* | N/A <br>Machines: N/A | N/A | Duplicate of `Guidelines 0n Pump Vibration First edition Final July 2013 (1).pdf` | `data/archive/original_inputs/Guidelines 0n Pump Vibration First edition Final July 2013 (2).pdf` | Redundant duplicate. Preserved in archive only; excluded from canonical docs. |
| `ISO-10816-7-2009 (1).pdf` | `aa7b69121b...` | 411,808 B | ISO 10816-7:2009 international standard for rotodynamic pumps (evaluation on non-rotating parts). <br>*11 pages* | N/A <br>Machines: N/A | N/A | Unique | `docs/reference/ISO_10816-7-2009.pdf` | Normative standard preview (Scope and measurement requirements, 11 pages). |
| `ISO-10816-7-2009 (2).pdf` | `aa7b69121b...` | 411,808 B | Byte-for-byte identical duplicate of ISO-10816-7-2009 (1).pdf. <br>*11 pages* | N/A <br>Machines: N/A | N/A | Duplicate of `ISO-10816-7-2009 (1).pdf` | `data/archive/original_inputs/ISO-10816-7-2009 (2).pdf` | Redundant duplicate. Preserved in archive only; excluded from canonical docs. |
| `Modified_high_readings_misalignment (1).ipynb` | `63d6ab145c...` | 9,730 B | Synthetic data generation script for coordinated high vibration events. <br>*2 cells (2 code, 0 md)* | N/A <br>Machines: N/A | N/A | Unique | `notebooks/legacy/Modified_high_readings_misalignment (1).ipynb` | Legacy generator. Introduces step increase in vibration for July 2024. |
| `daily_readings (1).ipynb` | `ddbe080767...` | 7,407 B | Synthetic data generation script for daily vibration telemetry. <br>*2 cells (2 code, 0 md)* | N/A <br>Machines: N/A | N/A | Unique | `notebooks/legacy/daily_readings (1).ipynb` | Legacy generator. Uses hardcoded seed 42 and random missing cell deletion. |
| `diagnosed_high_freq_high_temp_events.csv` | `6f3090ceb9...` | 1,554 B | Diagnostic summary output of high vibration/temperature event occurrences. <br>*14 rows × 8 cols* | 2024-08-10 to 2025-10-08 <br>Machines: M1202, M1204, M1201 | 0/112 cells (0.00%) | Unique | `data/raw/diagnosed_events.csv` | Useful output reference. Identifies 14 Zone D events for M1201, M1202, M1204. |
| `frequency_imbalance_with plot (1).ipynb` | `8abde941cd...` | 148,768 B | Harmonic signal synthesis, FFT calculation, and 12-panel plot rendering. <br>*2 cells (2 code, 0 md)* | N/A <br>Machines: N/A | N/A | Unique | `notebooks/legacy/frequency_imbalance_with plot (1).ipynb` | Legacy simulation. Creates 50 Hz running speed + harmonics for M1201. |
| `high_frequency_vibration_high_temperature.ipynb` | `687a543778...` | 15,733 B | Harmonic signal synthesis, FFT calculation, and 12-panel plot rendering. <br>*2 cells (2 code, 0 md)* | N/A <br>Machines: N/A | N/A | Unique | `notebooks/legacy/high_frequency_vibration_high_temperature.ipynb` | Legacy simulation. Creates 50 Hz running speed + harmonics for M1201. |
| `high_frequency_vibration_high_temperature.py` | `226ca53d2d...` | 12,534 B | Standalone Python script replicating high_frequency_vibration_high_temperature notebook. <br>*N/A* | N/A <br>Machines: N/A | N/A | Unique | `notebooks/legacy/high_frequency_vibration_high_temperature.py` | Legacy standalone script. Hardcodes 3000 RPM, BPFO 179 Hz, BPFI 271 Hz. |
| `high_reading_pump_motor_vibration_dataset_2024_2025 (1).csv` | `0a2d74be2e...` | 340,094 B | Daily telemetry with coordinated high-vibration events across all 4 measurement points. <br>*3655 rows × 18 cols* | 2024-01-01 to 2025-12-31 <br>Machines: M1201, M1202, M1203, M1204, M1205 | 4955/65790 cells (7.53%) | Unique | `data/raw/high_readings_telemetry.csv` | Useful synthetic fault dataset. Coordinated elevated readings on 2024-07-15/16. |
| `pump_imbalance_frequency_spectrum (1).csv` | `dbba7f12bd...` | 1,621,249 B | Simulated vibration velocity FFT frequency spectrum for machine M1201. <br>*24012 rows × 10 cols* | 2026-10-16 to 2026-10-16 <br>Machines: M1201 | 0/240120 cells (0.00%) | Unique | `data/raw/imbalance_spectrum.csv` | Single timestamp snapshot (2026-10-16). Synthetic 1x/2x/3x harmonic demo. |
| `pump_motor_vibration_2024_2025_daily (1).csv` | `f7dff3455b...` | 343,442 B | Baseline daily telemetry containing vibration (H/V/A) and temp for P1-P4 across 5 machines. <br>*3655 rows × 18 cols* | 2024-01-01 to 2025-12-31 <br>Machines: M1201, M1202, M1203, M1204, M1205 | 5263/65790 cells (8.00%) | Unique | `data/raw/daily_telemetry.csv` | Useful canonical raw baseline. Contains ~8.0% missing cells and ungrounded 7 mm/s flags. |

## 3. Legacy Code Inspection & Deficiencies

1. **Arbitrary Universal Thresholds:** Legacy notebooks frequently hardcoded `7.0 mm/s` as an arbitrary fault cut-off and `65°C` as an arbitrary bearing temperature trip. Under ISO 10816-7, acceptable vibration limits depend directly on machine category (Cat 1 vs Cat 2), rated power (≤200 kW vs >200 kW), and operating zone (POR vs AOR).
2. **Circular Labeling / Data Leakage:** In legacy scripts, labels such as `'High Frequency Vibration with High Temperature'` were assigned by applying fixed thresholds on vibration (>7.0 mm/s) and temperature (>70°C), and then claimed as 'diagnosed problems'. In this framework, ground truth and rule candidates must be explicitly decoupled.
3. **Missing Value Incoherence:** Approximately 8% of machine IDs and timestamps were replaced with `NaN`. Without robust validation and quarantine handling, raw datasets would silently drop or corrupt time-series alignment.
4. **Location Naming Ambiguity:** Daily telemetry used `P1, P2, P3, P4`, whereas spectral code used `P1, P2, M1, M2`. The new framework standardizes measurement point nomenclature across pump non-drive end (P-NDE / P1), pump drive end (P-DE / P2), motor drive end (M-DE / P3), and motor non-drive end (M-NDE / P4).
5. **Isolated Notebook Execution:** Previous analyses existed as disjointed scripts without a common pipeline, unit tests, or reproducible architecture.

## 4. Preservation & Canonical Mapping Plan

- All original source files remain intact and unmodified in `data/archive/original_inputs/`.
- Unique raw datasets are copied to `data/raw/` with standardized descriptive names.
- Authoritative PDF guidelines are copied to `docs/reference/`.
- Legacy notebooks and scripts are preserved in `notebooks/legacy/` for historical reference.