# PR-GAS-014 Slam-Shut Valve Function Testing

| Field | Value |
|---|---|
| Document ID | PR-GAS-014 |
| Version | 3 |
| Effective from | 2024-11-04 |
| Review due | 2027-11-04 |
| Owner | Head of Gas Network Operations |
| Approved by | Gas Safety Manager |
| Applies to | All Harrowmere Gas sites: slam-shut valves |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

A slam-shut valve is the last line of protection against over-pressure downstream of a governor or pressure reduction stream. This procedure sets out how Harrowmere Gas function tests slam-shut valves, the trip settings and tolerances, and the criteria for passing or failing a valve.

## 2 Scope

This procedure applies to all Harrowmere slam-shut valves:

- SSV-HRW-A and SSV-HRW-B on streams A and B of PRS-HRW-01 at the Harrowmere Pressure Reduction Station (GPR-HRW)
- SSV-112 at Mill Lane District Governor (GPR-MLN)
- SSV-118 at Station Road District Governor (GPR-STN)
- SSV-124 at Kingsmead Avenue District Governor (GPR-KAV)

District governor slam-shuts are tested every 12 months, normally during maintenance under PR-GAS-010. GPR-HRW slam-shuts are tested every 6 months, on the standby stream only. A slam-shut is also tested after any repair, adjustment or unplanned trip.

## 3 References

- PR-GAS-010 District Governor Maintenance
- PR-GAS-021 Permit-to-Work for Gas Operations
- PR-GAS-036 Pressure Reduction Station Stream Changeover
- PR-GAS-040 Working in Hazardous Areas (DSEAR Zones)
- PR-CORP-001 Reporting Incidents and Near Misses
- Pressure Systems Safety Regulations 2000 and HSE guidance L122
- Gas Safety (Management) Regulations 1996 and HSE guidance L80
- HSE guidance HSG253 (safe isolation of plant and equipment)

## 4 Definitions

Over-pressure shut-off (OPSO): The trip that closes the slam-shut if the sensed pressure rises above its setting.

Under-pressure shut-off (UPSO): The trip that closes the slam-shut if the sensed pressure falls below its setting.

Impulse line: The small-bore pipe that carries the downstream pressure to the slam-shut sensing head.

Test rig: A nitrogen supply with a fine-control regulator, a calibrated test gauge and a connection to the impulse line test point.

Let-by: Gas passing a closed slam-shut valve.

## 5 Responsibilities

Authorised Person (Gas): Issues the permit-to-work, confirms the stream is isolated or on standby, releases each hold point, and decides on any failed valve.

Competent Person (Pressure Systems): Carries out the test under the permit, records every result and reports any failure immediately.

Gas Network Controller: Confirms the network can be supported during the test, watches outlet pressures by telemetry and logs the test.

Gas Safety Manager: Is informed of every failed test and every unplanned trip.

## 6 Procedure

### 6.1 Trip settings and tolerances

| Valve | Site | OPSO setting | OPSO tolerance | UPSO setting | UPSO tolerance |
|---|---|---|---|---|---|
| SSV-HRW-A | GPR-HRW stream A | 1.90 bar | plus or minus 0.04 bar | not fitted | not applicable |
| SSV-HRW-B | GPR-HRW stream B | 1.90 bar | plus or minus 0.04 bar | not fitted | not applicable |
| SSV-112 | GPR-MLN | 60 mbar | plus or minus 2.5 mbar | 12 mbar | plus or minus 2 mbar |
| SSV-118 | GPR-STN | 55 mbar | plus or minus 2.5 mbar | 12 mbar | plus or minus 2 mbar |
| SSV-124 | GPR-KAV | 63 mbar | plus or minus 2.5 mbar | 12 mbar | plus or minus 2 mbar |

NOTE: These settings match the governor settings in PR-GAS-010 and the station settings in PR-GAS-036. Only the Gas Safety Manager may approve a change.

### 6.2 Preparation and authorisation

6.2.1 Obtain a permit-to-work from the Authorised Person (Gas) under PR-GAS-021.

6.2.2 At a district governor, put the LP network on bypass control or network support and isolate the governor stream under PR-GAS-010.

6.2.3 At GPR-HRW, test only the standby stream. If the stream to be tested is on duty, change over first under PR-GAS-036.

6.2.4 Check that the test gauge has been calibrated within the last 12 months and has a suitable range: 0 to 100 mbar for district governors, 0 to 4 bar for GPR-HRW.

6.2.5 Tell the Gas Network Controller the test is about to start.

HOLD POINT: Do not start the test until the Authorised Person (Gas) has confirmed that the stream under test is isolated, or is the standby stream with the duty stream carrying the full load.

### 6.3 Over-pressure trip test

WARNING: Closing the impulse line isolation valve disables the slam-shut's protection. Never isolate the impulse line on a stream that is supplying the network.

6.3.1 Close the impulse line isolation valve and connect the test rig to the impulse line test point.

6.3.2 Raise the test rig to the normal outlet pressure and reset the slam-shut so that it is latched open.

6.3.3 Raise the pressure slowly, no faster than 1 mbar per second for district governors or 0.01 bar per second for GPR-HRW.

6.3.4 Record the pressure at which the valve trips and confirm the position indicator shows fully closed.

6.3.5 Before reducing the test pressure, try to relatch the valve with the pressure still above the trip setting. It must not relatch.

6.3.6 Reduce the test pressure to the normal outlet pressure, reset the valve, and repeat the test once more.

### 6.4 Under-pressure trip test

NOTE: This subsection applies only to SSV-112, SSV-118 and SSV-124. The GPR-HRW slam-shuts have no under-pressure trip.

6.4.1 With the valve latched open and the test rig at normal outlet pressure, lower the pressure slowly, no faster than 1 mbar per second.

6.4.2 Record the pressure at which the valve trips and confirm the position indicator shows fully closed.

6.4.3 Restore normal outlet pressure, reset the valve and repeat the test once more.

### 6.5 Let-by test

6.5.1 With the slam-shut tripped closed and the outlet valve closed, vent the section between them to zero through the vent valve.

6.5.2 Close the vent valve and watch the gauge on the vented section.

6.5.3 For district governors, record the pressure rise over 5 minutes. For GPR-HRW, record the pressure rise over 10 minutes.

### 6.6 Pass and fail criteria

NOTE: A slam-shut valve passes only if every check in 6.6.1 to 6.6.5 is met.

6.6.1 Confirm that both OPSO trips, and both UPSO trips where fitted, are within the tolerance in 6.1.

6.6.2 Confirm that the valve closed fully in a single movement each time and the position indicator showed closed.

6.6.3 Confirm that the valve did not relatch while the test pressure was above the OPSO setting.

6.6.4 Confirm that let-by was no more than 1 mbar rise in 5 minutes for district governors, or no more than 10 mbar rise in 10 minutes for GPR-HRW.

6.6.5 Confirm that the valve resets and latches open without force.

WARNING: A failed slam-shut gives no reliable protection against over-pressure. Never return a stream with a failed slam-shut to service.

6.6.6 If any criterion is not met, record the valve as failed, tell the Authorised Person (Gas) and the Gas Network Controller, and keep the stream isolated until it is repaired and re-tested.

### 6.7 Reset and return to service

6.7.1 Disconnect the test rig and refit the test point cap.

6.7.2 Open the impulse line isolation valve and confirm it is locked open.

6.7.3 Equalise pressure across the slam-shut using its reset bypass, then reset the valve so it is latched open.

6.7.4 Return the stream to service under PR-GAS-010, or to standby under PR-GAS-036.

HOLD POINT: Do not cancel the permit until the Authorised Person (Gas) has confirmed that the impulse line isolation valve is open, the slam-shut is latched open and all results are recorded.

### 6.8 Unplanned trips

6.8.1 If a slam-shut is found tripped in service, do not reset it.

6.8.2 Tell the Gas Network Controller, who will arrange the response to any loss of supply.

6.8.3 The Authorised Person (Gas) must establish the cause of the trip and authorise a function test before the valve is reset.

### 6.9 Emergency

6.9.1 If gas escapes uncontrollably, clear the area and report to the Gas Network Controller for action under PR-GAS-003.

6.9.2 Call 999 for fire or injury, and call the National Gas Emergency Service on 0800 111 999 if the Gas Network Controller cannot be reached.

6.9.3 Report every failed test, unplanned trip and near miss under PR-CORP-001.

## 7 Records

The slam-shut test record holds the valve ID, date, test gauge serial number and calibration date, each trip pressure, let-by result, pass or fail decision and the permit number. It is kept in the asset file for the life of the valve. Failed tests are raised as defects in the work management system.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2016-11-07 | First issue. |
| 2 | 2020-11-02 | Added under-pressure trip testing for district governor slam-shuts and let-by test. |
| 3 | 2024-11-04 | Added relatch check, two-trip pass criterion, hold point on impulse line valve before cancelling the permit, and unplanned trip section. GPR-HRW test interval reduced from 12 to 6 months. |
