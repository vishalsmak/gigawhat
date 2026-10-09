# PR-GAS-058 Governor Inspection and Pressure Recording

| Field | Value |
|---|---|
| Document ID | PR-GAS-058 |
| Version | 3 |
| Effective from | 2025-07-07 |
| Review due | 2028-07-07 |
| Owner | Head of Gas Network Operations |
| Approved by | Gas Safety Manager |
| Applies to | All Harrowmere Gas sites: district governors and slam-shut valves |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out the routine inspection of district governors and their slam-shut valves, and how inlet and outlet pressures are recorded and checked against the standard settings.

## 2 Scope

This procedure applies to monthly inspections of G-112 (GPR-MLN), G-118 (GPR-STN) and G-124 (GPR-KAV) and their slam-shut valves SSV-112, SSV-118 and SSV-124. Inspection does not involve breaking containment or changing any setting. Adjustments and maintenance are carried out under PR-GAS-010 with a permit-to-work.

## 3 References

- PR-GAS-010 District Governor Maintenance
- PR-GAS-014 Slam-Shut Valve Function Testing
- PR-GAS-003 Response to Reported Gas Escapes
- PR-GAS-040 Working in Hazardous Areas (DSEAR Zones)
- PR-CORP-004 Lone Working
- PR-CORP-001 Reporting Incidents and Near Misses
- Pressure Systems Safety Regulations 2000 and HSE guidance L122
- Gas Safety (Management) Regulations 1996 and HSE guidance L80

## 4 Definitions

Outlet set point: The LP pressure the governor is set to maintain, as listed in PR-GAS-010.

Normal outlet band: The range of outlet pressure expected during normal operation, set point plus or minus 3 mbar.

Data logger: The pressure recorder in each governor kiosk that records inlet and outlet pressure every minute.

## 5 Responsibilities

Competent Person (Pressure Systems) or First Call Operative: Carries out the inspection, records the readings and reports anything abnormal.

Gas Network Controller: Records the inspector's arrival and departure, compares site readings with telemetry, and arranges follow-up of abnormal readings.

Authorised Person (Gas): Decides on action for any reading outside the normal band or any tripped slam-shut.

## 6 Procedure

### 6.1 Settings and acceptable readings

| Governor | Site | Outlet set point | Normal outlet band | Creep relief | SSV OPSO trip | SSV UPSO trip |
|---|---|---|---|---|---|---|
| G-112 | GPR-MLN | 35 mbar | 32 to 38 mbar | 47 mbar | 60 mbar | 12 mbar |
| G-118 | GPR-STN | 30 mbar | 27 to 33 mbar | 42 mbar | 55 mbar | 12 mbar |
| G-124 | GPR-KAV | 40 mbar | 37 to 43 mbar | 52 mbar | 63 mbar | 12 mbar |

The normal inlet pressure for all three governors is 1.0 to 2.0 bar. The settings are taken from PR-GAS-010, which takes precedence if they differ.

### 6.2 Arrival and site checks

6.2.1 Tell the Gas Network Controller you have arrived, and start lone working check-ins under PR-CORP-004.

6.2.2 Switch on your gas detector in clean air before opening the kiosk, and follow PR-GAS-040 inside it.

6.2.3 Check the fence, kiosk, locks and signs for damage or signs of entry.

6.2.4 Open the kiosk doors and test for gas before entering. If gas is detected or smelt, follow PR-GAS-003.

6.2.5 Check that vent terminals are clear and their insect screens are in place.

### 6.3 Recording pressures and valve status

6.3.1 Read the inlet and outlet gauges and record both readings with the time.

6.3.2 Ask the Gas Network Controller for the telemetry readings at the same time, and record any difference greater than 2 mbar on the outlet.

6.3.3 Check that the slam-shut position indicator shows open and latched, and that its impulse line isolation valve is open.

6.3.4 At G-112, read and record the FLT-112 differential pressure gauge.

6.3.5 Listen for gas passing through the creep relief valve vent, and record if it is discharging.

### 6.4 Data logger download

6.4.1 Download the data logger and check its battery level.

6.4.2 Record the maximum and minimum outlet pressure since the last download.

6.4.3 Flag any maximum outlet pressure more than 5 mbar above the set point, or any minimum more than 10 mbar below it.

6.4.4 Flag any inlet pressure below 1.0 bar.

6.4.5 Upload the logger file to the asset file before the end of the day.

### 6.5 Abnormal readings

CAUTION: Do not adjust a governor, creep relief valve or slam-shut during an inspection. Adjustment without a permit can lead to over-pressure in the LP network.

6.5.1 If the outlet pressure is outside the normal outlet band, tell the Gas Network Controller and the Authorised Person (Gas) before leaving site.

6.5.2 If the slam-shut is found tripped, do not reset it. Tell the Gas Network Controller immediately and follow the unplanned trip section of PR-GAS-014.

6.5.3 If the creep relief valve is discharging, or the outlet pressure is above the creep relief setting, tell the Gas Network Controller immediately.

6.5.4 If the FLT-112 differential pressure is above 100 mbar, raise a defect for a filter change under PR-GAS-010.

6.5.5 Raise a defect in the work management system for any other fault found.

### 6.6 Emergency

6.6.1 If you smell gas or your detector alarms, leave the kiosk, keep people away and report to the Gas Network Controller for action under PR-GAS-003.

6.6.2 Call 999 for fire or injury, and call the National Gas Emergency Service on 0800 111 999 if the Gas Network Controller cannot be reached.

6.6.3 Report any near miss under PR-CORP-001.

## 7 Records

The inspection record holds the governor ID, date, inspector role, inlet and outlet pressures, telemetry comparison, slam-shut status, filter differential pressure, logger maximum and minimum, and defects raised. Records and logger files are kept in the asset file for 6 years.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2017-07-03 | First issue. |
| 2 | 2021-07-05 | Added data logger download and telemetry comparison. |
| 3 | 2025-07-07 | Settings table aligned with PR-GAS-010 version 4. Added check that the slam-shut impulse line isolation valve is open, and FLT-112 differential pressure trigger. |
