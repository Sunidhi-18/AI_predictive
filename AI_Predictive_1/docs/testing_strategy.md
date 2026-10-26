# Automated Testing Strategy & Verification Plan

This document details the test framework, test suites, coverage criteria, and execution commands.

---

## 1. Testing Framework

The application uses **`pytest`** for deterministic, automated local unit and integration testing. All tests are designed to execute without external network access or cloud fixtures.

---

## 2. Test Suite Architecture

| Test File | Target Module | Scope & Key Invariants Verified |
|---|---|---|
| `tests/test_data_validation.py` | `src/pump_pm/ingestion/` | Schema validation, missing machine ID/timestamp quarantine, physical range enforcement, non-destructive parsing. |
| `tests/test_zone_assessment.py` | `src/pump_pm/standards/` | Exact ISO 10816-7 / Europump 2013 Table 1 boundary values, Category 1 vs 2 separation, $\le 200\text{ kW}$ vs $> 200\text{ kW}$, incomplete machine configuration refusal. |
| `tests/test_diagnostics.py` | `src/pump_pm/diagnostics/` | Evidence-based rule execution, multiple hypothesis ranking, unknown/insufficient evidence outcome, spectral and directional evidence checks. |
| `tests/test_features.py` | `src/pump_pm/features/` | 7-day rolling statistics, trend slopes, FFT spectral order extraction (1×, 2×, BPFO), temperature delta features. |
| `tests/test_storage.py` | `src/pump_pm/storage/` | SQLite database initialization, event creation, retrieval, operator acknowledgement, audit trail immutability. |
| `tests/test_reports.py` | `src/pump_pm/reporting/` | CSV report formatting, PDF report rendering using PyMuPDF, synthetic data watermark inclusion. |

---

## 3. Boundary-Value Testing for Severity Zones

To ensure standards compliance, tests explicitly verify exact boundary transitions:

### Category 1, $\le 200\text{ kW}$:
- $2.50\text{ mm/s} \to$ **Zone A**
- $2.51\text{ mm/s} \to$ **Zone B**
- $4.00\text{ mm/s} \to$ **Zone B**
- $4.01\text{ mm/s} \to$ **Zone C**
- $6.60\text{ mm/s} \to$ **Zone C**
- $6.61\text{ mm/s} \to$ **Zone D**
- Alarm limit: $> 5.0\text{ mm/s}$ triggers Warning/Alarm
- Trip limit: $> 8.3\text{ mm/s}$ triggers Trip

### Incomplete Configuration Verification:
- Machine `M1205` (with `category: null` and `nominal_power_kw: null`):
  Must return `Not evaluable — machine configuration or applicable criterion is incomplete`.

---

## 4. Test Execution Instructions

Run all test suites locally:
```bash
pytest -v
```

Run a specific test suite:
```bash
pytest tests/test_zone_assessment.py -v
```

Generate test coverage report:
```bash
pytest --cov=src/pump_pm -v
```
