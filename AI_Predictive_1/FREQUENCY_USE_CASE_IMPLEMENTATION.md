# Frequency Use Case Implementation Notes

This patch adds the third use case, **Frequency-Based Fault Diagnosis**, to the existing Streamlit dashboard.

## Changed / added files

- `src/pump_pm/diagnostics/frequency_diagnosis.py` — generates clearly labelled synthetic vibration waveforms, computes FFT features using the existing feature extractor, and applies transparent rules for the three target patterns.
- `app.py` — replaces the previous spectrum-only block with the new frequency diagnosis panel. The panel includes machine/date selection, event-schedule mode or controlled demo mode, location/direction selection, FFT graph, 1x/2x/3x/high-frequency metrics, diagnostic evidence, and a P1–P4 H/V/A channel table.
- `tests/test_frequency_diagnosis.py` — tests the three target patterns and event mapping.
- `docs/frequency_diagnosis_use_case.md` — describes the workflow and limitations.
- `README.md` — documents the new use case.

## Windows setup

Open PowerShell in the extracted project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks virtual-environment activation, run the project's Python directly after installing dependencies, or follow your local IT policy for script execution.

## How to use the dashboard

1. Open **Date-to-Date Report, Trends & Frequency Analysis**.
2. Scroll to **Use Case 3 — Frequency-Based Fault Diagnosis**.
3. Choose **Use synthetic event schedule for selected machine/date** to map existing synthetic event labels to the target conditions when possible.
4. Choose **Controlled synthetic demonstration** to test the three target conditions individually.
5. Select a date, location and direction. The graph shows the generated waveform's FFT spectrum and marks 1x, 2x and 3x running-speed frequencies.
6. Review the rule result and the table for all P1–P4, H/V/A channels.

## Important interpretation notes

- The existing daily dataset has overall readings, not raw vibration waveforms. It is not possible to derive real FFT spectra from daily RMS values alone.
- The new panel generates synthetic waveforms to demonstrate FFT analysis. It does not claim those waveforms were measured from the selected asset.
- The high-frequency + high-temperature demo deliberately injects a synthetic temperature rise at the selected location so the combined rule can be demonstrated.
- The diagnostic thresholds are demo heuristics, not ISO thresholds, calibrated probabilities or validated fault classifiers.
- Real deployment requires measured waveforms/spectra linked to machine, date, RPM, location and direction, verified temperature limits, and labelled fault examples.
- The app is for academic decision support only and must not operate physical machinery or replace certified protection systems.

## Validation performed

- Python syntax compilation succeeded for `app.py` and the new module.
- Automated test suite: 33 tests passed.
- The dashboard itself was not launched in the build environment because Streamlit is not installed there; install `requirements.txt` before running locally.
