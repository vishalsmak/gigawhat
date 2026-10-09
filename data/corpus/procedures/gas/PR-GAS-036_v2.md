# PR-GAS-036 Pressure Reduction Station Stream Changeover

| Field | Value |
|---|---|
| Document ID | PR-GAS-036 |
| Version | 2 |
| Effective from | 2025-08-04 |
| Review due | 2028-08-04 |
| Owner | Head of Gas Network Operations |
| Approved by | Gas Safety Manager |
| Applies to | Harrowmere Pressure Reduction Station (GPR-HRW): station PRS-HRW-01, slam-shut valves SSV-HRW-A and SSV-HRW-B, and filter FLT-HRW-01 |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how to change the duty stream at the Harrowmere Pressure Reduction Station without interrupting supply to the medium pressure network, and how to isolate a stream for maintenance and return it to standby.

## 2 Scope

This procedure applies to PRS-HRW-01 at GPR-HRW, which reduces intermediate pressure (IP) gas at 4.5 to 7 bar to medium pressure (MP) at up to 2 bar. The MP network it supplies includes MAIN-MP-03 and the district governors G-112, G-118 and G-124.

The station has a common inlet filter, FLT-HRW-01, feeding two identical streams, A and B. Each stream has an inlet valve (A1 or B1), a slam-shut valve (SSV-HRW-A or SSV-HRW-B), a regulator and an outlet valve (A2 or B2). A creep relief valve protects the common outlet header. One stream is on duty and the other is on live standby, set slightly lower so that it takes over automatically if the duty stream fails. The station has no manual bypass.

Changeover is carried out every 3 months to share wear between the streams, before maintenance of a stream, and after a duty stream failure.

## 3 References

- PR-GAS-014 Slam-Shut Valve Function Testing
- PR-GAS-021 Permit-to-Work for Gas Operations
- PR-GAS-040 Working in Hazardous Areas (DSEAR Zones)
- PR-CORP-001 Reporting Incidents and Near Misses
- Pressure Systems Safety Regulations 2000 and HSE guidance L122
- Gas Safety (Management) Regulations 1996 and HSE guidance L80
- HSE guidance HSG253 (safe isolation of plant and equipment)

## 4 Definitions

Duty stream: The stream controlling the station outlet pressure.

Standby stream: The stream with its valves open and its regulator set below the duty set point, ready to take over automatically.

Changeover: Transferring control of outlet pressure from the duty stream to the standby stream.

## 5 Responsibilities

Authorised Person (Gas): Authorises each planned changeover, attends on site, issues the permit for any stream isolation and releases each hold point.

Competent Person (Pressure Systems): Carries out the checks, set point adjustments and valve operations, and records all readings.

Gas Network Controller: Agrees the time of the changeover, watches station inlet and outlet pressures by telemetry throughout, and confirms stable conditions before each next stage.

Gas Safety Manager: Is informed of every unplanned changeover.

## 6 Procedure

### 6.1 Station settings

| Setting | Value | Tolerance |
|---|---|---|
| Duty stream outlet set point | 1.60 bar | plus or minus 0.03 bar |
| Standby stream outlet set point | 1.50 bar | plus or minus 0.03 bar |
| Outlet header creep relief (start to discharge) | 1.80 bar | plus or minus 0.03 bar |
| SSV-HRW-A and SSV-HRW-B over-pressure trip | 1.90 bar | plus or minus 0.04 bar |
| FLT-HRW-01 maximum differential pressure | 300 mbar | not applicable |

NOTE: Only the Gas Safety Manager may approve a change to these settings. The slam-shut settings are also in PR-GAS-014.

### 6.2 Planning and authorisation

6.2.1 Agree the changeover time with the Gas Network Controller, avoiding the winter peak periods of 06:00 to 09:00 and 16:00 to 20:00.

6.2.2 Obtain the Authorised Person (Gas)'s authorisation for the changeover, and a permit-to-work under PR-GAS-021 if a stream will be isolated.

6.2.3 Make sure at least two people are on site; changeover must not be carried out by a lone worker.

6.2.4 Treat the station compound as a hazardous area under PR-GAS-040.

6.2.5 Check that the test gauges are calibrated within the last 12 months.

HOLD POINT: Do not start the changeover until the Authorised Person (Gas) is on site and the Gas Network Controller has confirmed the agreed start time.

### 6.3 Checks on the incoming stream

6.3.1 Confirm the incoming stream's slam-shut is latched open and its impulse line isolation valve is locked open.

6.3.2 Confirm the incoming stream's inlet and outlet valves are fully open.

6.3.3 Read the FLT-HRW-01 differential pressure gauge and confirm it is below 300 mbar.

6.3.4 Compare local outlet gauge readings with the telemetry readings and confirm they agree within 0.05 bar.

6.3.5 Record all readings on the changeover record.

### 6.4 Changing the duty stream

WARNING: Raising a set point too quickly can overshoot the outlet pressure, trip both slam-shuts and cut off the whole MP network. Make every adjustment slowly and in small steps.

6.4.1 Tell the Gas Network Controller the changeover is starting.

6.4.2 Raise the incoming stream's set point in steps of no more than 0.02 bar, letting the outlet pressure settle after each step, until it reaches 1.60 bar.

6.4.3 Confirm the incoming stream is now passing gas, shown by its regulator position indicator and a temperature drop on its outlet pipework.

6.4.4 Lower the outgoing stream's set point in steps of no more than 0.02 bar until it reaches 1.50 bar.

6.4.5 Watch the outlet pressure for 15 minutes and confirm it is steady at 1.60 bar within tolerance.

6.4.6 Ask the Gas Network Controller to confirm stable telemetry readings, then change the duty and standby labels on the stream boards.

### 6.5 Isolating a stream for maintenance

WARNING: Never isolate a stream until the other stream is proven to be carrying the full load. Losing both streams cuts off supply to the MP network and every customer downstream.

6.5.1 Close the outlet valve of the stream to be isolated slowly, then close its inlet valve.

6.5.2 Lock and tag both valves with the permit number.

6.5.3 Vent the isolated stream to zero through its vent valve and vent stack.

6.5.4 Close the vent valve and watch the stream gauge for 10 minutes with no pressure rise.

6.5.5 Before breaking containment on the IP section of the stream, fit a spade at the inlet valve flange, because PR-GAS-021 requires positive isolation for IP plant.

HOLD POINT: Do not break containment until the Authorised Person (Gas) has witnessed the proving test and signed the isolation certificate.

### 6.6 Returning a stream to standby

6.6.1 Confirm the maintenance work has been handed back under PR-GAS-021 and the Authorised Person (Gas) has authorised de-isolation.

6.6.2 If containment was broken, purge the stream to gas through its vent valve and vent stack, then open the inlet valve slowly to pressurise the stream up to the closed slam-shut.

6.6.3 Equalise pressure across the slam-shut using its reset bypass, reset it, and confirm it is latched open.

6.6.4 Test all disturbed joints at operating pressure with leak detection fluid.

6.6.5 Open the outlet valve slowly and set the stream to the standby set point of 1.50 bar.

6.6.6 Watch the outlet pressure for 15 minutes to confirm the duty stream is still in control.

HOLD POINT: Do not leave site until the Authorised Person (Gas) has confirmed the stream is at its standby set point, the slam-shut is latched open and the impulse line isolation valve is locked open.

### 6.7 Unplanned changeover

6.7.1 If telemetry shows a duty stream slam-shut has tripped, or the outlet pressure has fallen to the standby set point, the Gas Network Controller sends the on-call Authorised Person (Gas) and a Competent Person (Pressure Systems) to site.

6.7.2 Confirm on site that the standby stream has taken over and the outlet pressure is steady.

6.7.3 Do not reset a tripped slam-shut until the cause is found; follow PR-GAS-014 for unplanned trips.

6.7.4 Raise the standby stream to the duty set point only when the Authorised Person (Gas) instructs.

6.7.5 Tell the Gas Safety Manager and report the event under PR-CORP-001.

### 6.8 Emergency

6.8.1 If gas escapes uncontrollably in the compound, withdraw everyone outside the fence, keep ignition sources away and tell the Gas Network Controller.

6.8.2 Call 999 for fire or injury.

6.8.3 If both streams are lost, the Gas Network Controller starts the MP network loss-of-supply plan and informs the Gas Safety Manager.

6.8.4 If the Gas Network Controller cannot be reached, call the National Gas Emergency Service on 0800 111 999.

## 7 Records

The changeover record holds the date, streams, set points before and after, filter differential pressure and the roles of those present. Isolation certificates and permits are kept with it in the GPR-HRW asset file for 6 years. The Gas Network Controller logs the time of each changeover and the current duty stream.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2021-08-02 | First issue. |
| 2 | 2025-08-04 | Added 0.02 bar step limit for set point changes after a slam-shut trip during changeover, winter peak exclusion periods, two-person rule and unplanned changeover section. |
