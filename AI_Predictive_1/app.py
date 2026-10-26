"""
app.py
------
Intelligent Predictive Maintenance Workstation for Smart Manufacturing.
Hybrid Architecture: Combines Standards-Based Rule Assessment (ISO 10816-7 / Europump 2013)
with Multi-Output Machine Learning Sensor Forecasting (Random Forest).

Features:
- Real-Time Live Telemetry Stream with Automatic Continuous Streaming (Auto-play / Pause / Speed control)
- Hybrid Rule-Based & ML Forecasting: Current ISO Severity Zone vs Predicted Next-Day Severity Zone
- Live changing sensor data for all 4 bearing locations (P1-NDE, P2-DE, P3-MDE, P4-MNDE) with dynamic deltas
- Real-time ISO 10816-7 Zone Assessment (Zone A, B, C, D) and ML Anomaly scoring
- Real-time Plain-English Diagnostic Explanations with physical rationales, supporting evidence, and mitigation
- Date-Based Fault Analysis & Detection (Calendar date picker, historical incident jump, 16-channel matrix, SHAP XAI)
- Multi-Point Vibration & Temperature Trends with ISO reference limits
- High-Resolution Spectral Order Analysis (FFT with 1X, 2X, 3X, VPF markers)
- Human-in-the-Loop Maintenance Workflow, SQLite Audit Trail & Industrial PDF/CSV Reporting
- Data Quality Assurance & Quarantine Isolation
"""

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import streamlit as st

# Configure Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from pump_pm.config import get_config
from pump_pm.storage.repository import MaintenanceRepository
from pump_pm.workflows.maintenance_workflow import AgenticMaintenanceWorkflow
from pump_pm.reporting.report_generator import generate_csv_summary, generate_pdf_report
from pump_pm.standards.zone_assessment import (
    assess_vibration_point,
    assess_machine_telemetry_row,
    NOT_EVALUABLE_MESSAGE
)
from pump_pm.diagnostics.rule_engine import MultiEvidenceRuleEngine
from pump_pm.diagnostics.frequency_diagnosis import (
    TARGET_SCENARIOS, analyse_waveform, map_event_to_target_scenario
)
from pump_pm.models.explainability import ModelExplainer
from pump_pm.models.anomaly_detection import AnomalyDetector
from pump_pm.forecasting import (
    SensorForecaster,
    prepare_forecasting_dataset,
    compare_current_and_predicted_zones,
    assess_predicted_telemetry,
    get_short_zone_name,
    DEFAULT_TARGET_CHANNELS
)

# Streamlit Page Setup
st.set_page_config(
    page_title="AI Predictive Maintenance | Industrial Workstation",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Industrial SCADA Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .scada-header {
        background: linear-gradient(135deg, #0b132b 0%, #1c2541 60%, #3a506b 100%);
        padding: 18px 26px;
        border-radius: 12px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .synthetic-banner {
        background: linear-gradient(90deg, rgba(230, 57, 70, 0.12) 0%, rgba(244, 162, 97, 0.12) 100%);
        border-left: 4px solid #e63946;
        padding: 8px 16px;
        border-radius: 6px;
        margin-bottom: 14px;
        color: #f1faee;
        font-size: 0.82rem;
    }
    
    .live-pulse {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #10b981;
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 10px #10b981;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.8; }
        50% { transform: scale(1.3); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.8; }
    }
    
    .status-badge-live {
        background: rgba(46, 196, 182, 0.2);
        color: #2ec4b6;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #2ec4b6;
        display: inline-flex;
        align-items: center;
        letter-spacing: 0.08em;
    }
    
    .status-badge-paused {
        background: rgba(244, 162, 97, 0.2);
        color: #f4a261;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #f4a261;
        display: inline-flex;
        align-items: center;
        letter-spacing: 0.08em;
    }
    
    .status-badge-alarm {
        background: rgba(230, 57, 70, 0.25);
        color: #e63946;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #e63946;
        display: inline-block;
        letter-spacing: 0.08em;
    }

    .bearing-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .bearing-card:hover {
        border-color: #60a5fa;
    }
    .bearing-card-header {
        font-size: 0.85rem;
        font-weight: 700;
        color: #93c5fd;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 6px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
    }
    
    .val-zone-A { color: #10b981; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size:1.02rem; }
    .val-zone-B { color: #38bdf8; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size:1.02rem; }
    .val-zone-C { color: #f59e0b; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size:1.02rem; }
    .val-zone-D { color: #ef4444; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size:1.02rem; }
    .val-temp-warn { color: #f59e0b; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .val-temp-alarm { color: #ef4444; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

    .explanation-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-left: 5px solid #38bdf8;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 14px 0;
    }
    .explanation-box-danger {
        background: #1f1d2b;
        border: 1px solid #451a1a;
        border-left: 5px solid #ef4444;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 14px 0;
    }
    
    .kpi-metric-box {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .kpi-metric-val {
        font-size: 1.45rem;
        font-weight: 700;
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
    }
    .kpi-metric-lbl {
        font-size: 0.70rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_framework():
    cfg = get_config()
    db_path = os.path.join(PROJECT_ROOT, "data", "database", "maintenance.db")
    repo = MaintenanceRepository(db_path=db_path)
    workflow = AgenticMaintenanceWorkflow(repository=repo)
    rule_engine = MultiEvidenceRuleEngine()
    
    # Anomaly detector
    model_path = os.path.join(PROJECT_ROOT, "outputs", "evaluation", "isolation_forest_model.pkl")
    detector = None
    explainer = None
    if os.path.exists(model_path):
        try:
            detector = AnomalyDetector.load(model_path)
            explainer = ModelExplainer(detector)
        except Exception:
            pass

    # Forecaster model
    forecaster_path = os.path.join(PROJECT_ROOT, "outputs", "models", "forecaster_model.pkl")
    forecaster_config = os.path.join(PROJECT_ROOT, "outputs", "models", "forecaster_config.json")
    forecaster = None
    if os.path.exists(forecaster_path):
        try:
            forecaster = SensorForecaster.load(forecaster_path, forecaster_config)
        except Exception:
            pass
            
    return cfg, repo, workflow, rule_engine, detector, explainer, forecaster


@st.cache_data
def load_all_datasets():
    feat_csv = os.path.join(PROJECT_ROOT, "data", "features", "wide_directional_features.csv")
    spec_csv = os.path.join(PROJECT_ROOT, "data", "generated", "synthetic_spectrum.csv")
    dummy_spec_csv = os.path.join(PROJECT_ROOT, "pump_imbalance_frequency_spectrum.csv")
    fault_events_csv = os.path.join(PROJECT_ROOT, "data", "generated", "synthetic_fault_events.csv")
    eval_rep_json = os.path.join(PROJECT_ROOT, "outputs", "reports", "forecasting_evaluation_report.json")
    
    df_wide = pd.read_csv(feat_csv) if os.path.exists(feat_csv) else pd.DataFrame()
    
    spec_dfs = []
    if os.path.exists(spec_csv):
        spec_dfs.append(pd.read_csv(spec_csv))
    if os.path.exists(dummy_spec_csv):
        spec_dfs.append(pd.read_csv(dummy_spec_csv))
    if spec_dfs:
        df_spec = pd.concat(spec_dfs, ignore_index=True).drop_duplicates(subset=["Machine_number", "Location", "Direction", "Frequency_Hz"])
    else:
        df_spec = pd.DataFrame()

    df_faults = pd.read_csv(fault_events_csv) if os.path.exists(fault_events_csv) else pd.DataFrame()
    
    eval_report = {}
    if os.path.exists(eval_rep_json):
        try:
            with open(eval_rep_json, "r") as f:
                eval_report = json.load(f)
        except Exception:
            pass
    
    if not df_wide.empty:
        df_wide["time stamp"] = pd.to_datetime(df_wide["time stamp"])
        
    return df_wide, df_spec, df_faults, eval_report


cfg, repo, workflow, rule_engine, detector, explainer, forecaster = load_framework()
df_wide, df_spec, df_faults, eval_report = load_all_datasets()


@st.cache_data
def get_machine_forecast_series(machine_id: str):
    """
    Computes and caches precomputed 1-step ahead forecasting predictions for the given machine.
    """
    if forecaster is None or df_wide.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    m_raw = df_wide[df_wide["Machine_number"] == machine_id].copy()
    if len(m_raw) < 10:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    try:
        X, y, feats, targets, meta = prepare_forecasting_dataset(
            df=m_raw,
            target_channels=DEFAULT_TARGET_CHANNELS,
            max_gap_days=1.0,
            lags=[1, 2, 3, 7],
            rolling_windows=[3, 7],
            require_targets=False
        )
        preds = forecaster.predict_dataframe(X)
        return X, y, preds, meta
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# -------------------------------------------------------------
# Top SCADA Workstation Header
# -------------------------------------------------------------
is_streaming = st.session_state.get("is_streaming", False)
stream_badge = (
    '<span class="status-badge-live"><span class="live-pulse"></span>LIVE STREAMING</span>'
    if is_streaming else
    '<span class="status-badge-paused">⏸️ STREAM PAUSED</span>'
)

st.markdown(f"""
<div class="scada-header">
    <div>
        <h2 style="color:#ffffff; margin:0; font-size:1.40rem; font-weight:700; letter-spacing:-0.02em;">
            ⚙️ Industrial Predictive Maintenance Workstation
        </h2>
        <div style="color:#94a3b8; font-size:0.80rem; margin-top:3px;">
            Hybrid Rule-Based (ISO 10816-7) &bull; Multi-Output ML Forecasting (Random Forest) &bull; Explainable AI &bull; Agentic Maintenance
        </div>
    </div>
    <div style="text-align:right;">
        {stream_badge}
        <div style="color:#64748b; font-size:0.75rem; margin-top:4px;">Europump 2013 Table 1 Compliant</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="synthetic-banner">
    ⚠️ <strong>SAFETY & SYNTHETIC DATA IDENTIFIER:</strong> 
    This system is an engineering decision-support tool. It is <strong>NOT</strong> an autonomous plant safety trip interlock. 
    Field telemetry and scenarios are tagged as <code>SYNTHETIC_SIMULATION</code> and verified against baseline recordings. 
    Diagnostic candidates represent evidence-backed hypotheses requiring human verification.
</div>
""", unsafe_allow_html=True)

if df_wide.empty:
    st.error("⚠️ Telemetry dataset not found. Run `python scripts/run_local_pipeline.py` to populate data.")
    st.stop()

# -------------------------------------------------------------
# Sidebar: Equipment Selection, Specs, and Standards
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Monitored Asset")
    
    all_machines = sorted(df_wide["Machine_number"].dropna().unique().tolist())
    
    if "selected_machine" not in st.session_state:
        st.session_state.selected_machine = "M1206" if "M1206" in all_machines else all_machines[0]
        
    sel_idx = all_machines.index(st.session_state.selected_machine) if st.session_state.selected_machine in all_machines else 0
    sel_machine = st.selectbox("Active Asset:", all_machines, index=sel_idx)
    if sel_machine != st.session_state.selected_machine:
        st.session_state.selected_machine = sel_machine
        st.session_state.stream_idx = 0
        st.rerun()
    
    # Machine Specs Lookup
    mach_cfg = cfg.get_machine(sel_machine) or {}
    mach_name = mach_cfg.get("name", f"Pump {sel_machine}")
    mach_cat = mach_cfg.get("category")
    mach_pwr = mach_cfg.get("nominal_power_kw")
    mach_rpm = mach_cfg.get("rated_speed_rpm", 3000)
    mach_hz = mach_cfg.get("running_frequency_hz", mach_rpm / 60.0)
    
    st.markdown(f"**Asset:** `{sel_machine}` — *{mach_name}*")
    
    # Display Specs Card
    st.markdown("---")
    st.markdown("#### 📋 Technical Specifications")
    st.write(f"• **Category:** `{mach_cat or 'INCOMPLETE'}`")
    st.write(f"• **Power:** `{mach_pwr or 'N/A'} kW`")
    st.write(f"• **Rated Speed:** `{mach_rpm} RPM` ({mach_hz:.1f} Hz 1X)")
    st.write(f"• **Pump Bearing:** `{mach_cfg.get('bearing_type_pump', 'Rolling Element')}`")
    st.write(f"• **Motor Bearing:** `{mach_cfg.get('bearing_type_motor', 'Rolling Element')}`")
    st.write(f"• **Vane Pass Freq:** `{mach_cfg.get('impeller_vanes', 5) * mach_hz:.1f} Hz` ({mach_cfg.get('impeller_vanes', 5)} vanes)")
    
    # Applicable ISO 10816-7 Limits Card
    st.markdown("---")
    st.markdown("#### 🛡️ ISO 10816-7 Reference Limits")
    if mach_cat and mach_pwr is not None:
        limits = cfg.get_standards_limits(mach_cat, mach_pwr)
        z_b = limits["zones"]["B"]
        z_c = limits["zones"]["C"]
        al_lim = limits["alarm_limit"]
        tr_lim = limits["trip_limit"]
        st.write(f"• **Zone A/B Limit:** `{z_b} mm/s` (Acceptable)")
        st.write(f"• **Zone B/C Limit:** `{z_c} mm/s` (Unsatisfactory)")
        st.write(f"• **Alarm Limit (1.25×B):** `{al_lim} mm/s`")
        st.write(f"• **Trip Limit (1.25×C):** `{tr_lim} mm/s`")
    else:
        st.warning("⚠️ Machine configuration is incomplete. Evaluation suspended per ISO standard.")
        
    st.markdown("---")
    st.markdown("#### ⚡ Quick-Jump to Benchmark Events")
    quick_events = [
        ("M1206", "2024-04-18", "Rotor Imbalance (Impeller Mass Loss)"),
        ("M1209", "2024-08-25", "Shaft Misalignment (High Coupling Axial)"),
        ("M1212", "2025-02-15", "Bearing Defect & Thermal Overheating"),
        ("M1215", "2025-06-20", "Mechanical Looseness (Structural Slack)"),
        ("M1217", "2025-09-12", "Hydraulic Cavitation (Suction Choke)"),
        ("M1205", "2024-10-28", "High Reading Excursion (Plant Raw)")
    ]
    for q_m, q_d, q_desc in quick_events:
        if st.button(f"Jump: {q_m} ({q_d})", key=f"q_{q_m}_{q_d}"):
            st.session_state.selected_machine = q_m
            st.session_state.jump_date = q_d
            st.session_state.is_streaming = False
            st.rerun()

# Filter data for active machine
m_data = df_wide[df_wide["Machine_number"] == sel_machine].sort_values("time stamp").reset_index(drop=True)
if m_data.empty:
    st.warning(f"No records found for machine {sel_machine}.")
    st.stop()

# Retrieve precomputed forecasting data for active machine
f_X, f_y, f_preds, f_meta = get_machine_forecast_series(sel_machine)

# -------------------------------------------------------------
# Main Navigation View Switchboard
# -------------------------------------------------------------
selected_view = st.radio(
    "Workstation Navigation:",
    [
        "🔴 Real-Time Live Monitor & ML Forecast",
        "📅 Date-to-Date Report, Trends & Frequency Analysis"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

CHANNELS_DISPLAY = [
    ("P1", "Pump NDE", "P1-V", "Vertical Velocity"),
    ("P1", "Pump NDE", "P1-H", "Horizontal Velocity"),
    ("P1", "Pump NDE", "P1-A", "Axial Velocity"),
    ("P1", "Pump NDE", "P1-T", "Housing Temperature"),
    ("P2", "Pump DE", "P2-V", "Vertical Velocity"),
    ("P2", "Pump DE", "P2-H", "Horizontal Velocity"),
    ("P2", "Pump DE", "P2-A", "Axial Velocity"),
    ("P2", "Pump DE", "P2-T", "Housing Temperature"),
    ("P3", "Motor DE", "P3-V", "Vertical Velocity"),
    ("P3", "Motor DE", "P3-H", "Horizontal Velocity"),
    ("P3", "Motor DE", "P3-A", "Axial Velocity"),
    ("P3", "Motor DE", "P3-T", "Housing Temperature"),
    ("P4", "Motor NDE", "P4-V", "Vertical Velocity"),
    ("P4", "Motor NDE", "P4-H", "Horizontal Velocity"),
    ("P4", "Motor NDE", "P4-A", "Axial Velocity"),
    ("P4", "Motor NDE", "P4-T", "Housing Temperature"),
]

# Helper function to classify value zone
def get_channel_zone(val: float, z_b: float = 5.1, z_c: float = 8.5) -> str:
    if val is None or np.isnan(val):
        return "N/A"
    if val <= (z_b * 0.65):
        return "Zone A"
    elif val <= z_b:
        return "Zone B"
    elif val <= z_c:
        return "Zone C"
    else:
        return "Zone D"

def format_zone_span(val: float, delta_str: str, z_b: float = 5.1, z_c: float = 8.5) -> str:
    z = get_channel_zone(val, z_b, z_c)
    css_class = f"val-zone-{z[-1]}"
    return f'<span class="{css_class}">{val:.2f} mm/s</span> <span style="font-size:0.75rem; color:#94a3b8;">({z})</span> {delta_str}'

def format_temp_span(temp: float, delta_str: str) -> str:
    if temp is None or np.isnan(temp):
        return "N/A"
    if temp >= 85.0:
        return f'<span class="val-temp-alarm">{temp:.1f}°C (TRIP)</span> {delta_str}'
    elif temp >= 70.0:
        return f'<span class="val-temp-warn">{temp:.1f}°C (WARN)</span> {delta_str}'
    else:
        return f'<span style="color:#10b981; font-weight:600; font-family:JetBrains Mono,monospace;">{temp:.1f}°C (NORM)</span> {delta_str}'

def get_delta_str(curr_val: float, prev_val: float) -> str:
    if curr_val is None or prev_val is None or np.isnan(curr_val) or np.isnan(prev_val):
        return ""
    diff = curr_val - prev_val
    if abs(diff) < 0.02:
        return '<span style="color:#64748b; font-size:0.72rem;">(±0.0)</span>'
    elif diff > 0:
        return f'<span style="color:#f87171; font-size:0.72rem; font-weight:600;">(▲ +{diff:.2f})</span>'
    else:
        return f'<span style="color:#34d399; font-size:0.72rem; font-weight:600;">(▼ {diff:.2f})</span>'


# =============================================================
# VIEW 1: REAL-TIME LIVE MONITOR & ML FORECAST
# =============================================================
if selected_view == "🔴 Real-Time Live Monitor & ML Forecast" or selected_view == "🔴 Real-Time Hybrid Monitor (Rule Assessment & ML Forecast)":
    st.markdown("### 🔴 Real-Time Live Monitor & ML Forecast")
    st.caption("Unified industrial workstation combining ISO 10816-7 / Europump 2013 Table 1 real-time rule assessment on incoming data, prominent fault type output, guideline threshold notifications, and same-page Random Forest next-day forecasting.")

    if "stream_idx" not in st.session_state:
        st.session_state.stream_idx = 0

    if "jump_date" in st.session_state and st.session_state.jump_date is not None:
        target_date = pd.to_datetime(st.session_state.jump_date).date()
        matching_indices = m_data.index[m_data["time stamp"].dt.date == target_date].tolist()
        if matching_indices:
            st.session_state.stream_idx = matching_indices[0]
        st.session_state.jump_date = None

    if st.session_state.stream_idx >= len(m_data):
        st.session_state.stream_idx = len(m_data) - 1
    if st.session_state.stream_idx < 0:
        st.session_state.stream_idx = 0
        
    curr_idx = st.session_state.stream_idx
    prev_idx = max(0, curr_idx - 1)
    
    curr_row = m_data.iloc[curr_idx]
    prev_row = m_data.iloc[prev_idx]
    curr_date_str = str(curr_row["time stamp"])[:10]

    # 1. Controls Toolbar
    col_c1, col_c2, col_c3, col_c4, col_c5, col_c6 = st.columns([1.5, 1.2, 0.8, 0.8, 0.8, 2.5])
    
    with col_c1:
        if st.session_state.get("is_streaming", False):
            if st.button("⏸️ Pause Live Stream", use_container_width=True, type="primary"):
                st.session_state.is_streaming = False
                st.rerun()
        else:
            if st.button("▶️ Start Live Stream", use_container_width=True, type="primary"):
                st.session_state.is_streaming = True
                st.rerun()

    with col_c2:
        speed_sel = st.selectbox(
            "Update Speed:",
            ["1.0s (Normal)", "0.5s (Fast)", "2.0s (Slow)"],
            index=0,
            label_visibility="collapsed"
        )
        delay_map = {"1.0s (Normal)": 1.0, "0.5s (Fast)": 0.5, "2.0s (Slow)": 2.0}
        stream_delay = delay_map[speed_sel]

    with col_c3:
        if st.button("⏮️ Prev", use_container_width=True):
            st.session_state.is_streaming = False
            st.session_state.stream_idx = max(0, st.session_state.stream_idx - 1)
            st.rerun()

    with col_c4:
        if st.button("⏭️ Next", use_container_width=True):
            st.session_state.is_streaming = False
            st.session_state.stream_idx = min(len(m_data) - 1, st.session_state.stream_idx + 1)
            st.rerun()

    with col_c5:
        if st.button("🔁 Reset", use_container_width=True):
            st.session_state.is_streaming = False
            st.session_state.stream_idx = 0
            st.rerun()

    with col_c6:
        scrub_slider = st.slider(
            "Timeline Position:",
            min_value=0,
            max_value=len(m_data) - 1,
            value=curr_idx,
            format="Day %d",
            label_visibility="collapsed"
        )
        if scrub_slider != curr_idx:
            st.session_state.is_streaming = False
            st.session_state.stream_idx = scrub_slider
            st.rerun()

    # 2. Real-Time Processing Output Status Banner (Including Forecast Zone)
    assessment = assess_machine_telemetry_row(curr_row)
    gov_zone = assessment["governing_zone"]
    gov_zone_short = get_short_zone_name(gov_zone)
    max_vib = assessment["max_vibration_rms"]
    gov_loc = assessment["governing_location"]
    alarm_stat = assessment["highest_alarm_status"]
    
    anom_score = float(curr_row.get("anomaly_score", 0.0))
    is_anom = bool(curr_row.get("is_anomaly", 0))
    max_temp = max(curr_row.get("P1-T", 0.0), curr_row.get("P2-T", 0.0), curr_row.get("P3-T", 0.0), curr_row.get("P4-T", 0.0))

    # Evaluate rule engine for real-time fault candidate detection
    eval_res = rule_engine.evaluate(
        machine_id=sel_machine,
        telemetry_row=curr_row,
        governing_zone=gov_zone
    )
    has_fault = bool(eval_res.candidates)
    top_cand = eval_res.dominant_hypothesis if has_fault else None
    fault_short_title = top_cand.fault_name.upper() if has_fault else "NORMAL OPERATION"
    fault_conf = f"{top_cand.confidence_score*100:.0f}%" if has_fault else "100%"
    fault_color = "#ef4444" if ("Zone D" in gov_zone or (top_cand and top_cand.confidence_score >= 0.85)) else ("#f59e0b" if has_fault else "#10b981")

    # Evaluate ML predicted next-day readings and zone comparison
    curr_date = pd.to_datetime(curr_row["time stamp"]).date()
    sample_preds = {}
    next_ts_str = None
    comparison = None
    is_warmup = False

    if not f_preds.empty and not f_meta.empty:
        meta_dates = pd.to_datetime(f_meta["timestamp"]).dt.date
        matches = f_meta.index[meta_dates == curr_date].tolist()
        if matches:
            match_idx = matches[0]
            raw_preds = f_preds.iloc[match_idx].to_dict()
            # Store both with and without 'pred_' prefix for seamless access across components
            sample_preds = {k: v for k, v in raw_preds.items()}
            for k, v in raw_preds.items():
                if k.startswith("pred_"):
                    sample_preds[k.replace("pred_", "")] = v

            next_ts_str = str(f_meta.iloc[match_idx].get("next_timestamp", ""))[:10]
            comparison = compare_current_and_predicted_zones(
                machine_id=sel_machine,
                current_row=curr_row,
                predicted_readings=sample_preds,
                forecast_timestamp=next_ts_str
            )
        elif not meta_dates.empty and curr_date < meta_dates.min():
            is_warmup = True

    if is_warmup:
        pred_zone_str = "Warmup (Day 1–7)"
        pred_zone_color = "#94a3b8"
    elif comparison:
        pred_zone_str = comparison.get("predicted_zone_short", "Refused")
        pred_zone_color = (
            "#10b981" if "Zone A" in pred_zone_str else (
                "#38bdf8" if "Zone B" in pred_zone_str else (
                    "#f59e0b" if "Zone C" in pred_zone_str else (
                        "#ef4444" if "Zone D" in pred_zone_str else "#64748b"
                    )
                )
            )
        )
    else:
        pred_zone_str = "Refused" if not mach_cat or mach_pwr is None else "N/A"
        pred_zone_color = "#64748b"

    stat_c1, stat_c2, stat_c3, stat_c4, stat_c5 = st.columns([1.1, 1.1, 1.1, 1.1, 2.0])
    
    with stat_c1:
        st.markdown(f"""
        <div class="kpi-metric-box">
            <div class="kpi-metric-val" style="font-size:1.10rem; color:#f1faee;">{curr_date_str}</div>
            <div class="kpi-metric-lbl">Current Date (Day {curr_idx+1})</div>
        </div>
        """, unsafe_allow_html=True)
        
    with stat_c2:
        zone_color = "#10b981" if "Zone A" in gov_zone_short else ("#38bdf8" if "Zone B" in gov_zone_short else ("#f59e0b" if "Zone C" in gov_zone_short else ("#ef4444" if "Zone D" in gov_zone_short else "#64748b")))
        st.markdown(f"""
        <div class="kpi-metric-box" style="border-color:{zone_color};">
            <div class="kpi-metric-val" style="color:{zone_color};">{gov_zone_short}</div>
            <div class="kpi-metric-lbl">Current ISO Severity</div>
        </div>
        """, unsafe_allow_html=True)

    with stat_c3:
        st.markdown(f"""
        <div class="kpi-metric-box" style="border-color:{pred_zone_color};">
            <div class="kpi-metric-val" style="color:{pred_zone_color};">{pred_zone_str}</div>
            <div class="kpi-metric-lbl">Predicted Next-Day Zone</div>
        </div>
        """, unsafe_allow_html=True)
        
    with stat_c4:
        st.markdown(f"""
        <div class="kpi-metric-box">
            <div class="kpi-metric-val" style="color:#f59e0b;">{max_vib:.2f} <span style="font-size:0.85rem;">mm/s</span></div>
            <div class="kpi-metric-lbl">Peak Vibration ({gov_loc})</div>
        </div>
        """, unsafe_allow_html=True)
        
    with stat_c5:
        st.markdown(f"""
        <div class="kpi-metric-box" style="border: 2px solid {fault_color}; box-shadow: 0 0 16px {fault_color}55; background: #131722;">
            <div class="kpi-metric-val" style="color:{fault_color}; font-size:1.05rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                {fault_short_title}
            </div>
            <div class="kpi-metric-lbl" style="color:#cbd5e1; font-weight:700;">
                🎯 FAULT TYPE OUTPUT &bull; CONFIDENCE: {fault_conf}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Dual-Zone Severity Assessment & Predictive Transition Banner
    if comparison is not None:
        zc_c1, zc_c2, zc_c3 = st.columns([1.2, 1.2, 1.6])
        
        with zc_c1:
            cz_short = comparison.get("current_zone_short", get_short_zone_name(gov_zone))
            c_color = "#10b981" if "Zone A" in cz_short else ("#38bdf8" if "Zone B" in cz_short else ("#f59e0b" if "Zone C" in cz_short else ("#ef4444" if "Zone D" in cz_short else "#64748b")))
            st.markdown(f"""
            <div class="kpi-metric-box" style="border-color:{c_color};">
                <div class="kpi-metric-val" style="color:{c_color};">{cz_short}</div>
                <div class="kpi-metric-lbl">Current Rule Zone ({comparison['current_location']} - {comparison['current_peak_vib']:.2f} mm/s)</div>
            </div>
            """, unsafe_allow_html=True)

        with zc_c2:
            pz_short = comparison.get("predicted_zone_short", get_short_zone_name(comparison["predicted_zone"]))
            p_color = "#10b981" if "Zone A" in pz_short else ("#38bdf8" if "Zone B" in pz_short else ("#f59e0b" if "Zone C" in pz_short else ("#ef4444" if "Zone D" in pz_short else "#64748b")))
            st.markdown(f"""
            <div class="kpi-metric-box" style="border-color:{p_color};">
                <div class="kpi-metric-val" style="color:{p_color};">{pz_short}</div>
                <div class="kpi-metric-lbl">ML Forecasted Zone ({comparison['predicted_location']} - {comparison['predicted_peak_vib']:.2f} mm/s)</div>
            </div>
            """, unsafe_allow_html=True)

        with zc_c3:
            box_style = "background:#3b1111; border:1px solid #ef4444;" if comparison["is_hazardous"] else (
                "background:#3b2a11; border:1px solid #f59e0b;" if comparison["is_degradation"] else "background:#0f2b1d; border:1px solid #10b981;"
            )
            st.markdown(f"""
            <div style="{box_style} border-radius:8px; padding:12px; height:100%;">
                <div style="font-size:0.75rem; text-transform:uppercase; color:#cbd5e1; font-weight:700;">Zone Transition Alert</div>
                <div style="font-size:0.88rem; color:#f8fafc; margin-top:4px; font-weight:600;">{comparison['transition_alert']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
    elif is_warmup:
        min_meta_d = pd.to_datetime(f_meta["timestamp"]).dt.date.min() if not f_meta.empty else "Day 8"
        st.markdown(
            f'<div class="explanation-box" style="border-left-color: #64748b; background: #1e293b; margin-top:0;">'
            f'<div style="display:flex; align-items:center; gap:10px;">'
            f'<span style="font-size:1.3rem;">⏳</span>'
            f'<div>'
            f'<strong style="color:#94a3b8; font-size:0.95rem;">HISTORICAL WARMUP PERIOD (DAYS 1–7) &bull; NEXT-DAY ML FORECASTING ACTIVE ON DAY 8 ({min_meta_d})</strong>'
            f'<div style="font-size:0.85rem; color:#cbd5e1; margin-top:3px;">'
            f'Next-day sensor forecasting computes 1, 2, 3, and 7-day historical lags alongside 3-day and 7-day rolling window statistics. Daily predictions activate automatically from Day 8 onwards once historical feature context is established.'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div><br>',
            unsafe_allow_html=True
        )

    if mach_cat and mach_pwr is not None:
        limits = cfg.get_standards_limits(mach_cat, mach_pwr)
        lim_b = limits["zones"]["B"]
        lim_c = limits["zones"]["C"]
        al_lim = limits["alarm_limit"]
        tr_lim = limits["trip_limit"]
    else:
        lim_b, lim_c, al_lim, tr_lim = 4.0, 6.6, 5.0, 8.25

    # 3. Dynamic Guideline Threshold Notification (ISO 10816-7 / Europump 2013 Table 1)
    if not mach_cat or mach_pwr is None:
        st.markdown(
            '<div class="explanation-box" style="border-left-color: #64748b; background: #1e293b; margin-top:0;">'
            '<div style="display:flex; align-items:center; gap:10px;">'
            '<span style="font-size:1.4rem;">⚙️</span>'
            '<div>'
            '<strong style="color:#94a3b8; font-size:0.95rem;">ISO 10816-7 THRESHOLD ASSESSMENT SUSPENDED — INCOMPLETE MACHINE METADATA</strong>'
            '<div style="font-size:0.85rem; color:#cbd5e1; margin-top:3px;">'
            'Pump Category or Rated Power is missing in equipment registry. Europump 2013 Table 1 strictly prohibits assuming default limits. Threshold alerts and zone evaluations are withheld per engineering safety guidelines.'
            '</div>'
            '</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )
    elif max_vib <= lim_b:
        st.markdown(
            f'<div class="explanation-box" style="border-left-color: #10b981; background: #0c2317; margin-top:0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<strong style="font-size:0.98rem; color:#10b981;">'
            f'🟢 GUIDELINE STATUS: NORMAL OPERATION ({gov_zone_short.upper()})'
            f'</strong>'
            f'<div style="font-size:0.86rem; color:#cbd5e1; margin-top:3px;">'
            f'Peak vibration is <strong>{max_vib:.2f} mm/s</strong> at <strong>{gov_loc}</strong>, safely below the ISO 10816-7 Zone B continuous permissible limit (<strong>{lim_b:.1f} mm/s</strong>) for Category {mach_cat} ({mach_pwr} kW). Baseline dynamic operation is stable.'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<span class="status-badge-live" style="background:#065f46; color:#a7f3d0; border-color:#059669; font-size:0.8rem;">WITHIN LIMITS</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    elif max_vib <= al_lim:
        st.markdown(
            f'<div class="explanation-box" style="border-left-color: #f59e0b; background: #2d1f08; margin-top:0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<strong style="font-size:1.02rem; color:#f59e0b;">'
            f'⚠️ THRESHOLD NOTIFICATION: VIBRATION REACHED ZONE C ({gov_zone_short.upper()})'
            f'</strong>'
            f'<div style="font-size:0.88rem; color:#f1faee; margin-top:4px; line-height:1.45;">'
            f'Peak vibration at <strong>{gov_loc}</strong> reached <strong>{max_vib:.2f} mm/s</strong>, exceeding the Zone B permissible limit (<strong>{lim_b:.1f} mm/s</strong>) for Category {mach_cat} ({mach_pwr} kW).<br>'
            f'<strong style="color:#fbbf24;">🔬 FREQUENCY SPECTRUM ANALYSIS (FFT) REQUIRED:</strong> Vibration has entered the unsatisfactory operating band. Harmonic order analysis required to isolate 1X unbalance or 2X misalignment harmonics before mechanical degradation accelerates.'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<span class="status-badge-warn" style="font-size:0.82rem;">ZONE C REACHED</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    elif max_vib <= lim_c:
        st.markdown(
            f'<div class="explanation-box" style="border-left-color: #f97316; background: #331d09; margin-top:0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<strong style="font-size:1.02rem; color:#f97316;">'
            f'🟠 GUIDELINE ALARM NOTIFICATION: ISO 10816-7 ALARM THRESHOLD EXCEEDED'
            f'</strong>'
            f'<div style="font-size:0.88rem; color:#f1faee; margin-top:4px; line-height:1.45;">'
            f'Peak vibration at <strong>{gov_loc}</strong> reached <strong>{max_vib:.2f} mm/s</strong>, exceeding the 1.25× Zone B Alarm Threshold (<strong>{al_lim:.1f} mm/s</strong>) for Category {mach_cat} ({mach_pwr} kW).<br>'
            f'<strong style="color:#fdba74;">🔬 FREQUENCY SPECTRUM ANALYSIS (FFT) MANDATORY:</strong> Perform narrowband FFT spectral decomposition immediately to isolate 1X unbalance, 2X misalignment, or bearing defect frequencies and schedule preventive overhaul.'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<span class="status-badge-alarm" style="background:#7c2d12; border-color:#ea580c; font-size:0.82rem;">ALARM LEVEL</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="explanation-box-danger" style="border-left-color: #ef4444; background: #3b1111; margin-top:0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<strong style="font-size:1.06rem; color:#ef4444;">'
            f'🔴 CRITICAL TRIP NOTIFICATION: ZONE D UNACCEPTABLE / TRIP LIMIT EXCEEDED'
            f'</strong>'
            f'<div style="font-size:0.88rem; color:#f1faee; margin-top:4px; line-height:1.45;">'
            f'Peak vibration reached <strong>{max_vib:.2f} mm/s</strong> at <strong>{gov_loc}</strong>, exceeding the Zone C limit (<strong>{lim_c:.1f} mm/s</strong>, Trip: <strong>{tr_lim:.1f} mm/s</strong>) for Category {mach_cat} ({mach_pwr} kW).<br>'
            f'<strong style="color:#fca5a5;">🚨 URGENT ACTION: HIGH RISK OF MECHANICAL BREAKDOWN!</strong> Immediate machine shutdown / load shedding recommended. Emergency frequency spectrum analysis (FFT) and physical teardown required before restart.'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<span class="status-badge-alarm" style="font-size:0.85rem; padding:6px 10px;">CRITICAL TRIP</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # 4. Primary Highlighted Fault Type Output & Plain-English Explanation
    st.markdown("#### 🎯 Primary Fault Type Output & Plain-English Explanation")
    
    if not has_fault:
        st.markdown(
            f'<div class="explanation-box" style="border-left: 6px solid #10b981; border: 2px solid #10b981; box-shadow: 0 0 16px rgba(16,185,129,0.25); background:#0c2317; margin-top:0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
            f'<h3 style="color:#10b981; margin:0; font-size:1.20rem;">🟢 DETECTED FAULT TYPE: NORMAL OPERATING CONDITION</h3>'
            f'<span class="status-badge-live" style="background:#065f46; color:#a7f3d0; border-color:#059669; font-size:0.85rem;">CONFIDENCE: 100%</span>'
            f'</div>'
            f'<p style="color:#cbd5e1; margin:0; font-size:0.92rem; line-height:1.5;">'
            f'All 16 directional vibration channels and bearing temperatures are operating well within acceptable ISO 10816-7 Zone A/B limits. Dynamic balance and shaft alignment are stable.'
            f'</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        box_class = "explanation-box-danger" if "Zone D" in gov_zone or top_cand.confidence_score >= 0.85 else "explanation-box"
        supp_items = "".join(f"<li>{s}</li>" for s in top_cand.supporting_evidence)
        miss_items = "".join(f"<li>{m}</li>" for m in top_cand.missing_evidence)
        
        card_html = (
            f'<div class="{box_class}" style="border: 2px solid {fault_color}; box-shadow: 0 0 24px {fault_color}55; margin: 12px 0; background: linear-gradient(135deg, #1c1427 0%, #0f172a 100%);">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
            f'<h3 style="color:#ffffff; margin:0; font-size:1.30rem;">'
            f'🎯 PRIMARY DETECTED FAULT TYPE: <span style="color:#fbbf24; text-decoration: underline; font-weight:800;">{top_cand.fault_name.upper()}</span>'
            f'</h3>'
            f'<span class="status-badge-alarm" style="font-size:0.88rem; padding:6px 14px; font-weight:800; background:#7c2d12; border-color:#ea580c;">CONFIDENCE: {top_cand.confidence_score*100:.0f}%</span>'
            f'</div>'
            f'<div style="color:#94a3b8; font-size:0.84rem; margin-bottom:12px;">'
            f'<strong>Fault Family:</strong> <code>{top_cand.fault_family}</code> &bull; '
            f'<strong>Evidence Level:</strong> <code>{top_cand.evidence_level}</code> &bull; '
            f'<strong>Governing Severity:</strong> <code>{gov_zone}</code>'
            f'</div>'
            f'<div style="background:rgba(0,0,0,0.35); border-radius:6px; padding:12px; margin-bottom:12px; border-left:4px solid #38bdf8;">'
            f'<h5 style="color:#38bdf8; margin:0 0 4px 0; font-size:0.92rem;">📖 Plain-English Diagnostic Explanation:</h5>'
            f'<p style="color:#f1faee; margin:0; font-size:0.94rem; line-height:1.5;">{top_cand.selection_reason}</p>'
            f'</div>'
            f'<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">'
            f'<div>'
            f'<h5 style="color:#10b981; margin:0 0 6px 0; font-size:0.85rem;">✅ Supporting Sensor Evidence:</h5>'
            f'<ul style="color:#cbd5e1; margin:0; padding-left:18px; font-size:0.85rem;">{supp_items}</ul>'
            f'</div>'
            f'<div>'
            f'<h5 style="color:#f59e0b; margin:0 0 6px 0; font-size:0.85rem;">⚠️ Missing Checks & Diagnostic Uncertainty:</h5>'
            f'<ul style="color:#cbd5e1; margin:0; padding-left:18px; font-size:0.85rem;">{miss_items}</ul>'
            f'</div>'
            f'</div>'
            f'<div style="margin-top:12px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">'
            f'<strong style="color:#38bdf8; font-size:0.88rem;">💡 Recommended Immediate Maintenance Action:</strong>'
            f'<span style="color:#e2e8f0; font-size:0.88rem;"> {top_cand.recommended_action}</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    # 5. Physical Machine Schematic & 4 Live Bearing Cards
    st.markdown("#### 📡 Live Multi-Point Sensor Telemetry (P1 → P4)")
    st.caption("Live vibration velocity and bearing temperatures with day-over-day directional delta indicators.")
    
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    
    with b_col1:
        d_p1v = get_delta_str(curr_row.get('P1-V'), prev_row.get('P1-V'))
        d_p1h = get_delta_str(curr_row.get('P1-H'), prev_row.get('P1-H'))
        d_p1a = get_delta_str(curr_row.get('P1-A'), prev_row.get('P1-A'))
        d_p1t = get_delta_str(curr_row.get('P1-T'), prev_row.get('P1-T'))
        st.markdown(f"""
        <div class="bearing-card">
            <div class="bearing-card-header">
                <span>P1: Pump NDE</span>
                <span style="color:#64748b;">Non-Drive</span>
            </div>
            <div style="font-size:0.85rem; line-height:1.75;">
                <div>Vertical (V): {format_zone_span(curr_row.get('P1-V'), d_p1v, lim_b, lim_c)}</div>
                <div>Horizontal (H): {format_zone_span(curr_row.get('P1-H'), d_p1h, lim_b, lim_c)}</div>
                <div>Axial (A): {format_zone_span(curr_row.get('P1-A'), d_p1a, lim_b, lim_c)}</div>
                <div style="margin-top:6px; border-top:1px dashed #374151; padding-top:4px;">
                    Housing Temp: {format_temp_span(curr_row.get('P1-T'), d_p1t)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b_col2:
        d_p2v = get_delta_str(curr_row.get('P2-V'), prev_row.get('P2-V'))
        d_p2h = get_delta_str(curr_row.get('P2-H'), prev_row.get('P2-H'))
        d_p2a = get_delta_str(curr_row.get('P2-A'), prev_row.get('P2-A'))
        d_p2t = get_delta_str(curr_row.get('P2-T'), prev_row.get('P2-T'))
        st.markdown(f"""
        <div class="bearing-card">
            <div class="bearing-card-header">
                <span>P2: Pump DE</span>
                <span style="color:#64748b;">Drive End</span>
            </div>
            <div style="font-size:0.85rem; line-height:1.75;">
                <div>Vertical (V): {format_zone_span(curr_row.get('P2-V'), d_p2v, lim_b, lim_c)}</div>
                <div>Horizontal (H): {format_zone_span(curr_row.get('P2-H'), d_p2h, lim_b, lim_c)}</div>
                <div>Axial (A): {format_zone_span(curr_row.get('P2-A'), d_p2a, lim_b, lim_c)}</div>
                <div style="margin-top:6px; border-top:1px dashed #374151; padding-top:4px;">
                    Housing Temp: {format_temp_span(curr_row.get('P2-T'), d_p2t)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b_col3:
        d_p3v = get_delta_str(curr_row.get('P3-V'), prev_row.get('P3-V'))
        d_p3h = get_delta_str(curr_row.get('P3-H'), prev_row.get('P3-H'))
        d_p3a = get_delta_str(curr_row.get('P3-A'), prev_row.get('P3-A'))
        d_p3t = get_delta_str(curr_row.get('P3-T'), prev_row.get('P3-T'))
        st.markdown(f"""
        <div class="bearing-card">
            <div class="bearing-card-header">
                <span>P3: Motor DE</span>
                <span style="color:#64748b;">Coupling Side</span>
            </div>
            <div style="font-size:0.85rem; line-height:1.75;">
                <div>Vertical (V): {format_zone_span(curr_row.get('P3-V'), d_p3v, lim_b, lim_c)}</div>
                <div>Horizontal (H): {format_zone_span(curr_row.get('P3-H'), d_p3h, lim_b, lim_c)}</div>
                <div>Axial (A): {format_zone_span(curr_row.get('P3-A'), d_p3a, lim_b, lim_c)}</div>
                <div style="margin-top:6px; border-top:1px dashed #374151; padding-top:4px;">
                    Housing Temp: {format_temp_span(curr_row.get('P3-T'), d_p3t)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with b_col4:
        d_p4v = get_delta_str(curr_row.get('P4-V'), prev_row.get('P4-V'))
        d_p4h = get_delta_str(curr_row.get('P4-H'), prev_row.get('P4-H'))
        d_p4a = get_delta_str(curr_row.get('P4-A'), prev_row.get('P4-A'))
        d_p4t = get_delta_str(curr_row.get('P4-T'), prev_row.get('P4-T'))
        st.markdown(f"""
        <div class="bearing-card">
            <div class="bearing-card-header">
                <span>P4: Motor NDE</span>
                <span style="color:#64748b;">Fan End</span>
            </div>
            <div style="font-size:0.85rem; line-height:1.75;">
                <div>Vertical (V): {format_zone_span(curr_row.get('P4-V'), d_p4v, lim_b, lim_c)}</div>
                <div>Horizontal (H): {format_zone_span(curr_row.get('P4-H'), d_p4h, lim_b, lim_c)}</div>
                <div>Axial (A): {format_zone_span(curr_row.get('P4-A'), d_p4a, lim_b, lim_c)}</div>
                <div style="margin-top:6px; border-top:1px dashed #374151; padding-top:4px;">
                    Housing Temp: {format_temp_span(curr_row.get('P4-T'), d_p4t)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Directional Ratios Row
    r_col1, r_col2, r_col3 = st.columns(3)
    p2_ra = curr_row.get("P2_radial_to_axial_ratio", 1.0)
    p2_hv = curr_row.get("P2_h_to_v_ratio", 1.0)
    c_axial = curr_row.get("coupling_axial_ratio", 1.0)
    
    with r_col1:
        ra_flag = "⚠️ Elevated (>3.0 Unbalance Indication)" if p2_ra > 3.0 else "Normal (<2.5)"
        st.caption(f"**P2 Radial-to-Axial Ratio:** `{p2_ra:.2f}` — {ra_flag}")
    with r_col2:
        hv_flag = "⚠️ Asymmetric (>2.0 Looseness Indication)" if p2_hv > 2.0 or p2_hv < 0.5 else "Balanced (~1.0)"
        st.caption(f"**P2 H-to-V Ratio:** `{p2_hv:.2f}` — {hv_flag}")
    with r_col3:
        ax_flag = "⚠️ Elevated (>1.5 Misalignment Indication)" if c_axial > 1.5 else "Normal Coupling Axis"
        st.caption(f"**Coupling Axial Ratio (P2/P3):** `{c_axial:.2f}` — {ax_flag}")



    # 5. Current Observed vs ML Forecasted Next-Day Telemetry Matrix (All 16 Channels)
    if sample_preds:
        st.markdown(f"#### 📋 Current Observed vs ML Forecasted Next-Day Telemetry Matrix (Current Date: `{curr_date_str}` ➔ Target Forecast: `{next_ts_str}`)")
        st.caption("Real-time side-by-side comparison of current sensor readings ($t$) against ML multi-output Random Forest predictions ($t+1$) evaluated through ISO 10816-7 rules.")
        
        comparison_rows = []
        for loc_code, loc_name, ch, desc in CHANNELS_DISPLAY:
            cur_val = curr_row.get(ch, np.nan)
            pred_k = f"pred_{ch}" if f"pred_{ch}" in sample_preds else ch
            pred_val = sample_preds.get(pred_k, np.nan)
            
            # Formatting
            if pd.notna(cur_val) and pd.notna(pred_val):
                diff = pred_val - cur_val
                delta_str = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
                trend_str = "▲ Rising" if diff > 0.05 else ("▼ Falling" if diff < -0.05 else "➖ Stable")
            else:
                diff = np.nan
                delta_str = "N/A"
                trend_str = "N/A"

            is_temp = "Temp" in desc
            if is_temp:
                cur_z = "Normal (<70°C)" if cur_val < 70 else ("Warning (70-85°C)" if cur_val < 85 else "Trip (>85°C)")
                pred_z = "Normal (<70°C)" if pred_val < 70 else ("Warning (70-85°C)" if pred_val < 85 else "Trip (>85°C)")
                unit = "°C"
            else:
                if not mach_cat or mach_pwr is None:
                    cur_z = "Refused (Incomplete Config)"
                    pred_z = "Refused (Incomplete Config)"
                else:
                    cur_z = get_channel_zone(cur_val, lim_b, lim_c)
                    pred_z = get_channel_zone(pred_val, lim_b, lim_c)
                unit = "mm/s"

            comparison_rows.append({
                "Bearing Point": f"{loc_code}: {loc_name}",
                "Sensor Channel": f"{ch} ({desc})",
                "Current Reading (t)": f"{cur_val:.2f} {unit}" if pd.notna(cur_val) else "N/A",
                "Current Rule Zone": cur_z,
                "ML Forecast (t+1)": f"{pred_val:.2f} {unit}" if pd.notna(pred_val) else "N/A",
                "Forecasted Rule Zone": pred_z,
                "Projected Delta (Δ)": delta_str,
                "Projected Trend": trend_str
            })
            
        st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True)
    elif is_warmup:
        min_meta_d = pd.to_datetime(f_meta["timestamp"]).dt.date.min() if not f_meta.empty else "Day 8"
        st.markdown(f"#### 📋 Current Observed vs ML Forecasted Next-Day Telemetry Matrix (Current Date: `{curr_date_str}`)")
        st.info(f"⏳ ML multi-output forecasting is in historical warmup (requires 7 days of historical lag data). Full $t+1$ predictions across all 16 channels activate on Day 8 ({min_meta_d}).")

    # 6. Live Rolling Strip-Chart & Next-Day Forecast Trajectory
    target_lbl = f" ➔ Forecast: {next_ts_str}" if next_ts_str else ""
    st.markdown(f"#### 📉 Live Rolling Strip-Chart & ML Forecast Trajectory (Past 30 Days Telemetry{target_lbl})")
    
    start_window_idx = max(0, curr_idx - 30)
    window_data = m_data.iloc[start_window_idx : curr_idx + 1]
    
    fig_strip = go.Figure()
    colors = {"P1-H": "#38bdf8", "P2-H": "#f59e0b", "P2-V": "#10b981", "P3-A": "#ec4899", "P3-H": "#8b5cf6"}
    
    for ch, col in colors.items():
        if ch in window_data.columns:
            fig_strip.add_trace(go.Scatter(
                x=window_data["time stamp"], y=window_data[ch],
                mode="lines+markers", name=f"{ch} (Observed)",
                line=dict(color=col, width=2), marker=dict(size=4)
            ))
            # If next-day forecast exists, plot dashed projection line to target
            if sample_preds and next_ts_str:
                pred_k = f"pred_{ch}" if f"pred_{ch}" in sample_preds else ch
                if pred_k in sample_preds:
                    pred_v = sample_preds[pred_k]
                    last_actual = window_data[ch].iloc[-1]
                    fig_strip.add_trace(go.Scatter(
                        x=[window_data["time stamp"].iloc[-1], next_ts_str],
                        y=[last_actual, pred_v],
                        mode="lines+markers",
                        line=dict(color=col, width=2, dash="dot"),
                        marker=dict(symbol="star", size=9, color=col),
                        name=f"{ch} (Forecast: {pred_v:.2f})",
                        showlegend=False
                    ))
            
    fig_strip.add_hline(y=lim_b, line_dash="dash", line_color="#38bdf8", annotation_text=f"Zone A/B Limit ({lim_b} mm/s)")
    fig_strip.add_hline(y=lim_c, line_dash="dash", line_color="#ef4444", annotation_text=f"Zone B/C Limit ({lim_c} mm/s)")
    
    fig_strip.update_layout(template="plotly_dark", height=320, margin=dict(t=20, b=20, l=20, r=20), xaxis_title="Timeline", yaxis_title="Velocity RMS (mm/s)", hovermode="x unified")
    st.plotly_chart(fig_strip, use_container_width=True)

    # 7. Unseen Test Data Model Comparison Benchmarks (Expander)
    with st.expander("🔬 Unseen Test Data Model Comparison Benchmarks (Random Forest vs Baselines)", expanded=False):
        st.caption("Evaluated on 3,962 chronologically held-out test samples across all 20 machines. Zero lookahead leakage.")
        if eval_report and "models_evaluated" in eval_report:
            m_eval = eval_report["models_evaluated"]
            bench_df = pd.DataFrame([
                {
                    "Model": "1. Persistence Baseline (y_hat = y_t)",
                    "Overall MAE (mm/s)": m_eval["persistence_baseline"]["overall_mae"],
                    "Overall RMSE (mm/s)": m_eval["persistence_baseline"]["overall_rmse"],
                    "R² Score": m_eval["persistence_baseline"]["overall_r2"],
                    "Error Reduction vs Persistence": "Baseline (0.0%)"
                },
                {
                    "Model": "2. Ridge Linear Regression",
                    "Overall MAE (mm/s)": m_eval["ridge_regression"]["overall_mae"],
                    "Overall RMSE (mm/s)": m_eval["ridge_regression"]["overall_rmse"],
                    "R² Score": m_eval["ridge_regression"]["overall_r2"],
                    "Error Reduction vs Persistence": f"{(1 - m_eval['ridge_regression']['overall_mae'] / m_eval['persistence_baseline']['overall_mae'])*100:.1f}%"
                },
                {
                    "Model": "3. Random Forest Regressor (Multi-Output)",
                    "Overall MAE (mm/s)": m_eval["random_forest"]["overall_mae"],
                    "Overall RMSE (mm/s)": m_eval["random_forest"]["overall_rmse"],
                    "R² Score": m_eval["random_forest"]["overall_r2"],
                    "Error Reduction vs Persistence": f"{(1 - m_eval['random_forest']['overall_mae'] / m_eval['persistence_baseline']['overall_mae'])*100:.1f}%"
                }
            ])
            st.dataframe(bench_df, use_container_width=True)

    # Automatic Continuous Live Stream Loop
    if st.session_state.get("is_streaming", False):
        time.sleep(stream_delay)
        st.session_state.stream_idx = (st.session_state.stream_idx + 1) % len(m_data)
        st.rerun()


# =============================================================
# VIEW 2: DATE-TO-DATE REPORT, TRENDS & FREQUENCY ANALYSIS
# =============================================================
elif selected_view == "📅 Date-to-Date Report, Trends & Frequency Analysis":
    st.markdown("### 📅 Date-to-Date Health Report, Graph Trends & Frequency Spectrum Analysis")
    st.caption(
        "Inspect any custom date window evaluated against ISO 10816-7 / Europump 2013 Table 1 category and power limits, "
        "multi-channel vibration and temperature trends, and high-resolution FFT order spectrum."
    )

    if mach_cat and mach_pwr is not None:
        limits = cfg.get_standards_limits(mach_cat, mach_pwr)
        lim_b = limits["zones"]["B"]
        lim_c = limits["zones"]["C"]
        al_lim = limits["alarm_limit"]
        tr_lim = limits["trip_limit"]
    else:
        lim_b, lim_c, al_lim, tr_lim = 4.0, 6.6, 5.0, 8.25

    # 1. Technical Specifications & Applicable ISO Limits Banner
    spec_col1, spec_col2 = st.columns([1.5, 2.5])
    with spec_col1:
        st.markdown(f"""
        <div class="kpi-metric-box" style="text-align:left; padding:14px;">
            <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">Monitored Asset & Category</div>
            <div style="font-size:1.15rem; font-weight:700; color:#ffffff; margin:4px 0;">{sel_machine} — {mach_name}</div>
            <div style="font-size:0.83rem; color:#cbd5e1; line-height:1.6;">
                • <strong>Category:</strong> <code>{mach_cat or 'INCOMPLETE'}</code><br>
                • <strong>Nominal Power:</strong> <code>{mach_pwr or 'N/A'} kW</code><br>
                • <strong>Rated Speed:</strong> <code>{mach_rpm} RPM</code> (1X = {mach_hz:.1f} Hz)<br>
                • <strong>Impeller Vanes:</strong> <code>{mach_cfg.get('impeller_vanes', 5)} vanes</code> (VPF = {mach_cfg.get('impeller_vanes', 5) * mach_hz:.1f} Hz)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with spec_col2:
        if mach_cat and mach_pwr is not None:
            st.markdown(f"""
            <div class="kpi-metric-box" style="text-align:left; padding:14px;">
                <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">Applicable ISO 10816-7 / Europump 2013 Table 1 Reference Limits</div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; margin-top:8px;">
                    <div style="background:#1e293b; border-radius:6px; padding:8px; text-align:center;">
                        <div style="color:#10b981; font-weight:700; font-size:1.1rem;">≤ {lim_b * 0.65:.1f}</div>
                        <div style="font-size:0.70rem; color:#94a3b8;">ZONE A (NEW)</div>
                    </div>
                    <div style="background:#1e293b; border-radius:6px; padding:8px; text-align:center;">
                        <div style="color:#38bdf8; font-weight:700; font-size:1.1rem;">≤ {lim_b:.1f}</div>
                        <div style="font-size:0.70rem; color:#94a3b8;">ZONE B (ACCEPTABLE)</div>
                    </div>
                    <div style="background:#1e293b; border-radius:6px; padding:8px; text-align:center;">
                        <div style="color:#f59e0b; font-weight:700; font-size:1.1rem;">≤ {lim_c:.1f}</div>
                        <div style="font-size:0.70rem; color:#94a3b8;">ZONE C (UNSATISFACTORY)</div>
                    </div>
                    <div style="background:#1e293b; border-radius:6px; padding:8px; text-align:center;">
                        <div style="color:#ef4444; font-weight:700; font-size:1.1rem;">> {lim_c:.1f}</div>
                        <div style="font-size:0.70rem; color:#94a3b8;">ZONE D (TRIP)</div>
                    </div>
                </div>
                <div style="font-size:0.78rem; color:#94a3b8; margin-top:8px;">
                    Alarm Threshold: <strong>{al_lim:.1f} mm/s</strong> (1.25×B) &bull; Trip Threshold: <strong>{tr_lim:.1f} mm/s</strong> (1.25×C)
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Machine configuration is incomplete. Standard ISO limits cannot be evaluated per Europump guidelines.")

    # 2. Date-to-Date Selection Toolbar
    all_dates = m_data["time stamp"].dt.date.tolist()
    min_d = min(all_dates)
    max_d = max(all_dates)
    
    # Defaults
    mach_faults = df_faults[df_faults["machine_id"] == sel_machine]
    if not mach_faults.empty:
        f_s_def = max(min_d, pd.to_datetime(mach_faults.iloc[0]["start_date"]).date() - timedelta(days=7))
        f_e_def = min(max_d, pd.to_datetime(mach_faults.iloc[0]["end_date"]).date() + timedelta(days=7))
    else:
        f_s_def = max(min_d, max_d - timedelta(days=60))
        f_e_def = max_d
        
    if "dt_from" in st.session_state and "dt_to" in st.session_state:
        f_s_def = st.session_state["dt_from"]
        f_e_def = st.session_state["dt_to"]

    st.markdown("---")
    st.markdown("#### 📅 Select Custom Date Range (From Date ➔ To Date)")
    
    d_col1, d_col2 = st.columns([1.5, 2.5])
    with d_col1:
        sel_range = st.date_input(
            "Date Range Filter:",
            value=(f_s_def, f_e_def),
            min_value=min_d,
            max_value=max_d,
            key="range_input_widget"
        )
        if isinstance(sel_range, (list, tuple)) and len(sel_range) == 2:
            from_date, to_date = sel_range[0], sel_range[1]
        elif isinstance(sel_range, (list, tuple)) and len(sel_range) == 1:
            from_date, to_date = sel_range[0], sel_range[0]
        else:
            from_date, to_date = min_d, max_d
            
    with d_col2:
        if not mach_faults.empty:
            st.write("**Quick Presets for Documented Benchmark Events:**")
            p_cols = st.columns(min(3, len(mach_faults)))
            for p_idx, (_, f_r) in enumerate(mach_faults.head(3).iterrows()):
                with p_cols[p_idx]:
                    if st.button(f"📌 {f_r['fault_scenario'].title()}", key=f"qk_{p_idx}", use_container_width=True):
                        st.session_state["dt_from"] = pd.to_datetime(f_r["start_date"]).date()
                        st.session_state["dt_to"] = pd.to_datetime(f_r["end_date"]).date()
                        st.rerun()
        else:
            st.caption(f"Telemetry spans from `{min_d}` to `{max_d}` ({len(m_data)} total daily records).")

    # 3. Filter Range Data
    range_df = m_data[(m_data["time stamp"].dt.date >= from_date) & (m_data["time stamp"].dt.date <= to_date)].copy()
    
    if range_df.empty:
        st.warning(f"No records found between {from_date} and {to_date}.")
    else:
        vib_cols = [c for c in ['P1-V', 'P1-H', 'P1-A', 'P2-V', 'P2-H', 'P2-A', 'P3-V', 'P3-H', 'P3-A', 'P4-V', 'P4-H', 'P4-A'] if c in range_df.columns]
        temp_cols = [c for c in ['P1-T', 'P2-T', 'P3-T', 'P4-T'] if c in range_df.columns]
        
        # Calculate Peak Vibration and Peak Date
        peak_val = 0.0
        peak_ch = "N/A"
        peak_dt = str(from_date)
        
        for _, r in range_df.iterrows():
            for ch in vib_cols:
                v = r.get(ch, 0.0)
                if pd.notna(v) and v > peak_val:
                    peak_val = v
                    peak_ch = ch
                    peak_dt = str(r["time stamp"])[:10]
                    
        # Calculate ISO zone distribution across date range
        days_A, days_B, days_C, days_D = 0, 0, 0, 0
        anom_days = 0
        for _, r in range_df.iterrows():
            row_max = max([r.get(c, 0.0) for c in vib_cols if pd.notna(r.get(c))], default=0.0)
            if row_max <= lim_b * 0.65:
                days_A += 1
            elif row_max <= lim_b:
                days_B += 1
            elif row_max <= lim_c:
                days_C += 1
            else:
                days_D += 1
            if bool(r.get("is_anomaly", 0)):
                anom_days += 1
                
        tot_d = len(range_df)
        dom_zone = "Zone A" if days_A >= max(days_B, days_C, days_D) else (
            "Zone B" if days_B >= max(days_A, days_C, days_D) else (
                "Zone C" if days_C >= max(days_A, days_B, days_D) else "Zone D"
            )
        )
        
        # Date-to-Date Health Report Card
        st.markdown(f"#### 📊 Date-to-Date Condition Summary (`{from_date}` to `{to_date}`)")
        
        rep_c1, rep_c2, rep_c3, rep_c4 = st.columns(4)
        with rep_c1:
            st.markdown(f"""
            <div class="kpi-metric-box">
                <div class="kpi-metric-val">{tot_d} Days</div>
                <div class="kpi-metric-lbl">Duration Monitored</div>
            </div>
            """, unsafe_allow_html=True)
            
        with rep_c2:
            p_color = "#10b981" if peak_val <= lim_b else ("#f59e0b" if peak_val <= lim_c else "#ef4444")
            st.markdown(f"""
            <div class="kpi-metric-box" style="border-color:{p_color};">
                <div class="kpi-metric-val" style="color:{p_color};">{peak_val:.2f} mm/s</div>
                <div class="kpi-metric-lbl">Peak Vibration ({peak_ch} on {peak_dt})</div>
            </div>
            """, unsafe_allow_html=True)
            
        with rep_c3:
            z_color = "#10b981" if "Zone A" in dom_zone else ("#38bdf8" if "Zone B" in dom_zone else ("#f59e0b" if "Zone C" in dom_zone else "#ef4444"))
            st.markdown(f"""
            <div class="kpi-metric-box" style="border-color:{z_color};">
                <div class="kpi-metric-val" style="color:{z_color};">{dom_zone}</div>
                <div class="kpi-metric-lbl">Dominant ISO Severity</div>
            </div>
            """, unsafe_allow_html=True)
            
        with rep_c4:
            a_color = "#ef4444" if anom_days > 0 else "#10b981"
            st.markdown(f"""
            <div class="kpi-metric-box" style="border-color:{a_color};">
                <div class="kpi-metric-val" style="color:{a_color};">{anom_days} Days</div>
                <div class="kpi-metric-lbl">Abnormal / Excursion Days</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Zone distribution bar
        pct_A = days_A / tot_d * 100
        pct_B = days_B / tot_d * 100
        pct_C = days_C / tot_d * 100
        pct_D = days_D / tot_d * 100
        
        st.markdown(f"""
        <div style="background:#111827; border:1px solid #374151; border-radius:8px; padding:12px; margin:12px 0;">
            <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; margin-bottom:8px;">
                ISO 10816-7 Operating Zone Distribution Across Selected Range
            </div>
            <div style="display:flex; height:24px; border-radius:4px; overflow:hidden; font-size:0.75rem; font-weight:700; text-align:center; line-height:24px;">
                <div style="width:{pct_A}%; background:#10b981; color:#064e3b;" title="Zone A: {days_A} days">A: {days_A}d ({pct_A:.0f}%)</div>
                <div style="width:{pct_B}%; background:#38bdf8; color:#0c4a6e;" title="Zone B: {days_B} days">B: {days_B}d ({pct_B:.0f}%)</div>
                <div style="width:{pct_C}%; background:#f59e0b; color:#78350f;" title="Zone C: {days_C} days">C: {days_C}d ({pct_C:.0f}%)</div>
                <div style="width:{pct_D}%; background:#ef4444; color:#450a0a;" title="Zone D: {days_D} days">D: {days_D}d ({pct_D:.0f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Download Report Center
        d_btn1, d_btn2 = st.columns(2)
        with d_btn1:
            csv_export = range_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download Date Range Telemetry CSV ({tot_d} Rows)",
                data=csv_export,
                file_name=f"{sel_machine}_telemetry_{from_date}_to_{to_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with d_btn2:
            pdf_out_path = os.path.join(PROJECT_ROOT, "outputs", "reports", f"{sel_machine}_{from_date}_to_{to_date}_report.pdf")
            if st.button("📄 Generate Certified PDF Condition Report", use_container_width=True):
                events = repo.get_events(machine_id=sel_machine, limit=50)
                generate_pdf_report(sel_machine, mach_cfg, events, pdf_out_path)
                st.success("PDF Report generated successfully!")
                with open(pdf_out_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Generated PDF Report",
                        data=f.read(),
                        file_name=f"{sel_machine}_report_{from_date}_to_{to_date}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

        # 4. Date-to-Date Multi-Point Graph Trend
        st.markdown("---")
        st.markdown("#### 📈 Multi-Point Vibration Velocity Graph Trend (mm/s RMS)")
        st.caption(f"Continuous telemetry trend across `{from_date}` to `{to_date}` with Category {mach_cat} ({mach_pwr} kW) Zone B ({lim_b:.1f} mm/s) and Zone C ({lim_c:.1f} mm/s) limit lines.")
        
        pt_col1, pt_col2 = st.columns([2, 1])
        with pt_col1:
            sel_pts = st.multiselect("Measurement Points to Plot:", ["P1", "P2", "P3", "P4"], default=["P1", "P2", "P3"], key="rng_pts")
        with pt_col2:
            sel_dirs = st.multiselect("Directions to Plot:", ["H (Horizontal)", "V (Vertical)", "A (Axial)"], default=["H (Horizontal)", "V (Vertical)"], key="rng_dirs")
            
        dir_map = {"H (Horizontal)": "H", "V (Vertical)": "V", "A (Axial)": "A"}
        active_dirs = [dir_map[d] for d in sel_dirs]
        
        fig_trend = go.Figure()
        palette = {
            "P1-H": "#38bdf8", "P1-V": "#0284c7", "P1-A": "#7dd3fc",
            "P2-H": "#f59e0b", "P2-V": "#10b981", "P2-A": "#d97706",
            "P3-H": "#8b5cf6", "P3-V": "#a78bfa", "P3-A": "#ec4899",
            "P4-H": "#64748b", "P4-V": "#94a3b8", "P4-A": "#cbd5e1"
        }
        
        for pt in sel_pts:
            for d in active_dirs:
                ch_name = f"{pt}-{d}"
                if ch_name in range_df.columns:
                    fig_trend.add_trace(go.Scatter(
                        x=range_df["time stamp"],
                        y=range_df[ch_name],
                        mode="lines+markers",
                        name=ch_name,
                        line=dict(color=palette.get(ch_name, "#ffffff"), width=2),
                        marker=dict(size=4)
                    ))
                    
        fig_trend.add_hline(y=lim_b, line_dash="dash", line_color="#38bdf8", annotation_text=f"Zone B Limit ({lim_b:.1f} mm/s)")
        fig_trend.add_hline(y=lim_c, line_dash="dash", line_color="#ef4444", annotation_text=f"Zone C Limit ({lim_c:.1f} mm/s)")
        fig_trend.add_hline(y=al_lim, line_dash="dot", line_color="#f59e0b", annotation_text=f"Alarm Limit ({al_lim:.1f} mm/s)")
        
        fig_trend.update_layout(
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Vibration Velocity (mm/s RMS)",
            hovermode="x unified",
            height=380,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Temperature Trend Chart
        st.markdown("#### 🌡️ Bearing Housing Temperature Trends (°C)")
        fig_temp = go.Figure()
        temp_palette = {"P1-T": "#38bdf8", "P2-T": "#f59e0b", "P3-T": "#ec4899", "P4-T": "#10b981"}
        for pt in sel_pts:
            t_ch = f"{pt}-T"
            if t_ch in range_df.columns:
                fig_temp.add_trace(go.Scatter(
                    x=range_df["time stamp"],
                    y=range_df[t_ch],
                    mode="lines",
                    name=f"{pt} Housing Temp",
                    line=dict(color=temp_palette.get(t_ch, "#ffffff"), width=1.5)
                ))
        fig_temp.add_hline(y=70.0, line_dash="dot", line_color="#f59e0b", annotation_text="Warning (70°C)")
        fig_temp.add_hline(y=85.0, line_dash="dash", line_color="#ef4444", annotation_text="Trip (85°C)")
        fig_temp.update_layout(
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Housing Temperature (°C)",
            hovermode="x unified",
            height=280,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        # 5. Frequency-based fault diagnosis: third project use case
        st.markdown("---")
        st.markdown("#### 🔬 Use Case 3 — Frequency-Based Fault Diagnosis")
        st.info(
            "The daily telemetry contains overall sensor readings, not raw high-frequency waveforms. "
            "This module therefore runs an explicitly labelled synthetic waveform demonstration, "
            "then applies FFT feature extraction and transparent diagnostic rules. It does not claim "
            "that a generated waveform was measured from the selected machine."
        )

        freq_mode = st.radio(
            "Frequency analysis source:",
            ["Use synthetic event schedule for selected machine/date", "Controlled synthetic demonstration"],
            horizontal=True,
            key="frequency_analysis_source_mode",
        )

        available_spec_dates = sorted(range_df["time stamp"].dt.date.dropna().unique().tolist())
        if not available_spec_dates:
            available_spec_dates = sorted(m_data["time stamp"].dt.date.dropna().unique().tolist())
        default_spec_date = available_spec_dates[-1]
        spec_date = st.selectbox(
            "Date to analyse", available_spec_dates,
            index=len(available_spec_dates) - 1,
            key="frequency_analysis_date",
        )

        day_rows = m_data[m_data["time stamp"].dt.date == spec_date]
        if day_rows.empty:
            st.warning("No daily telemetry row exists for this machine/date.")
            daily_spec_row = m_data.iloc[-1]
        else:
            daily_spec_row = day_rows.iloc[-1]

        temp_warning = float(mach_cfg.get("temperature_limits", {}).get("warning_deg_c", 65.0))
        temp_alarm = float(mach_cfg.get("temperature_limits", {}).get("alarm_deg_c", 80.0))

        selected_scenario = "healthy"
        event_note = ""
        diagnosis_allowed = True
        if freq_mode == "Use synthetic event schedule for selected machine/date":
            matching_events = df_faults[
                (df_faults["machine_id"].astype(str) == str(sel_machine))
                & (pd.to_datetime(df_faults["start_date"]).dt.date <= spec_date)
                & (pd.to_datetime(df_faults["end_date"]).dt.date >= spec_date)
            ] if not df_faults.empty else pd.DataFrame()
            if matching_events.empty:
                selected_scenario = "healthy"
                event_note = "No synthetic fault event is recorded for this machine/date; using a synthetic healthy reference waveform."
            else:
                event_name = str(matching_events.iloc[0]["fault_scenario"])
                mapped = map_event_to_target_scenario(event_name)
                if mapped is None:
                    diagnosis_allowed = False
                    selected_scenario = "healthy"
                    event_note = (
                        f"The event schedule labels this date as '{event_name}', which is outside the three target conditions. "
                        "No target-fault diagnosis will be claimed for this event. Switch to controlled demonstration to test the three target patterns."
                    )
                else:
                    selected_scenario = mapped
                    event_note = f"Synthetic event schedule maps '{event_name}' to '{TARGET_SCENARIOS[mapped]}'."
        else:
            demo_options = {
                "Healthy reference": "healthy",
                "Rotor imbalance": "rotor_imbalance",
                "Shaft misalignment": "shaft_misalignment",
                "High-frequency vibration + high temperature": "high_frequency_high_temperature",
            }
            demo_label = st.selectbox(
                "Synthetic test case (for validating the diagnostic logic)",
                list(demo_options.keys()),
                key="frequency_demo_scenario",
            )
            selected_scenario = demo_options[demo_label]
            event_note = "Controlled synthetic test case selected. This is a simulated example, not measured machine data."

        st.caption(event_note)
        st.caption(
            f"Machine: {sel_machine} | Date: {spec_date} | Configured speed: {mach_rpm} RPM "
            f"({mach_rpm / 60.0:.2f} Hz at 1×)."
        )

        freq_col1, freq_col2, freq_col3 = st.columns(3)
        with freq_col1:
            selected_location = st.selectbox(
                "Sensor location", ["P1", "P2", "P3", "P4"], index=1,
                key="frequency_sensor_location",
            )
        with freq_col2:
            selected_direction = st.selectbox(
                "Vibration direction", ["H", "V", "A"], index=0,
                key="frequency_sensor_direction",
            )
        with freq_col3:
            st.metric("Temperature warning reference", f"{temp_warning:.1f} °C")

        selected_temp_col = f"{selected_location}-T"
        selected_temp_actual = pd.to_numeric(pd.Series([daily_spec_row.get(selected_temp_col, np.nan)]), errors="coerce").iloc[0]
        if pd.isna(selected_temp_actual):
            selected_temp_actual = float(daily_spec_row[[c for c in ["P1-T", "P2-T", "P3-T", "P4-T"] if c in daily_spec_row.index]].mean())
        selected_temp_for_diagnosis = float(selected_temp_actual)
        temperature_provenance = "daily synthetic telemetry"
        if selected_scenario == "high_frequency_high_temperature":
            # The third fault condition is a controlled simulation: inject a thermal rise at the selected location.
            selected_temp_for_diagnosis = max(selected_temp_for_diagnosis, temp_warning + 8.0)
            temperature_provenance = "simulated thermal rise added to the daily reading"

        seed_text = f"{sel_machine}|{spec_date}|{selected_location}|{selected_direction}|{selected_scenario}"
        waveform_seed = sum((i + 1) * ord(ch) for i, ch in enumerate(seed_text)) % (2**32 - 1)
        selected_result = analyse_waveform(
            scenario=selected_scenario,
            rpm=float(mach_rpm),
            location=selected_location,
            direction=selected_direction,
            temperature_c=selected_temp_for_diagnosis,
            temperature_warning_c=temp_warning,
            sample_rate_hz=4096,
            duration_sec=2.0,
            seed=int(waveform_seed),
        )
        selected_features = selected_result["features"]
        selected_diagnosis = selected_result["diagnosis"]

        if not diagnosis_allowed:
            st.warning("Target-condition diagnosis withheld because the scheduled synthetic event is outside the three target classes.")
        else:
            result_cols = st.columns([1.2, 2.0])
            with result_cols[0]:
                st.markdown("##### Diagnostic result")
                st.markdown(f"**{selected_diagnosis['condition']}**")
                st.caption(selected_diagnosis["status"])
                st.caption(selected_diagnosis["confidence"])
            with result_cols[1]:
                st.markdown("##### Why this result was returned")
                for evidence_item in selected_diagnosis["evidence"]:
                    st.write(f"• {evidence_item}")
                st.caption(f"Temperature used: {selected_temp_for_diagnosis:.1f} °C ({temperature_provenance}).")

        st.markdown("##### FFT spectrum for the selected sensor")
        fft_fig = go.Figure()
        fft_fig.add_trace(go.Scatter(
            x=selected_result["frequencies_hz"],
            y=selected_result["amplitudes_rms_mm_s"],
            mode="lines",
            name="Synthetic velocity RMS spectrum",
            line=dict(width=1.4),
        ))
        f1 = float(mach_rpm) / 60.0
        for order, color in [(1, "#10b981"), (2, "#f59e0b"), (3, "#ef4444")]:
            fft_fig.add_vline(
                x=order * f1, line_dash="dash", line_color=color,
                annotation_text=f"{order}× ({order*f1:.1f} Hz)",
                annotation_position="top left",
            )
        fft_fig.update_layout(
            template="plotly_dark", height=400,
            xaxis_title="Frequency (Hz)", yaxis_title="Velocity amplitude (mm/s RMS)",
            margin=dict(t=45, b=25, l=25, r=25),
        )
        st.plotly_chart(fft_fig, use_container_width=True)

        metric_cols = st.columns(5)
        metric_cols[0].metric("1× amplitude", f"{selected_features['amp_1x_mm_s']:.2f} mm/s")
        metric_cols[1].metric("2× amplitude", f"{selected_features['amp_2x_mm_s']:.2f} mm/s")
        metric_cols[2].metric("3× amplitude", f"{selected_features['amp_3x_mm_s']:.2f} mm/s")
        metric_cols[3].metric("High-frequency RMS", f"{selected_features['high_freq_rms_mm_s']:.2f} mm/s")
        metric_cols[4].metric("Temperature used", f"{selected_temp_for_diagnosis:.1f} °C")

        st.markdown("##### All sensor channels for this machine/date")
        st.caption(
            "Each row is a synthetic waveform generated for one location/direction using the selected scenario. "
            "The daily vibration and temperature values come from the selected date; for the high-frequency + high-temperature "
            "demo, a simulated thermal rise is added at the selected location."
        )
        channel_rows = []
        for loc in ["P1", "P2", "P3", "P4"]:
            for direc in ["H", "V", "A"]:
                actual_temp = pd.to_numeric(pd.Series([daily_spec_row.get(f"{loc}-T", np.nan)]), errors="coerce").iloc[0]
                if pd.isna(actual_temp):
                    actual_temp = float(selected_temp_actual)
                temp_used = float(actual_temp)
                temp_source = "daily telemetry"
                if selected_scenario == "high_frequency_high_temperature" and loc == selected_location:
                    temp_used = max(temp_used, temp_warning + 8.0)
                    temp_source = "simulated rise"
                ch_seed_text = f"{sel_machine}|{spec_date}|{loc}|{direc}|{selected_scenario}"
                ch_seed = sum((i + 1) * ord(ch) for i, ch in enumerate(ch_seed_text)) % (2**32 - 1)
                ch_result = analyse_waveform(
                    scenario=selected_scenario,
                    rpm=float(mach_rpm),
                    location=loc,
                    direction=direc,
                    temperature_c=temp_used,
                    temperature_warning_c=temp_warning,
                    sample_rate_hz=4096,
                    duration_sec=2.0,
                    seed=int(ch_seed),
                )
                ch_feat = ch_result["features"]
                ch_diag = ch_result["diagnosis"]
                channel_rows.append({
                    "Location": loc,
                    "Direction": direc,
                    "Daily vibration (mm/s)": daily_spec_row.get(f"{loc}-{direc}", np.nan),
                    "Daily temperature (°C)": actual_temp,
                    "Temperature used (°C)": temp_used,
                    "Temperature source": temp_source,
                    "1× (mm/s)": ch_feat["amp_1x_mm_s"],
                    "2× (mm/s)": ch_feat["amp_2x_mm_s"],
                    "3× (mm/s)": ch_feat["amp_3x_mm_s"],
                    "High-frequency RMS": ch_feat["high_freq_rms_mm_s"],
                    "Diagnosis": ch_diag["condition"] if diagnosis_allowed else "Outside target scope",
                    "Provenance": "SYNTHETIC_SIMULATION",
                })
        st.dataframe(pd.DataFrame(channel_rows).round(3), use_container_width=True, hide_index=True)
        st.warning(
            "Research prototype only: 1×/2×/3× and high-frequency rules are diagnostic heuristics, not calibrated probabilities. "
            "Use measured waveforms, verified RPM, sensor metadata and labelled fault examples before claiming real-machine diagnosis."
        )

        # 6. Collapsible Maintenance Work Order & Audit Trail (Operator Tools)
        st.markdown("---")
        with st.expander("🛠️ Maintenance Work Order Management & Audit Trail (Operator Tools)", expanded=False):
            st.caption("Review pipeline-diagnosed events from SQLite database, issue maintenance work orders, sign off, and inspect audit logs.")
            status_filter = st.selectbox("Filter Events by Status:", ["ALL", "OPEN", "ACKNOWLEDGED", "RESOLVED"], key="op_stat")
            filter_val = None if status_filter == "ALL" else status_filter
            events = repo.get_events(machine_id=sel_machine, status=filter_val, limit=50)
            
            if not events:
                st.info(f"No matching maintenance events found for machine {sel_machine}.")
            else:
                st.markdown(f"Displaying **{len(events)}** events for asset `{sel_machine}`:")
                event_summary_rows = []
                for e in events:
                    top_f = e["candidate_faults"][0]["fault_name"] if e["candidate_faults"] else "Unclassified"
                    event_summary_rows.append({
                        "Event ID": e["event_id"],
                        "Date": e["timestamp"][:10],
                        "ISO Zone": e["severity_zone"],
                        "Peak Vib (mm/s)": e["max_vibration"],
                        "Primary Fault Hypothesis": top_f,
                        "Workflow Status": e["status"],
                        "Acknowledged By": e.get("acknowledged_by", "Pending")
                    })
                st.dataframe(pd.DataFrame(event_summary_rows), use_container_width=True)
                
                event_ids = [e["event_id"] for e in events]
                sel_ev_id = st.selectbox("Select Event ID to Review:", event_ids, key="op_ev_id")
                
                tab_rev, tab_ack, tab_res, tab_audit = st.tabs(["1. Review & Draft", "2. Acknowledge", "3. Complete Maintenance", "4. Audit Trail"])
                
                with tab_rev:
                    draft = workflow.review_event_and_draft_task(sel_ev_id)
                    st.write(f"**Automated Summary:** {draft['summary']}")
                    st.write(f"**Uncertainty Assessment:** {draft['uncertainty_assessment']}")
                    st.warning(f"**Drafted Work Order:** {draft['drafted_inspection_task']}")
                    
                with tab_ack:
                    ack_user = st.text_input("Operator Name:", value="Reliability_Lead", key="op_ack_u")
                    ack_notes = st.text_area("Acknowledgement Notes:", value="Verified abnormal readings; scheduled physical verification.", key="op_ack_n")
                    if st.button("Acknowledge Event", key="op_btn_ack"):
                        repo.acknowledge_event(sel_ev_id, ack_user, ack_notes)
                        st.success(f"Event #{sel_ev_id} acknowledged by {ack_user}.")
                        st.rerun()
                        
                with tab_res:
                    res_user = st.text_input("Maintenance Supervisor:", value="Plant_Engineer", key="op_res_u")
                    action_done = st.text_area("Maintenance Action Completed:", value="Replaced worn coupling insert; dynamic trim balanced to ISO G2.5.", key="op_res_a")
                    post_obs = st.text_area("Post-Maintenance Observation:", value="Vibration dropped to Zone A (2.1 mm/s RMS).", key="op_res_o")
                    if st.button("Complete Maintenance & Resolve", key="op_btn_res"):
                        repo.complete_maintenance(sel_ev_id, action_done, post_obs, performed_by=res_user)
                        st.success(f"Event #{sel_ev_id} marked RESOLVED. Audit trail committed.")
                        st.rerun()
                        
                with tab_audit:
                    audit_records = repo.get_audit_trail(sel_ev_id)
                    st.dataframe(pd.DataFrame(audit_records), use_container_width=True)
