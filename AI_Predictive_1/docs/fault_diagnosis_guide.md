# Industrial Machinery Fault Diagnosis & Vibration Analyst Reference Guide

This reference handbook documents the 12 condition-monitoring fault families implemented in the rule engine, detailing characteristic vibration signatures, physical root causes, directional patterns, spectral indicators, and recommended maintenance interventions.

---

## 1. Rotor Imbalance
- **Physical Cause:** Center of mass of the rotating assembly does not coincide with the geometric center of rotation (e.g., uneven impeller dirt build-up, loss of balance weights, broken vane tip, cavitation erosion).
- **Vibration Signature:**
  - Dominant sinusoidal 1× running speed peak in radial directions (Horizontal and Vertical).
  - Horizontal and vertical vibration amplitudes are typically high, with axial vibration remaining low.
  - Phase difference between horizontal and vertical planes is approximately $90^\circ$ ($\pm 30^\circ$).
- **Supporting Telemetry:** Concentrated high RMS on pump bearing housings (P1-H, P1-V, P2-H, P2-V).
- **Missing / Follow-up Evidence:** Phase measurement across bearings, single/two-plane dynamic balancing survey.
- **Recommended Action:** Inspect impeller for uneven fouling; clean and perform dynamic field balancing.

---

## 2. Shaft or Coupling Misalignment
- **Physical Cause:** Shaft centerlines of driving (motor) and driven (pump) units are not colinear (angular, parallel, or combination misalignment).
- **Vibration Signature:**
  - High 1× and prominent 2× running speed harmonics. High 2× is the classic hallmark of misalignment.
  - Substantial axial vibration, especially at the coupling bearings (P2-A and P3-A).
  - Phase shift across the coupling in the axial direction is approximately $180^\circ$ out of phase.
- **Supporting Telemetry:** Coordinated elevated vibration across both pump drive-end (P2) and motor drive-end (P3).
- **Missing / Follow-up Evidence:** Dial indicator or laser shaft alignment measurement, soft foot survey.
- **Recommended Action:** Check coupling insert for wear; perform hot/cold laser alignment and verify pipe strain.

---

## 3. Mechanical Looseness
- **Physical Cause:** Excessive bearing clearance, loose foundation bolts, cracked structural grout, or loose bearing cap fits.
- **Vibration Signature:**
  - Multiple harmonics of running speed ($1\times, 2\times, 3\times, 4\times \dots 10\times$).
  - Possible half-order subharmonics ($0.5\times, 1.5\times, 2.5\times$) caused by non-linear stiffness and bouncing.
  - Severe directional asymmetry (e.g., Vertical much higher or lower than Horizontal).
- **Supporting Telemetry:** Sudden jumps in directional ratios.
- **Missing / Follow-up Evidence:** Torque check on anchor bolts, operational deflection shape (ODS) motion amplification.
- **Recommended Action:** Check foundation hold-down bolts, inspect baseplate grout, check bearing housing bore tolerances.

---

## 4. Resonance & Structural / Foundation Issues
- **Physical Cause:** Natural frequency of the pump, motor, baseplate, or attached piping coincides with or is excited by forcing frequencies (e.g., 1× RPM, 2× RPM, blade pass).
- **Vibration Signature:**
  - Abnormally high amplitude at a specific speed with steep drop-off when speed changes slightly.
  - Directional vibration heavily polarized along the flexible structural axis.
- **Supporting Telemetry:** High vibration localized to one direction or point despite low residual unbalance.
- **Missing / Follow-up Evidence:** Impact (bump) test with machine shut down; run-up / coast-down Bode/Nyquist peak response.
- **Recommended Action:** Stiffen foundation / piping supports or adjust operating RPM away from resonant zone.

---

## 5. Rolling-Element Bearing Defects
- **Physical Cause:** Fatigue spalling, brinelling, flaking, or cracking on raceways or rolling elements.
- **Vibration Signature:**
  - Non-synchronous discrete defect frequencies calculated from bearing geometry:
    - **BPFO (Ball Pass Frequency Outer Race):** $\frac{n}{2}\left(1 - \frac{d}{D}\cos\alpha\right) f_r$ (typically $3.0\times - 4.5\times$)
    - **BPFI (Ball Pass Frequency Inner Race):** $\frac{n}{2}\left(1 + \frac{d}{D}\cos\alpha\right) f_r$ (typically $5.0\times - 6.5\times$)
    - **BSF (Ball Spin Frequency):** $\frac{D}{2d}\left(1 - \left(\frac{d}{D}\cos\alpha\right)^2\right) f_r$
    - **FTF (Fundamental Train Frequency - Cage):** $\frac{1}{2}\left(1 - \frac{d}{D}\cos\alpha\right) f_r$ (typically $0.38\times - 0.42\times$)
  - In advanced stages, defect peaks modulate with 1× sidebands and high-frequency noise carpet rises.
- **Supporting Telemetry:** Elevated high-frequency vibration accompanied by progressive temperature rise.
- **Missing / Follow-up Evidence:** High-frequency envelope spectrum (PeakVue / demodulation), ultrasonic acoustic emission.
- **Recommended Action:** Greasing check; schedule planned bearing replacement before catastrophic cage failure.

---

## 6. Lubrication-Related Issues & Abnormal Bearing Temperature
- **Physical Cause:** Insufficient lubricant, over-greasing, oil oxidation, water contamination, or loss of oil cooler cooling.
- **Vibration Signature:**
  - High-frequency friction carpet (broadband excitation in $1\text{ kHz} - 5\text{ kHz}$ region) without discrete harmonics.
- **Supporting Telemetry:** Bearing temperature sharply exceeds baseline ($> 70^\circ\text{C} - 85^\circ\text{C}$).
- **Missing / Follow-up Evidence:** Oil sample viscosity, Karl Fischer water test, infrared thermography.
- **Recommended Action:** Inspect oil level, verify grease quantity, inspect oil seals, test cooling water circuit.

---

## 7. Cavitation & Hydraulic Turbulence
- **Physical Cause:** Net Positive Suction Head available (NPSHa) drops below required (NPSHr), causing vapor bubble collapse.
- **Vibration Signature:**
  - Broad continuous high-frequency random energy (hump in the $500\text{ Hz} - 5000\text{ Hz}$ range).
  - Audible noise reminiscent of gravel or stones passing through the pump volute.
- **Supporting Telemetry:** Fluctuating suction pressure and low-flow or over-flow conditions outside POR.
- **Missing / Follow-up Evidence:** Suction pressure transmitter logs, differential pressure, liquid temperature.
- **Recommended Action:** Clean suction strainers, open suction throttling valves fully, verify tank liquid level.

---

## 8. Impeller Blade-Passing Vibration
- **Physical Cause:** Pressure pulses generated each time an impeller vane passes the casing cutwater / diffuser vane.
- **Vibration Signature:**
  - Dominant discrete peak at Blade Pass Frequency: $\text{BPF} = Z \times f_r$ (where $Z$ is the number of vanes).
  - Harmonics at $2 \times \text{BPF}$ if cutwater clearance is too small (Gap 'A' $< 5-10\%$).
- **Supporting Telemetry:** High vibration localized to pump casing / bearings (P1, P2) in radial direction.
- **Missing / Follow-up Evidence:** Internal inspection of volute cutwater tip and impeller vane diameter.
- **Recommended Action:** Confirm cutwater clearance; inspect volute for erosion or foreign object wedged in nozzle.

---

## 9. Abnormal Operation Outside Preferred Operating Range (POR)
- **Physical Cause:** Operating pump at extreme low flow (internal recirculation) or high flow (run-out).
- **Vibration Signature:**
  - Increased low-frequency hydraulic surge ($0.1\times - 0.3\times$) or broadband flow turbulence.
- **Supporting Telemetry:** Process flow meter indicating flow $< 70\%$ or $> 120\%$ of BEP.
- **Missing / Follow-up Evidence:** Discharge valve position, pump curve comparison.
- **Recommended Action:** Modulate discharge valve or bypass line to return pump into $70\% - 120\%$ of BEP.

---

## 10. Mechanical Rubbing / Shaft Contact
- **Physical Cause:** Rotating impeller or shaft contacting stationary wear rings, stuffing box, or seal faces.
- **Vibration Signature:**
  - Truncated waveform causing fractional subharmonics ($1/2\times, 1/3\times$) and multiple synchronous harmonics.
- **Supporting Telemetry:** Localized sharp temperature spikes at mechanical seal or stuffing box.
- **Missing / Follow-up Evidence:** Radial play / clearance measurement, seal inspection.
- **Recommended Action:** Inspect seal faces, check shaft deflection, inspect wear ring clearance.

---

## 11. Potential Motor / Electrical Faults
- **Physical Cause:** Stator winding unbalance, broken rotor bars, air-gap eccentricity, or variable frequency drive harmonics.
- **Vibration Signature:**
  - Vibration at twice line frequency ($2 \times f_L = 100\text{ Hz}$ for $50\text{ Hz}$ electrical grid; $120\text{ Hz}$ for $60\text{ Hz}$).
  - Pole pass frequency sidebands ($f_p = 2 \cdot s \cdot f_L$) around 1× RPM peak.
- **Supporting Telemetry:** Motor bearing vibration (P3, P4) elevated while pump bearings (P1, P2) remain normal.
- **Missing / Follow-up Evidence:** Motor Current Signature Analysis (MCSA), stator insulation resistance (Megger test).
- **Recommended Action:** Collect 3-phase current waveforms; test motor winding resistance.

---

## 12. Sensor Faults, Missing Data & Unknown / Insufficient Evidence
- **Physical Cause:** Cable break, loose accelerometer stud, transmitter drift, telemetry loss, or ambiguous multi-mode failure.
- **Vibration Signature:**
  - Flatline (constant zero or fixed repeated value), infinite spiking, or intermittent nulls.
- **System Outcome:**
  - If data is invalid: Quarantined with documented reason.
  - If data is abnormal but evidence is insufficient: The rule engine outputs **`Unknown / insufficient evidence — physical inspection required`**.
- **Recommended Action:** Check accelerometer cabling, test signal conditioner power, verify physical transducer mounting.
