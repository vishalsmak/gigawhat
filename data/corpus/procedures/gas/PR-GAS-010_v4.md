# PR-GAS-010 District Governor Maintenance

| Field | Value |
|---|---|
| Document ID | PR-GAS-010 |
| Version | 4 |
| Effective from | 2025-05-06 |
| Review due | 2028-05-06 |
| Owner | Head of Gas Network Operations |
| Approved by | Gas Safety Manager |
| Applies to | All Harrowmere Gas sites: district governors and their slam-shut valves and filters |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how Harrowmere Gas carries out planned maintenance of district governors, including their slam-shut valves, creep relief valves and filters, while keeping customers in supply. It also sets the standard pressure settings for each district governor.

## 2 Scope

This procedure applies to the three district governors that reduce medium pressure (MP) to low pressure (LP):

- G-112 at Mill Lane District Governor (GPR-MLN), installed 2006, with slam-shut valve SSV-112 and filter FLT-112
- G-118 at Station Road District Governor (GPR-STN), installed 1998, with slam-shut valve SSV-118
- G-124 at Kingsmead Avenue District Governor (GPR-KAV), installed 2015, with slam-shut valve SSV-124

Each installation has a single regulator stream with a manually operated bypass. Annual maintenance is carried out between 1 April and 30 September, when demand is low. The slam-shut valves and filter at the Harrowmere Pressure Reduction Station (GPR-HRW) are maintained under the station plan, with stream changeover under PR-GAS-036.

## 3 References

- PR-GAS-014 Slam-Shut Valve Function Testing
- PR-GAS-021 Permit-to-Work for Gas Operations
- PR-GAS-040 Working in Hazardous Areas (DSEAR Zones)
- PR-GAS-058 Governor Inspection and Pressure Recording
- PR-GAS-003 Response to Reported Gas Escapes
- PR-CORP-001 Reporting Incidents and Near Misses
- Pressure Systems Safety Regulations 2000 and HSE guidance L122
- Gas Safety (Management) Regulations 1996 and HSE guidance L80
- HSE guidance HSG250 (permit-to-work systems) and HSG253 (safe isolation of plant and equipment)

## 4 Definitions

Outlet set point: The LP pressure the governor is set to maintain at its outlet.

Creep relief valve: A small relief valve on the governor outlet that vents gas if the outlet pressure creeps above the set point because the governor is not shutting off tightly at low flow.

Over-pressure shut-off (OPSO): The slam-shut trip that closes the valve if outlet pressure rises above the trip setting.

Under-pressure shut-off (UPSO): The slam-shut trip that closes the valve if outlet pressure falls below the trip setting.

Bypass control: Keeping the LP network in supply through the manual bypass valve, with a person continuously watching the outlet pressure.

## 5 Responsibilities

Authorised Person (Gas): Plans the work, agrees supply arrangements with the Gas Network Controller, issues the permit-to-work, and releases each hold point.

Competent Person (Pressure Systems): Carries out the isolation, maintenance, testing and setting under the permit, and records all readings.

Gas Network Controller: Confirms whether the LP network can be supported while the governor is out of service, monitors network pressures by telemetry throughout, and logs the work.

Gas Safety Manager: Approves any change to the settings in 6.1.

## 6 Procedure

### 6.1 Governor settings

The standard settings below must be used unless the Gas Safety Manager has approved a change in writing. Normal inlet pressure for all three governors is 1.0 to 2.0 bar.

| Governor | Site | Outlet set point | Creep relief (start to discharge) | SSV over-pressure trip (OPSO) | SSV under-pressure trip (UPSO) |
|---|---|---|---|---|---|
| G-112 | GPR-MLN | 35 mbar | 47 mbar | 60 mbar (SSV-112) | 12 mbar (SSV-112) |
| G-118 | GPR-STN | 30 mbar | 42 mbar | 55 mbar (SSV-118) | 12 mbar (SSV-118) |
| G-124 | GPR-KAV | 40 mbar | 52 mbar | 63 mbar (SSV-124) | 12 mbar (SSV-124) |

Tolerances: outlet set point plus or minus 1 mbar; creep relief plus or minus 2 mbar; OPSO plus or minus 2.5 mbar; UPSO plus or minus 2 mbar.

NOTE: The settings are in a fixed order: outlet set point, then creep relief, then OPSO, all below the LP maximum of 75 mbar. Never set the creep relief at or above the OPSO setting.

### 6.2 Planning and authorisation

6.2.1 Check the last inspection record under PR-GAS-058 and note any defects to be put right.

6.2.2 Ask the Gas Network Controller to confirm, from telemetry and the network model, whether the LP network can be supported by the other governors while this governor is out of service.

6.2.3 Plan for bypass control at G-118 in all cases, because the Station Road LP network it feeds is not interconnected.

6.2.4 Obtain a permit-to-work from the Authorised Person (Gas) under PR-GAS-021, with an isolation certificate for the governor stream.

6.2.5 Check that the test gauge is calibrated within the last 12 months and that the gas detector has been bump tested.

6.2.6 Treat the governor kiosk as a hazardous area under PR-GAS-040 and keep all non-Ex equipment outside it.

HOLD POINT: Do not operate any valve until the Authorised Person (Gas) has issued the permit and the Gas Network Controller has confirmed the supply arrangement.

### 6.3 Maintaining supply on bypass control

WARNING: An open bypass passes MP gas straight into the LP network. If it is left unattended or opened too far, LP pressure can rise above 75 mbar and put customers' appliances and pipework at risk.

6.3.1 Fit a calibrated test gauge to the outlet test point and keep it in view of the bypass valve.

6.3.2 Open the bypass valve slowly until the outlet pressure is held at the set point in 6.1.

6.3.3 Keep a Competent Person (Pressure Systems) at the bypass valve at all times while it is open, adjusting it to hold the set point within plus or minus 3 mbar.

6.3.4 Record the outlet pressure every 10 minutes while on bypass.

6.3.5 Close the bypass valve immediately if the outlet pressure reaches the creep relief setting.

### 6.4 Isolating and venting the governor stream

WARNING: The section between the inlet valve and the governor holds MP gas. Never break containment until isolation has been proved.

6.4.1 Close the outlet valve slowly, then close the inlet valve.

6.4.2 Lock and tag both valves with the permit number.

6.4.3 Vent the isolated section through the vent valve to the vent stack until the gauge reads zero.

6.4.4 Close the vent valve and watch the gauge for 5 minutes. Any pressure rise means a valve is passing.

6.4.5 Record the proving result on the isolation certificate.

HOLD POINT: Do not break containment until the Authorised Person (Gas) has witnessed the proving test and signed the isolation certificate.

### 6.5 Filter and governor maintenance

CAUTION: Filter dust can contain iron sulphide, which can heat up and ignite when it dries in air. Keep dust damp and seal it in a bag before removing it from site.

6.5.1 At G-112, record the FLT-112 differential pressure before isolation, then replace the filter element if the differential pressure was above 100 mbar or the element is more than 3 years old.

6.5.2 At G-118 and G-124, remove and clean the governor inlet strainer.

6.5.3 Inspect the governor diaphragm, valve seat and seals, and replace them with the manufacturer's kit every 6 years or sooner if worn.

6.5.4 Check that impulse lines are clear, undamaged and connected to the correct sensing points.

6.5.5 Check that vent terminals for the governor, creep relief and slam-shut are clear and fitted with insect screens.

### 6.6 Slam-shut and creep relief checks

6.6.1 Function test the slam-shut valve under PR-GAS-014, using the OPSO and UPSO settings in 6.1.

6.6.2 Record the trip pressures and confirm they are within tolerance.

6.6.3 Test the creep relief valve with the test rig and record the pressure at which it starts to discharge.

6.6.4 Adjust any setting found outside tolerance, then re-test it.

6.6.5 Reset the slam-shut valve and confirm its impulse line isolation valve is open.

### 6.7 Recommissioning and setting

6.7.1 Remove locks and tags only on the instruction of the Authorised Person (Gas).

6.7.2 Open the inlet valve slowly to pressurise the governor stream against the closed outlet valve.

6.7.3 Test all disturbed joints at operating pressure with leak detection fluid and a gas detector.

6.7.4 Set the outlet set point using the test gauge, with a small flow through the outlet vent point, to the value in 6.1.

6.7.5 Open the outlet valve slowly, then close the bypass valve slowly if it was in use, watching the outlet pressure throughout.

6.7.6 Watch the outlet pressure for 15 minutes and confirm it is steady within plus or minus 1 mbar of the set point.

HOLD POINT: Do not cancel the permit or leave site until the Authorised Person (Gas) has confirmed that all settings are recorded within tolerance, the slam-shut is latched open and the Gas Network Controller has confirmed normal telemetry readings.

### 6.8 Emergency

6.8.1 If gas escapes uncontrollably, close the nearest safe isolation valve, clear the area and report to the Gas Network Controller for action under PR-GAS-003.

6.8.2 If LP pressure is lost or exceeds 75 mbar, tell the Gas Network Controller immediately.

6.8.3 Call 999 for fire or injury, and call the National Gas Emergency Service on 0800 111 999 if the Gas Network Controller cannot be reached.

6.8.4 Report every incident and near miss under PR-CORP-001.

## 7 Records

The maintenance record for each governor holds the as-found and as-left settings, filter differential pressure, parts replaced, slam-shut trip pressures and creep relief pressure. It is kept with the permit-to-work and isolation certificate in the asset file for the life of the governor. Settings outside tolerance are raised as defects in the work management system.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2013-04-01 | First issue. |
| 2 | 2016-05-03 | Added under-pressure shut-off settings and creep relief tolerances. |
| 3 | 2022-05-03 | Added filter dust precautions and 6-yearly soft parts replacement. |
| 4 | 2025-05-06 | Added Gas Network Controller network support check, mandatory bypass control at G-118, and hold point before leaving site. Settings table moved into 6.1. |
