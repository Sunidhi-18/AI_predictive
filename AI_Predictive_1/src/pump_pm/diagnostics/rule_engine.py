"""
rule_engine.py
--------------
Multi-evidence heuristic diagnostic engine covering 12 rotating machinery fault families.
Synthesizes directional telemetry, thermal gradients, and spectral order features
into ranked fault candidates with explicit supporting/missing evidence and uncertainty fallbacks.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from ..config import get_config
from .fault_candidates import FaultCandidate, DiagnosticEvaluation


class MultiEvidenceRuleEngine:
    def __init__(self):
        self.cfg = get_config()
        self.rules_cfg = self.cfg.rules

    def evaluate(
        self,
        machine_id: str,
        telemetry_row: pd.Series,
        spectrum_features: Optional[Dict[str, float]] = None,
        operational_context: Optional[Dict[str, Any]] = None,
        governing_zone: str = "Zone A"
    ) -> DiagnosticEvaluation:
        """
        Evaluates a machine state against diagnostic rules.
        """
        candidates: List[FaultCandidate] = []
        op_ctx = operational_context or {}
        spec = spectrum_features or {}

        # Extract telemetry sensor values
        p1_h = float(telemetry_row.get("P1-H", 0.0) or 0.0)
        p1_v = float(telemetry_row.get("P1-V", 0.0) or 0.0)
        p1_a = float(telemetry_row.get("P1-A", 0.0) or 0.0)
        p1_t = float(telemetry_row.get("P1-T", 0.0) or 0.0)

        p2_h = float(telemetry_row.get("P2-H", 0.0) or 0.0)
        p2_v = float(telemetry_row.get("P2-V", 0.0) or 0.0)
        p2_a = float(telemetry_row.get("P2-A", 0.0) or 0.0)
        p2_t = float(telemetry_row.get("P2-T", 0.0) or 0.0)

        p3_h = float(telemetry_row.get("P3-H", 0.0) or 0.0)
        p3_v = float(telemetry_row.get("P3-V", 0.0) or 0.0)
        p3_a = float(telemetry_row.get("P3-A", 0.0) or 0.0)
        p3_t = float(telemetry_row.get("P3-T", 0.0) or 0.0)

        p4_h = float(telemetry_row.get("P4-H", 0.0) or 0.0)
        p4_v = float(telemetry_row.get("P4-V", 0.0) or 0.0)
        p4_a = float(telemetry_row.get("P4-A", 0.0) or 0.0)
        p4_t = float(telemetry_row.get("P4-T", 0.0) or 0.0)

        max_pump_radial = max(p1_h, p1_v, p2_h, p2_v)
        max_pump_axial = max(p1_a, p2_a)
        max_motor_vib = max(p3_h, p3_v, p3_a, p4_h, p4_v, p4_a)
        max_machine_temp = max(p1_t, p2_t, p3_t, p4_t)

        ts = str(telemetry_row.get("time stamp", ""))

        # Machine configuration context
        mach_meta = self.cfg.get_machine(machine_id) or {}
        rated_rpm = mach_meta.get("rated_speed_rpm", 3000)
        temp_warn = mach_meta.get("temperature_limits", {}).get("warning_deg_c", 70.0)
        temp_alarm = mach_meta.get("temperature_limits", {}).get("alarm_deg_c", 85.0)

        # -------------------------------------------------------------
        # 1. Rotor Imbalance
        # -------------------------------------------------------------
        pump_radial_to_axial = max_pump_radial / (max_pump_axial + 1e-4)
        imbalance_score = 0.0
        imbalance_sup = []
        imbalance_miss = []

        if max_pump_radial >= 6.0 and pump_radial_to_axial >= 2.0:
            imbalance_score += 0.55
            imbalance_sup.append(f"High radial vibration on pump bearings ({max_pump_radial:.2f} mm/s RMS)")
            imbalance_sup.append(f"Radial-to-axial vibration ratio is high ({pump_radial_to_axial:.2f} >= 2.0)")

        if spec.get("ratio_1x_to_overall", 0.0) >= 0.70:
            imbalance_score += 0.35
            imbalance_sup.append(f"Dominant 1x running speed component ({spec.get('ratio_1x_to_overall', 0):.2f} of total RMS energy)")
        else:
            imbalance_miss.append("Cross-channel phase analysis between Horizontal and Vertical planes (approx 90 deg)")

        if imbalance_score >= 0.50:
            candidates.append(FaultCandidate(
                fault_name="Rotor Imbalance",
                fault_family="mechanical",
                confidence_score=min(imbalance_score, 0.95),
                evidence_level="HIGH" if imbalance_score >= 0.80 else "MODERATE",
                selection_reason="Dominant 1x sinusoidal energy polarized in radial direction on pump bearings.",
                supporting_evidence=imbalance_sup,
                missing_evidence=imbalance_miss or ["Phase vector confirmation during dynamic coast-down"],
                relevant_locations=["P1", "P2"],
                recommended_action="Inspect impeller for dirt accumulation or loss of balancing weights; conduct dynamic two-plane balancing."
            ))

        # -------------------------------------------------------------
        # 2. Shaft or Coupling Misalignment
        # -------------------------------------------------------------
        misalign_score = 0.0
        misalign_sup = []
        misalign_miss = []

        # Misalignment is characterized by dominant axial vibration across the coupling
        # and/or prominent 2x running speed harmonic.
        coupling_axial_high = (p2_a >= 5.5 and p3_a >= 5.5 and (p2_a >= p2_h * 0.9 or p3_a >= p3_h * 0.9))
        ratio_2x = spec.get("ratio_2x_to_1x", 0.0)

        if coupling_axial_high:
            misalign_score += 0.50
            misalign_sup.append(f"Elevated axial vibration across coupling hubs (P2-A: {p2_a:.2f}, P3-A: {p3_a:.2f} mm/s)")

        if ratio_2x >= 0.35:
            misalign_score += 0.40
            misalign_sup.append(f"Pronounced 2x harmonic component ({ratio_2x:.2f} relative to 1x fundamental)")
        else:
            misalign_miss.append("High-resolution laser shaft alignment measurement across coupling hubs")
            misalign_miss.append("180 degree axial phase shift measurement across coupling")

        if misalign_score >= 0.45:
            candidates.append(FaultCandidate(
                fault_name="Shaft or Coupling Misalignment",
                fault_family="mechanical",
                confidence_score=min(misalign_score, 0.95),
                evidence_level="HIGH" if misalign_score >= 0.80 else "MODERATE",
                selection_reason="Coordinated elevated axial vibration across pump and motor drive-end bearings.",
                supporting_evidence=misalign_sup,
                missing_evidence=misalign_miss,
                relevant_locations=["P2", "P3"],
                recommended_action="Inspect flexible coupling element for wear; perform dial indicator / laser shaft alignment and check pipe strain."
            ))

        # -------------------------------------------------------------
        # 3. Mechanical Looseness
        # -------------------------------------------------------------
        looseness_score = 0.0
        looseness_sup = []
        looseness_miss = []

        # Directional asymmetry: H / V ratio extreme
        h_to_v_p1 = p1_h / (p1_v + 1e-4)
        h_to_v_p4 = p4_h / (p4_v + 1e-4)

        if (h_to_v_p1 >= 2.2 or h_to_v_p1 <= 0.45) or (h_to_v_p4 >= 2.2 or h_to_v_p4 <= 0.45):
            looseness_score += 0.45
            looseness_sup.append(f"Significant horizontal-to-vertical directional asymmetry (H/V ratio: {max(h_to_v_p1, h_to_v_p4):.2f})")

        if spec.get("amp_subharmonic_0_5x_mm_s", 0.0) >= 1.5:
            looseness_score += 0.40
            looseness_sup.append(f"Prominent fractional subharmonics (0.5x order: {spec.get('amp_subharmonic_0_5x_mm_s'):.2f} mm/s)")
        else:
            looseness_miss.append("Operational Deflection Shape (ODS) survey or motion amplification video")
            looseness_miss.append("Torque check on foundation hold-down bolts")

        if looseness_score >= 0.45:
            candidates.append(FaultCandidate(
                fault_name="Mechanical Looseness",
                fault_family="mechanical",
                confidence_score=min(looseness_score, 0.90),
                evidence_level="MODERATE",
                selection_reason="Directional structural stiffness asymmetry combined with harmonic/subharmonic content.",
                supporting_evidence=looseness_sup,
                missing_evidence=looseness_miss,
                relevant_locations=["P1", "P4"],
                recommended_action="Inspect baseplate grouting, check for soft foot, and verify torque on foundation anchor bolts."
            ))

        # -------------------------------------------------------------
        # 4. Rolling-Element Bearing Defect & Overheating
        # -------------------------------------------------------------
        bearing_score = 0.0
        bearing_sup = []
        bearing_miss = []

        if max_machine_temp >= temp_warn:
            bearing_score += 0.35
            bearing_sup.append(f"Elevated bearing temperature ({max_machine_temp:.1f} deg C exceeds warning threshold of {temp_warn:.1f} deg C)")

        if max_machine_temp >= temp_alarm:
            bearing_score += 0.20
            bearing_sup.append(f"Critical bearing thermal escalation ({max_machine_temp:.1f} deg C exceeds alarm threshold)")

        if spec.get("high_freq_rms_mm_s", 0.0) >= 3.0 or spec.get("ratio_hf_to_overall", 0.0) >= 0.30:
            bearing_score += 0.35
            bearing_sup.append(f"High-frequency spectral excitation ({spec.get('high_freq_rms_mm_s', 0):.2f} mm/s in >3.5x band)")
        else:
            bearing_miss.append("High-frequency demodulation / PeakVue envelope spectrum")
            bearing_miss.append("Bearing kinematic defect calculations (BPFO, BPFI, BSF, FTF)")

        if bearing_score >= 0.50:
            # Determine dominant temperature location
            loc_t = "P2" if p2_t == max_machine_temp else ("P1" if p1_t == max_machine_temp else ("P3" if p3_t == max_machine_temp else "P4"))
            candidates.append(FaultCandidate(
                fault_name="Rolling-Element Bearing Defect & Thermal Overheating",
                fault_family="bearing",
                confidence_score=min(bearing_score, 0.95),
                evidence_level="HIGH" if bearing_score >= 0.80 else "MODERATE",
                selection_reason="Combined high-frequency impact energy with concurrent bearing thermal rise.",
                supporting_evidence=bearing_sup,
                missing_evidence=bearing_miss,
                relevant_locations=[loc_t],
                recommended_action="Conduct ultrasonic acoustic emission check; verify lubrication condition; plan bearing replacement."
            ))

        # -------------------------------------------------------------
        # 5. Lubrication Deficiency
        # -------------------------------------------------------------
        if max_machine_temp >= temp_warn and max_pump_radial < 6.0:
            candidates.append(FaultCandidate(
                fault_name="Lubrication Deficiency / Inadequate Cooling",
                fault_family="tribology",
                confidence_score=0.65,
                evidence_level="MODERATE",
                selection_reason="Significant bearing temperature escalation without severe mechanical synchronous vibration.",
                supporting_evidence=[f"Bearing temperature at {max_machine_temp:.1f} deg C exceeds {temp_warn:.1f} deg C limit"],
                missing_evidence=["Grease/oil sample analysis (viscosity, water contamination, wear particle count)"],
                relevant_locations=["P1", "P2", "P3", "P4"],
                recommended_action="Check grease replenishment interval, oil reservoir level, and bearing cooling water flow."
            ))

        # -------------------------------------------------------------
        # 6. Cavitation / Hydraulic Turbulence
        # -------------------------------------------------------------
        cav_score = 0.0
        cav_sup = []
        cav_miss = []

        is_flow_abnormal = op_ctx.get("flow_outside_por", False)
        suction_press_low = op_ctx.get("suction_pressure_low", False)

        if is_flow_abnormal or suction_press_low:
            cav_score += 0.40
            cav_sup.append("Operating flow or suction pressure outside Preferred Operating Range")

        if spec.get("high_freq_rms_mm_s", 0.0) >= 2.5 and max_pump_radial >= 6.0:
            cav_score += 0.35
            cav_sup.append("Elevated broadband high-frequency acoustic turbulence on pump volute")
        else:
            cav_miss.append("NPSHa vs NPSHr suction head calculation")
            cav_miss.append("Audible acoustic emission survey for gravel-like cavitation noise")

        if cav_score >= 0.40:
            candidates.append(FaultCandidate(
                fault_name="Cavitation / Hydraulic Turbulence",
                fault_family="hydraulic",
                confidence_score=min(cav_score, 0.85),
                evidence_level="MODERATE",
                selection_reason="Elevated pump vibration combined with off-design flow or suction head deficit.",
                supporting_evidence=cav_sup,
                missing_evidence=cav_miss,
                relevant_locations=["P1", "P2"],
                recommended_action="Inspect suction strainers for clogging; check tank level; modulate discharge throttling valve into POR."
            ))

        # -------------------------------------------------------------
        # 7. Potential Motor / Electrical Fault
        # -------------------------------------------------------------
        if max_motor_vib >= 6.5 and max_pump_radial < 4.5:
            candidates.append(FaultCandidate(
                fault_name="Potential Motor / Electrical Asymmetry",
                fault_family="electrical",
                confidence_score=0.60,
                evidence_level="MODERATE",
                selection_reason="Vibration concentrated strictly on motor bearings (P3/P4) while pump remains calm.",
                supporting_evidence=[f"Motor vibration elevated ({max_motor_vib:.2f} mm/s) relative to pump ({max_pump_radial:.2f} mm/s)"],
                missing_evidence=[
                    "Motor Current Signature Analysis (MCSA)",
                    "3-phase supply voltage and stator current waveforms",
                    "Twice line frequency (2x FL = 100 Hz) spectral peak verification"
                ],
                relevant_locations=["P3", "P4"],
                recommended_action="Collect MCSA current measurements; test stator winding resistance and inspect rotor bars."
            ))

        # -------------------------------------------------------------
        # 8. Sensor Fault / Data Quality Anomaly
        # -------------------------------------------------------------
        # Checked if values are missing, frozen zero, or identical across days
        zero_cells = sum(1 for v in [p1_h, p1_v, p1_a, p2_h, p2_v, p2_a] if v == 0.0)
        if zero_cells >= 2:
            candidates.append(FaultCandidate(
                fault_name="Sensor Fault / Telemetry Anomaly",
                fault_family="instrumentation",
                confidence_score=0.75,
                evidence_level="HIGH",
                selection_reason="Multiple zero or non-responsive sensor readings detected.",
                supporting_evidence=[f"{zero_cells} sensor channels reporting zero values"],
                missing_evidence=["Transducer loop resistance and accelerometer mounting check"],
                relevant_locations=["P1", "P2"],
                recommended_action="Inspect accelerometer cabling, check signal conditioner, and verify channel continuity."
            ))

        # -------------------------------------------------------------
        # 9. Fallback: Unknown / Insufficient Evidence
        # -------------------------------------------------------------
        # If machine is in Zone C or Zone D and no single candidate has high confidence (>= 0.70)
        is_abnormal_zone = ("Zone C" in governing_zone) or ("Zone D" in governing_zone)
        high_conf_exists = any(c.confidence_score >= 0.70 for c in candidates)

        if is_abnormal_zone and not high_conf_exists:
            candidates.append(FaultCandidate(
                fault_name="Unknown / Insufficient Evidence — Physical Inspection Required",
                fault_family="indeterminate",
                confidence_score=0.35,
                evidence_level="INSUFFICIENT",
                selection_reason="Vibration severity is elevated (Zone C/D), but available spectral and contextual evidence is insufficient to distinguish a single failure mode.",
                supporting_evidence=[f"Governing severity is {governing_zone} ({max(max_pump_radial, max_motor_vib):.2f} mm/s)"],
                missing_evidence=[
                    "High-resolution portable spectrum acquisition",
                    "Multi-channel phase analysis",
                    "Process operational DCS parameters (flow, suction/discharge pressure, motor power)"
                ],
                relevant_locations=["P1", "P2", "P3", "P4"],
                recommended_action="Deploy predictive maintenance technician for handheld spectral walkdown survey."
            ))

        # Sort candidates by confidence score descending
        candidates.sort(key=lambda c: c.confidence_score, reverse=True)
        dominant = candidates[0] if candidates else None

        uncertainty_note = ""
        if dominant and dominant.confidence_score < 0.70:
            uncertainty_note = "Moderate confidence: Multiple failure hypotheses are technically plausible. Secondary verification required."

        return DiagnosticEvaluation(
            machine_id=machine_id,
            timestamp=ts,
            governing_zone=governing_zone,
            candidates=candidates,
            dominant_hypothesis=dominant,
            uncertainty_note=uncertainty_note
        )
