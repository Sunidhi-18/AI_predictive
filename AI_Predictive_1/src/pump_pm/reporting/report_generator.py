"""
report_generator.py
--------------------
Generates condition monitoring summaries in CSV and PDF formats.
Integrates PyMuPDF for local, self-contained PDF generation with
mandatory academic prototype notices and synthetic data disclosures.
"""

import os
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime


def generate_csv_summary(events: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
    """
    Exports maintenance events list into a structured CSV string or file.
    """
    rows = []
    for ev in events:
        c_faults = ev.get("candidate_faults", [])
        top_fault = c_faults[0]["fault_name"] if c_faults else "N/A"
        top_conf = c_faults[0]["confidence_score"] if c_faults else "N/A"

        rows.append({
            "Event_ID": ev.get("event_id"),
            "Machine_ID": ev.get("machine_id"),
            "Timestamp": ev.get("timestamp"),
            "Severity_Zone": ev.get("severity_zone"),
            "Alarm_Status": ev.get("alarm_status"),
            "Max_Vibration_mm_s": ev.get("max_vibration"),
            "Dominant_Location": ev.get("dominant_location"),
            "Top_Candidate_Fault": top_fault,
            "Diagnostic_Confidence": top_conf,
            "Anomaly_Score": ev.get("anomaly_score"),
            "Workflow_Status": ev.get("status"),
            "Acknowledged_By": ev.get("acknowledged_by"),
            "Action_Taken": ev.get("action_taken"),
            "Provenance": "ACADEMIC_PROTOTYPE_SIMULATION"
        })

    df = pd.DataFrame(rows)
    csv_str = df.to_csv(index=False)
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
    return csv_str


def generate_pdf_report(
    machine_id: str,
    machine_meta: Dict[str, Any],
    recent_events: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    Generates an industrial condition monitoring PDF report using PyMuPDF.
    Includes technical metadata, ISO 10816-7 zone assessments, diagnostic hypotheses,
    and mandatory academic prototype disclaimers.
    """
    import pymupdf

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 (points)

    # Color palette
    c_navy = (0.05, 0.15, 0.3)
    c_dark = (0.1, 0.1, 0.1)
    c_red = (0.75, 0.1, 0.1)
    c_gray = (0.4, 0.4, 0.4)
    c_bg_gray = (0.95, 0.95, 0.95)

    # Header Banner
    page.draw_rect(pymupdf.Rect(30, 30, 565, 80), color=None, fill=c_navy)
    page.insert_text(
        pymupdf.Point(45, 55),
        "PUMP & MOTOR CONDITION MONITORING REPORT",
        fontsize=14,
        color=(1, 1, 1),
        fontname="helv"
    )
    page.insert_text(
        pymupdf.Point(45, 70),
        "Intelligent Predictive Maintenance Framework — Smart Manufacturing Decision Support",
        fontsize=9,
        color=(0.85, 0.85, 0.85),
        fontname="helv"
    )

    # Academic Prototype Watermark / Notice
    page.draw_rect(pymupdf.Rect(30, 90, 565, 138), color=c_red, fill=(1.0, 0.94, 0.94), width=1)
    notice_text = (
        "IMPORTANT NOTICE: ACADEMIC ENGINEERING PROTOTYPE ONLY.\n"
        "This diagnostic report is generated from local simulations and sensor features for educational and "
        "decision-support research. It is NOT certified for physical plant protection or automated safety trips."
    )
    page.insert_textbox(pymupdf.Rect(40, 94, 555, 134), notice_text, fontsize=8, color=c_red, fontname="helv")

    # Section 1: Machine Technical Profile
    y = 155
    page.insert_text(pymupdf.Point(35, y), "1. MACHINE TECHNICAL PROFILE & APPLICABLE CRITERIA", fontsize=11, color=c_navy, fontname="helv")
    y += 15
    page.draw_line(pymupdf.Point(35, y), pymupdf.Point(565, y), color=c_gray, width=0.5)
    y += 15

    power = machine_meta.get("nominal_power_kw", "N/A")
    cat = machine_meta.get("category", "N/A")
    rpm = machine_meta.get("rated_speed_rpm", "N/A")
    name = machine_meta.get("name", "Industrial Pump Unit")

    profile_lines = [
        f"Machine ID: {machine_id}  |  Equipment Name: {name}",
        f"ISO 10816-7 Classification: {str(cat).replace('_', ' ').title()}  |  Nominal Power: {power} kW",
        f"Rated Speed: {rpm} RPM (Running Freq: {float(rpm)/60.0 if rpm != 'N/A' else 50.0:.1f} Hz)  |  Standard Limits: Europump 2013 Table 1",
        f"Report Generation Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    ]
    for line in profile_lines:
        page.insert_text(pymupdf.Point(40, y), line, fontsize=9, color=c_dark, fontname="helv")
        y += 14

    # Section 2: Recent Diagnostic Events
    y += 15
    page.insert_text(pymupdf.Point(35, y), "2. RECENT CONDITION ASSESSMENTS & DIAGNOSTIC EVENTS", fontsize=11, color=c_navy, fontname="helv")
    y += 15
    page.draw_line(pymupdf.Point(35, y), pymupdf.Point(565, y), color=c_gray, width=0.5)
    y += 15

    if not recent_events:
        page.insert_text(pymupdf.Point(40, y), "No open or high-severity alarm events recorded for this machine.", fontsize=9, color=c_dark, fontname="helv")
        y += 20
    else:
        for idx, ev in enumerate(recent_events[:4]):
            z = ev.get("severity_zone", "Zone A")
            v = ev.get("max_vibration", 0.0)
            status = ev.get("status", "OPEN")
            c_faults = ev.get("candidate_faults", [])
            top_fault = c_faults[0]["fault_name"] if c_faults else "Unknown"
            conf = c_faults[0]["confidence_score"] if c_faults else 0.0

            # Event box
            page.draw_rect(pymupdf.Rect(35, y, 565, y + 45), color=c_gray, fill=c_bg_gray, width=0.5)
            page.insert_text(
                pymupdf.Point(45, y + 15),
                f"Event #{ev.get('event_id')} — Date: {ev.get('timestamp')} | Status: {status} | Severity: {z} (Peak: {v:.2f} mm/s RMS)",
                fontsize=9,
                color=c_dark,
                fontname="helv"
            )
            page.insert_text(
                pymupdf.Point(45, y + 30),
                f"Candidate Fault: {top_fault} (Confidence Score: {conf:.2f})",
                fontsize=8,
                color=c_navy,
                fontname="helv"
            )
            y += 52

    # Section 3: Recommended Actions & Human Sign-off
    y += 15
    page.insert_text(pymupdf.Point(35, y), "3. RECOMMENDED MAINTENANCE ACTIONS & SIGN-OFF", fontsize=11, color=c_navy, fontname="helv")
    y += 15
    page.draw_line(pymupdf.Point(35, y), pymupdf.Point(565, y), color=c_gray, width=0.5)
    y += 15

    actions = [
        "1. Physical Verification: Verify transducer stud torque and confirm no loose accelerometer cables.",
        "2. Handheld Walkdown: Conduct spectral frequency survey around 1x RPM and coupling axial plane.",
        "3. Lubrication Inspection: Check oil reservoir level and verify grease interval compliance.",
        "4. Work Order Authorization: Operator must verify findings prior to opening physical mechanical casing."
    ]
    for act in actions:
        page.insert_text(pymupdf.Point(40, y), act, fontsize=9, color=c_dark, fontname="helv")
        y += 16

    # Footer
    page.draw_line(pymupdf.Point(35, 800), pymupdf.Point(565, 800), color=c_gray, width=0.5)
    page.insert_text(
        pymupdf.Point(35, 815),
        "Intelligent Predictive Maintenance Framework — Academic Research Prototype — Not for Physical Machinery Control",
        fontsize=8,
        color=c_gray,
        fontname="helv"
    )

    doc.save(output_path)
    doc.close()
    return output_path
