# Data Dictionary & Schema Definitions

This document details the data structures, types, units, and semantic definitions across all pipeline stages.

---

## 1. Raw Telemetry Schema (`data/raw/daily_telemetry.csv`, `high_readings_telemetry.csv`)

| Column Name | Data Type | Physical Meaning | Valid Range / Format | Units |
|---|---|---|---|---|
| `Machine_number` | String | Machine unique identifier | `M1201` – `M1220` | Dimensionless |
| `time stamp` | String / DateTime | Sampling timestamp (daily) | `YYYY-MM-DD` | ISO-8601 Date |
| `P1-V` | Float | Pump Non-Drive End (P-NDE) Vertical vibration | $0.0 - 50.0$ | $\text{mm/s RMS}$ |
| `P1-H` | Float | Pump Non-Drive End (P-NDE) Horizontal vibration | $0.0 - 50.0$ | $\text{mm/s RMS}$ |
| `P1-A` | Float | Pump Non-Drive End (P-NDE) Axial vibration | $0.0 - 50.0$ | $\text{mm/s RMS}$ |
| `P1-T` | Float | Pump Non-Drive End bearing housing temperature | $-10.0 - 150.0$ | $^{\circ}\text{C}$ |
| `P2-V`, `P2-H`, `P2-A`, `P2-T` | Float | Pump Drive End (P-DE) measurements | Same as above | $\text{mm/s RMS} / ^{\circ}\text{C}$ |
| `P3-V`, `P3-H`, `P3-A`, `P3-T` | Float | Motor Drive End (M-DE) measurements | Same as above | $\text{mm/s RMS} / ^{\circ}\text{C}$ |
| `P4-V`, `P4-H`, `P4-A`, `P4-T` | Float | Motor Non-Drive End (M-NDE) measurements | Same as above | $\text{mm/s RMS} / ^{\circ}\text{C}$ |

---

## 2. Normalized Long-Form Telemetry (`data/processed/normalized_telemetry.parquet` / `.csv`)

Normalized into a tidy tabular format for scalable querying and model feature ingestion:

| Field Name | Type | Description |
|---|---|---|
| `machine_id` | String | Unique machine identifier |
| `timestamp` | DateTime64 | Standardized UTC timestamp |
| `location_id` | String | Measurement point (`P1`, `P2`, `P3`, `P4`) |
| `location_name` | String | Full mechanical location name (`P-NDE`, `P-DE`, `M-DE`, `M-NDE`) |
| `direction` | String | Measurement direction (`V`, `H`, `A`) |
| `vibration_rms` | Float64 | Root-mean-square vibration velocity ($\text{mm/s}$) |
| `temperature_c` | Float64 | Bearing temperature ($^{\circ}\text{C}$) |
| `quality_flag` | String | Data health flag: `VALID`, `IMPUTED_MEDIAN`, `INTERPOLATED` |
| `provenance` | String | Source metadata: `RAW_BASELINE`, `SYNTHETIC_SIMULATION`, etc. |

---

## 3. High-Resolution Frequency Spectrum Schema (`data/raw/` & `data/generated/`)

| Field Name | Type | Description | Units |
|---|---|---|---|
| `Machine_number` | String | Unique machine identifier | Dimensionless |
| `Timestamp` | String | Acquisition timestamp | ISO-8601 |
| `RPM` | Float | Operating rotational speed | $\text{RPM}$ |
| `Running_frequency_Hz` | Float | Shaft 1x fundamental frequency ($\text{RPM} / 60$) | $\text{Hz}$ |
| `Location` | String | Sensor location (`P1`, `P2`, `P3`, `P4`) | Dimensionless |
| `Direction` | String | Measurement axis (`V`, `H`, `A`) | Dimensionless |
| `Frequency_Hz` | Float | Spectral discrete bin frequency | $\text{Hz}$ |
| `Frequency_Order` | Float | Order normalized by shaft speed ($\text{Freq} / 1\text{x}$) | Orders |
| `Velocity_RMS_mm_s` | Float | RMS amplitude at discrete frequency | $\text{mm/s RMS}$ |
| `Overall_RMS_mm_s` | Float | Total broadband integrated RMS across spectrum | $\text{mm/s RMS}$ |
| `Bearing_Temperature_C` | Float | Concurrent bearing temperature | $^{\circ}\text{C}$ |
| `Provenance` | String | Flag indicating simulated vs field acquired | Dimensionless |

---

## 4. Maintenance Database Tables (`data/database/maintenance.db`)

### `events` Table:
- `event_id`: Primary Key (UUID / Auto-increment integer)
- `machine_id`: Foreign Key referencing machine registry
- `timestamp`: Incident date/time
- `source`: Source dataset or trigger (`DAILY_RULE`, `ANOMALY_DETECTOR`, `MANUAL`)
- `max_vibration`: Peak measured vibration across all points ($\text{mm/s}$)
- `dominant_location`: Point with highest vibration
- `severity_zone`: Assessed ISO zone (`Zone A`, `Zone B`, `Zone C`, `Zone D`, `Not evaluable`)
- `alarm_status`: `NORMAL`, `WARNING`, `ALARM`, `TRIP`
- `candidate_faults_json`: Serialized JSON array of candidate hypotheses with scores
- `supporting_evidence_json`: Serialized array of supporting sensor observations
- `missing_evidence_json`: Serialized array of missing diagnostic evidence
- `anomaly_score`: ML Isolation Forest anomaly score ($[-1.0, 1.0]$)
- `model_version`: ML pipeline version tag
- `status`: Workflow state (`OPEN`, `ACKNOWLEDGED`, `UNDER_INSPECTION`, `RESOLVED`, `FALSE_ALARM`)
- `acknowledgement_notes`: Operator notes upon acknowledgement
- `acknowledged_by`: User identifier
- `acknowledged_at`: Timestamp of acknowledgement
- `work_order_id`: Generated or linked work order ID
- `action_taken`: Description of corrective physical action
- `action_completed_at`: Resolution timestamp
- `post_maintenance_notes`: Verification and follow-up observations

### `quarantine` Table (`data/quarantine/quarantine_log.csv`):
- `record_id`: Tracking identifier
- `source_file`: Original file path
- `raw_row_index`: Line number in source
- `raw_payload`: Unparsed raw row string
- `quarantine_reason`: Documented failure reason (`INVALID_MACHINE_ID`, `INVALID_TIMESTAMP`, `OUT_OF_PHYSICAL_RANGE`)
- `quarantined_at`: Processing timestamp
