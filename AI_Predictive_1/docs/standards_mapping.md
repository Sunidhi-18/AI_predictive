# Vibration Standards Mapping & Severity Assessment Methodology

**Applicable Standard:** ISO 10816-7:2009 / BS ISO 10816-7  
**Primary Reference Text:** *Europump Guideline on Pump Vibration First Edition (July 2013)*, Section 1.5 & Table 1 (Page 9)  
**Supporting Reference:** *ISO 10816-7:2009(E) Mechanical vibration — Evaluation of machine vibration by measurements on non-rotating parts — Part 7*

---

## 1. Normative Status of the Standard (Checked October 2026)

- **Current Published Standard:** ISO 10816-7:2009 remains the officially published international standard for rotodynamic pumps.
- **Revision Status:** ISO TC 108/SC 2 is actively preparing a revised standard under the harmonized 20816 series, designated **ISO/AWI 20816-7** (*Mechanical vibration — Measurement and evaluation of machine vibration — Part 7: Rotodynamic pumps*).
- **Mandatory Compliance Rule:** Because ISO/AWI 20816-7 is currently an Approved Work Item (AWI) under development and has not been formally published, **all operational thresholds in this project are strictly mapped to ISO 10816-7:2009 / Europump 2013 Table 1**. We do NOT cite unapproved draft revisions as published standards.

---

## 2. Scope, Applicability & Machine Categories

ISO 10816-7 applies to rotodynamic pumps for industrial applications with nominal power **above 1 kW** and impellers having **more than 3 vanes**, evaluated via vibration measurements on non-rotating parts (bearing housings).

### Why Pump Category & Power Matter:
Rigid assumptions (such as applying a universal 7.0 mm/s limit) violate international engineering guidelines. Vibration limits depend heavily on pump design, service criticality, and power:

1. **Category I (High Criticality / Arduous Duty):**
   - Pumps required to have a high level of reliability, availability, or safety.
   - Applications: toxic/hazardous fluids, critical petrochemical, oil & gas, boiler feed water, nuclear, and major power utility pumps.
   - Requires tighter allowable vibration limits.
2. **Category II (General Duty):**
   - Pumps for general industrial or less critical services (e.g., non-hazardous water, circulation, sewage).
   - Vertical suspended pumps with speeds > 600 rpm are classified under Category II.
   - Has slightly higher allowable vibration thresholds.
3. **Nominal Power Stratification:**
   - Pumps $\le 200\text{ kW}$
   - Pumps $> 200\text{ kW}$ (larger machines tolerate higher absolute velocity due to increased structural mass and shaft dimensions).

---

## 3. Evaluation Zones and Operational Ranges

Measurements are evaluated in terms of **overall vibration velocity RMS (mm/s)** over the frequency range $10\text{ Hz}$ to $1000\text{ Hz}$.

### Zone Definitions:
- **Zone A:** Vibration of newly commissioned machines in the Preferred Operating Range (POR).
- **Zone B:** Machines acceptable for unrestricted long-term continuous operation in the Allowable Operating Range (AOR).
- **Zone C:** Unsatisfactory for continuous long-term operation. Limited operation permitted until corrective maintenance can be scheduled.
- **Zone D:** High vibration severity sufficient to cause physical damage. Immediate intervention required.

### Operating Ranges:
- **POR (Preferred Operating Range):** Typically $70\%$ to $120\%$ of Best Efficiency Point (BEP). Vibration and hydraulic turbulence are at a minimum.
- **AOR (Allowable Operating Range):** Limits within which the pump can operate without exceeding acceptable wear rates. Higher vibration is tolerated compared to POR.

---

## 4. Master Threshold Table (Europump 2013 Table 1, Page 9)

All limits represent overall broadband vibration velocity in **$\text{mm/s RMS}$** measured radially or axially on the bearing housing:

| Category | Rated Power | Zone A (POR) | Zone B (AOR) | Zone C (Limited) | Zone D (Hazardous) | Max Alarm Limit | Max Trip Limit |
|---|---|---|---|---|---|---|---|
| **Category 1** | $\le 200\text{ kW}$ | $\le 2.5$ | $\le 4.0$ | $\le 6.6$ | $> 6.6$ | **$5.0\text{ mm/s}$** | **$8.3\text{ mm/s}$** |
| **Category 1** | $> 200\text{ kW}$ | $\le 3.5$ | $\le 5.0$ | $\le 7.6$ | $> 7.6$ | **$6.3\text{ mm/s}$** | **$9.5\text{ mm/s}$** |
| **Category 2** | $\le 200\text{ kW}$ | $\le 3.2$ | $\le 5.1$ | $\le 8.5$ | $> 8.5$ | **$6.4\text{ mm/s}$** | **$10.6\text{ mm/s}$** |
| **Category 2** | $> 200\text{ kW}$ | $\le 4.2$ | $\le 6.1$ | $\le 9.5$ | $> 9.5$ | **$7.6\text{ mm/s}$** | **$11.9\text{ mm/s}$** |

### Alarm and Trip Setpoint Multipliers:
- **Alarm Setpoint:** Configured at **$1.25 \times \text{Upper Limit of Zone B}$**.
- **Trip Setpoint:** Configured at **$1.25 \times \text{Upper Limit of Zone C}$**.
- **Time Delay:** To avoid nuisance trips caused by hydraulic transients or motor start-up surges, vibration magnitudes must exceed the alarm or trip setpoint continuously for approximately **$10\text{ seconds}$** before triggering plant signals.

---

## 5. Distinction Between Concepts

1. **Severity Zone (A/B/C/D):** An objective classification of machine operating health based on international standards. It does NOT diagnose the fault.
2. **Warning / Alarm Setpoint:** Operational notice that vibration has exceeded normal bounds, prompting condition monitoring investigation.
3. **Trip Setpoint:** Threshold beyond which rapid mechanical damage is likely, mandating protective machine shutdown.
4. **Diagnostic Fault Candidate:** An evidence-backed mechanical hypothesis (e.g., dynamic unbalance, angular misalignment, outer-race bearing spall) derived from spectral analysis, directional ratios, and phase relationships.

---

## 6. Treatment of Incomplete Configurations

If any of the mandatory parameters (`category`, `nominal_power_kw`, or `measurement_location`) is missing or undefined for a machine, the evaluation engine MUST NOT assume default values. It will output:

> `Not evaluable — machine configuration or applicable criterion is incomplete`

Users are provided with an editable interface to supply the missing engineering parameters before assessment is performed.
