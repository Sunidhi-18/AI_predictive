# Intelligent Predictive Maintenance Framework for Smart Manufacturing

> **An Engineering Decision-Support Prototype Using Data Engineering, ML, Explainable AI, and Human-in-the-Loop Workflow Orchestration for Industrial Pumps and Motors.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Standards Compliance: ISO 10816-7 / Europump 2013](https://img.shields.io/badge/Standards-ISO%2010816--7-green.svg)](docs/standards_mapping.md)
[![License: Academic/Research](https://img.shields.io/badge/License-Academic%20Prototype-orange.svg)](docs/assumptions_and_limitations.md)

---

## 1. Important Safety & Operational Notice

This software is an **academic engineering prototype** for condition monitoring, anomaly detection, vibration analysis, and maintenance decision support. **It is NOT a certified industrial machine protection system or Safety Instrumented System (SIS).** It must **never** directly actuate or trip physical machinery. Plant emergency shutdowns and machine interlocks must remain independently engineered and hardwired.

All synthetic data and demonstration models are explicitly tagged. Diagnostic results represent **hypotheses backed by heuristic evidence**, never unverified ground-truth conclusions.

---

## 2. System Features & Capabilities

- **ISO 10816-7 & Europump 2013 Vibration Assessment:**
  Evaluates broadband bearing housing vibration across Zones A, B, C, and D based on pump category (Cat 1 vs Cat 2), nominal power ($\le 200\text{ kW}$ vs $> 200\text{ kW}$), and operational range (POR vs AOR). Enforces refusal when machine configuration is incomplete.
- **Hybrid Rule-Based + ML Forecasting Architecture:**
  Combines standards-compliant rule evaluation with a multi-output Machine Learning forecaster. Predicts next-day vibration velocities and bearing temperatures across 16 sensor channels, feeding forecasted values through the same configurable ISO rule engine to anticipate zone degradation (e.g., Zone B $\to$ Zone C) before alarm thresholds are breached.
- **Leakage-Free Forecasting Data Engineering:**
  Enforces strict machine boundary separation (targets and lag features never cross machine boundaries), timestamp gap invalidation (`time_gap_days > 1.0` sets target to NaN), and zero lookahead leakage (features at $t$ only utilize historical data $\le t$).
- **Multi-Model Benchmark on Unseen Chronological Test Data:**
  Trains a multi-output Random Forest Regressor and benchmarks against a Persistence Baseline ($\hat{y}_{t+1} = y_t$) and Ridge Regression on 3,962 unseen chronological test samples, reporting MAE, RMSE, and $R^2$.
- **Robust Local Data Engineering Pipeline:**
  Ingests daily telemetry, validates schemas and physical ranges, preserves data quality statistics, safely quarantines invalid IDs/timestamps without data loss, and normalizes into a tidy schema.
- **Reproducible 20-Machine Synthetic Fleet Generator:**
  Generates multi-year telemetry with documented mechanical degradation scenarios, high-speed time waveforms, and FFT spectra.
- **Transparent Multi-Evidence Diagnostic Engine:**
  Evaluates 12 distinct mechanical, hydraulic, electrical, and sensor fault families, providing supporting evidence, missing checks, confidence scoring, and explicit "Unknown / Insufficient Evidence" fallback.
- **ML Anomaly Detection & Explainability:**
  Unsupervised Isolation Forest baseline with SHAP / feature contribution explainability.
- **Local Persistence & Maintenance Workflow:**
  SQLite database tracking machine events, operator acknowledgements, work order drafting, and maintenance logs with an immutable audit trail.
- **Streamlined 2-View Industrial SCADA Workstation:**
  - **View 1 (Real-Time Live Monitor & ML Forecast):** Real-time incoming data evaluation, prominent fault type output, ISO 10816-7 threshold notifications with FFT recommendations, same-page Random Forest next-day forecast ($t+1$), 16-channel comparison matrix, and rolling strip-chart with forecast projections.
  - **View 2 (Date-to-Date Report, Trends & Frequency Analysis):** Custom date range filter (`From Date` ➔ `To Date`), date-to-date health summary and CSV/PDF export, multi-point trend graphs with Category- and Power-specific Zone B/C limit lines, and high-resolution FFT order spectrum analysis (1X, 2X, 3X, VPF).

---

## 3. Directory Structure

```text
AI_Predictive_1/
├── app.py                      # Main Streamlit interactive dashboard
├── README.md                   # Project documentation & setup instructions
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── CHECKLIST.md                # Task tracking with completion percentage
├── PROGRESS_LOG.md             # Chronological engineering log
│
├── config/                     # Centralized YAML configurations
│   ├── app.yaml                # Global paths, units, and logging
│   ├── machine_config.yaml     # Machine technical registry & power/speed
│   ├── standards_limits.yaml   # ISO 10816-7 / Europump 2013 limits table
│   └── diagnostic_rules.yaml   # 12 fault families evidence rules
│
├── data/
│   ├── raw/                    # Canonical raw input datasets
│   ├── generated/              # Reproducible synthetic fleet data
│   │   └── synthetic_waveforms/ # Time waveforms & FFT spectra
│   ├── processed/              # Normalized long-form telemetry
│   ├── features/               # Calculated rolling & spectral features
│   ├── quarantine/             # Invalid records with error logs
│   ├── archive/original_inputs/# Recoverable original input files
│   └── database/               # Local SQLite maintenance.db
│
├── docs/                       # Technical engineering guides
│   ├── architecture.md         # System design & module data flows
│   ├── standards_mapping.md    # ISO 10816-7 rationale & tables
│   ├── data_dictionary.md      # Schema & data definitions
│   ├── assumptions_and_limitations.md # Prototype boundaries & disclaimers
│   ├── fault_diagnosis_guide.md# Vibration analyst diagnostic handbook
│   ├── testing_strategy.md     # Test plan & coverage criteria
│   ├── source_register.md      # Audit log of original workspace files
│   └── reference/              # Normative reference standards PDFs
│
├── notebooks/legacy/           # Original archived exploratory notebooks
├── scripts/                    # Automation & pipeline CLI scripts
│   ├── audit_existing_files.py # File audit and hash verification
│   ├── generate_synthetic_data.py # Fleet data generator
│   ├── validate_data.py        # Data quality validator
│   ├── run_local_pipeline.py   # End-to-end data processing pipeline
│   └── train_forecaster.py     # ML forecasting pipeline & benchmark
│
├── src/pump_pm/                # Modular Python source package
│   ├── config.py               # Configuration loader & validator
│   ├── ingestion/              # Data loading, schema validation, quarantine
│   ├── processing/             # Cleaning, imputation, normalization
│   ├── standards/              # ISO 10816-7 zone evaluator
│   ├── features/               # Trend statistics & FFT order extraction
│   ├── forecasting/            # Data engineering, ML models & predicted zones
│   ├── diagnostics/            # 12-family multi-evidence rule engine
│   ├── models/                 # Anomaly detection & SHAP explainability
│   ├── storage/                # SQLite repository & audit trail
│   ├── workflows/              # Human-in-the-loop maintenance workflow
│   └── reporting/              # CSV summary & PDF report generator
│
├── tests/                      # Automated unit & integration tests
│   ├── test_data_validation.py # Ingestion & schema checks
│   ├── test_zone_assessment.py # ISO 10816-7 boundary tests
│   ├── test_features.py        # Rolling & FFT feature tests
│   ├── test_forecasting.py     # Leakage, time gaps, ML & zone forecast tests
│   ├── test_diagnostics.py     # Fault rule engine tests
│   ├── test_storage.py         # SQLite & workflow tests
│   └── test_reports.py         # Report generation tests
└── outputs/                    # Exported outputs
    ├── figures/                # Exported diagnostic plots
    ├── models/                 # Persisted forecaster model & config
    ├── reports/                # PDF/CSV reports & evaluation summaries
    └── evaluation/             # Model evaluation metrics & matrices
```

---

## 4. Local Installation & Setup

### Prerequisites
- Python 3.11+
- Git (optional)

### Setup Instructions
1. Open PowerShell / terminal in the project root:
   ```bash
   cd c:\Users\omgow\OneDrive\Desktop\AI_Predictive_1
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Quick-Start Guide

### Step 1: Run the Automated Data Quality & Processing Pipeline
Process raw telemetry into cleaned long-form data, compute features, assess severity zones, and populate the SQLite database:
```bash
python scripts/run_local_pipeline.py
```

### Step 2: Train and Benchmark the ML Forecaster
Engineer historical features with strict machine separation, train the multi-output Random Forest regressor, evaluate against baselines on unseen test data, and persist models:
```bash
python scripts/train_forecaster.py
```

### Step 3: Run the Automated Test Suite
Execute all 29 unit and integration tests across data validation, ISO zones, feature extraction, forecasting, and diagnostics:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Step 4: Launch the Interactive SCADA Workstation
Start the local Streamlit application:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 6. Hybrid Rule-Based Assessment & ML Forecasting Architecture

The system unites deterministic ISO rule compliance with proactive multi-channel forecasting:

```text
[Historical Telemetry (t <= T)] 
       │
       ▼
[Data Engineering & Feature Store] ──> Lags (1,2,3,7), 3d/7d Rolling Stats, Rate-of-Change, Ratios
       │                              (Strict Machine Separation & Time-Gap Invalidation)
       ▼
[Multi-Output ML Forecaster] ───────> Predicts Next-Valid-Daily Readings (16 Sensor Channels)
       │
       ▼
[ISO 10816-7 Rule Engine] ──────────> Evaluates Predicted Readings using Configurable Pump Limits
       │
       ▼
[Zone Degradation Detector] ────────> Flags Early Transitions (e.g. Zone B -> Zone C) Ahead of Trips
```

### Rigorous Leakage Prevention & Data Engineering
- **Strict Machine Separation:** Target generation (`shift(-1)`) and lag features are computed strictly within each individual machine group. Targets and features **never cross machine boundaries**.
- **Time-Gap Invalidation:** Any gap between consecutive timestamps exceeding 1.0 day (`time_gap_days > 1.0`) invalidates the target (set to `NaN`), preventing artificial transitions across unmonitored outages.
- **Zero Lookahead Data Leakage:** Features calculated at time $t$ only utilize historical measurements $\le t$. Future readings are never accessed during feature creation.
- **Chronological Train/Test Partitioning:** Training is conducted on the initial 80% chronological interval (15,809 samples); evaluation is performed strictly on the unseen chronologically held-out 20% test partition (3,962 samples).

### Verified Test Benchmark Results (Unseen Test Data)

Evaluated across **3,962 chronologically held-out unseen samples** predicting 16 simultaneous channels (12 vibration velocities in mm/s and 4 bearing temperatures in °C):

| Model | Evaluation Split | Samples | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | R² Score | Performance vs. Baseline |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Persistence Baseline** ($\hat{y}_{t+1} = y_t$) | Chronological Test | 3,962 | 0.4820 mm/s | 1.0151 mm/s | 0.6787 | Baseline Reference |
| **Ridge Regression Baseline** ($\alpha=1.0$) | Chronological Test | 3,962 | **0.4080 mm/s** | **0.8156 mm/s** | **0.7855** | **15.4% MAE reduction** |
| **Random Forest Regressor** (100 Trees) | Chronological Test | 3,962 | 0.4240 mm/s | 0.8490 mm/s | 0.7308 | **12.0% MAE reduction** |

*Note: All accuracy claims are strictly computed on unseen chronologically held-out test data. Zero data leakage.*

### ISO Severity Zone Assessment & Refusal Logic
- **Current Zone vs. Predicted Zone:** The identical configurable ISO 10816-7 / Europump 2013 Table 1 rules evaluate both current sensor measurements and predicted next-day values.
- **Early Degradation Warning:** If an asset is currently in Zone B (unrestricted operation) but forecasted to transition to Zone C (restricted continuous operation), the system raises a proactive advisory alert before high vibration trips occur.
- **Incomplete Configuration Refusal:** For assets with incomplete technical ratings (such as `M1205` where pump category and power are unassigned), both the rule engine and the forecasting zone evaluator strictly refuse evaluation with:
  > `Not evaluable — machine configuration or applicable criterion is incomplete`

---

## 7. Assumptions, Safety Policies & Limitations

1. **Independent Plant Safety:** The system serves exclusively as diagnostic and predictive decision support. It must never actuate physical plant interlocks or emergency shutdowns.
2. **Forecast Step Horizon:** Predictions represent the next valid daily steady-state operating reading ($t+1$). Multi-step horizons degrade in confidence and are intended for advisory trend tracking.
3. **Continuous Retraining:** Physical machine baseline characteristics drift over multi-year operations; models should be retrained periodically as new validated sensor data accumulates.

