# PR-ELEC-075 Fault Restoration on 11 kV Feeders

| Field | Value |
|---|---|
| Document ID | PR-ELEC-075 |
| Version | 3 |
| Effective from | 2025-09-01 |
| Review due | 2028-09-01 |
| Owner | Head of Electricity Network Operations |
| Approved by | Electricity Safety Manager |
| Applies to | All Harrowmere Electricity sites: 11 kV feeders, switchgear and ring main units |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how supplies are restored safely after a fault trip on an 11 kV feeder, how the faulted section is found and isolated, and how the network is returned to normal.

## 2 Scope

This procedure applies to 11 kV feeders, switchgear and ring main units at all Harrowmere Electricity sites, including FDR-ASH-07 and FDR-ASH-09 from SWG-ASH-11, FDR-KGM-03 from SWG-KGM-11, and RMU-BRK-01 and RMU-ORC-01. The Harrowmere 11 kV feeders are underground cable and have no auto-reclose.

## 3 References

- PR-ELEC-001 Distribution Safety Rules - Summary for Operational Staff
- PR-ELEC-012 Isolation and Earthing of 11 kV Circuits
- PR-ELEC-015 Switching Programmes on the 11 kV and 33 kV Networks
- PR-ELEC-020 Permit-to-Work and Sanction-for-Test (Electrical)
- PR-ELEC-063 Substation Access, Keys and Visitors
- PR-CORP-001 Reporting Incidents and Near Misses
- PR-CORP-004 Lone Working
- HSE HSG85 Electricity at work: Safe working practices
- Electricity Safety, Quality and Continuity Regulations 2002

## 4 Definitions

Test close: a single attempt to re-energise a tripped feeder by closing its circuit breaker.

Fault passage indicator (FPI): a device at a ring main unit that shows whether fault current has passed through it.

Sectionalising: opening switches along a feeder to separate the faulted section from healthy sections.

Normally open point: a switch kept open between feeders that can be closed to supply a section from another feeder.

## 5 Responsibilities

Senior Authorised Person (HV): approves any departure from the test close rules and reviews faults involving third-party damage.

Authorised Person (HV): attends site, carries out switching, isolation and earthing, and issues permits for repair.

Competent Person (HV): reads fault passage indicators and carries out repairs under a permit.

Control Engineer: leads the response, decides on any test close, instructs switching and records every operation.

## 6 Procedure

### 6.1 Initial response by the Control Engineer

6.1.1 Acknowledge the trip alarm and record the time, circuit breaker, feeder and protection flags shown on SCADA.

6.1.2 Check for reports of third-party damage, injury, fire or exposed conductors from 105 calls, the emergency services or staff.

6.1.3 Check whether any permit or other work is in force on or near the feeder, and whether anyone is known to be digging near the cable route.

6.1.4 Identify the customers affected, including those on the Priority Services Register, and the alternative feeds through normally open points.

6.1.5 Send an Authorised Person (HV) to the source substation and, where needed, a Competent Person (HV) to the ring main units along the feeder.

### 6.2 Test closing

WARNING: Closing a circuit breaker onto a cable damaged by excavation can kill anyone at the dig site. Never test close if there is any report of third-party damage or anyone working on or near the cable route.

6.2.1 Make no more than one test close on a tripped 11 kV feeder, and only from the control room.

6.2.2 Test close only when no damage has been reported, no work is in progress on or near the feeder and at least 5 minutes have passed since the trip.

6.2.3 Do not test close any circuit breaker on SWG-KGM-11, including FDR-KGM-03. Its oil circuit breakers must be inspected on site after a fault trip before they are closed again.

6.2.4 If the test close trips, treat the feeder as having a permanent fault and do not close the source circuit breaker again until the faulted section has been isolated.

6.2.5 Record the decision and the result in the control log.

### 6.3 Site attendance and safety

WARNING: Switchgear that has cleared a fault may be damaged. If there is smoke, a smell of burning, oil on the floor or abnormal noise, do not enter the switchroom.

6.3.1 On arrival, inform the Control Engineer and sign the site log under PR-ELEC-063.

6.3.2 Check the switchroom from the doorway before entering, and withdraw and report if there are signs of damage.

6.3.3 Record the protection relay flags and reset them only when the Control Engineer instructs.

6.3.4 On SWG-KGM-11, check the oil level and look for oil discharge on the tripped circuit breaker before reporting it fit to close.

6.3.5 If working alone at night, follow PR-CORP-004 and check in with the Control Engineer at least every 30 minutes.

### 6.4 Locating the faulted section

6.4.1 Visit each ring main unit along the feeder, read and record its fault passage indicators, and report them to the Control Engineer.

6.4.2 Identify the faulted section as lying between the last ring main unit whose indicator has operated and the first whose indicator has not.

NOTE: Fault passage indicators can give misleading readings on some earth faults. Treat them as a guide and confirm by sectionalising.

6.4.3 Where indicators are not fitted or are unclear, sectionalise by opening a switch near the middle of the feeder and energising each half in turn under the Control Engineer's instruction.

6.4.4 Reset the fault passage indicators when the Control Engineer instructs.

### 6.5 Restoring healthy sections

6.5.1 As Control Engineer, issue fault switching instructions under PR-ELEC-015 to open the ring main unit switches either side of the faulted section.

6.5.2 Lock the open switches either side of the faulted section and fix Danger notices.

6.5.3 Restore the section nearest the source by closing the source circuit breaker.

6.5.4 Before closing a normally open point to restore the remaining sections, confirm the receiving feeder can carry the extra load.

6.5.5 Restore the remaining healthy sections by closing the normally open point.

6.5.6 If customers will be without supply for more than 3 hours, inform the Head of Electricity Network Operations so that mobile generation can be arranged.

### 6.6 Isolating the faulted section for repair

HOLD POINT: Excavation or repair on the faulted cable must not start until the section has been isolated, proved dead and earthed under PR-ELEC-012, and an Authorised Person (HV) has issued a Permit-to-Work under PR-ELEC-020.

6.6.1 Prepare a written switching programme under PR-ELEC-015 for the isolation.

6.6.2 Locate the fault position with cable fault location equipment under a Sanction-for-Test.

6.6.3 Identify and spike the cable at the dig site before cutting, as required by PR-ELEC-012.

### 6.7 Returning to normal running

6.7.1 After repair and testing, clear and cancel the permit and remove the earths under PR-ELEC-012.

6.7.2 Restore the normal running arrangement using a switching programme under PR-ELEC-015.

6.7.3 As Control Engineer, update the network diagram and close the fault record.

6.7.4 Report any fault involving third-party damage, injury or switchgear failure under PR-CORP-001.

### 6.8 Emergency and public safety

6.8.1 Call 999 for any injury or fire, then inform the Control Engineer.

6.8.2 Where conductors are exposed or a cable is damaged, keep the public at least 5 m away and guard the area until it is made safe.

6.8.3 Ask members of the public who report a power cut or damaged power lines to call 105.

## 7 Records

- Control log entries for the trip, any test close and every switching operation.
- Fault passage indicator readings and the fault record.
- Switching programmes and permits, kept under PR-ELEC-015 and PR-ELEC-020.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2016-09-05 | First issue. |
| 2 | 2022-03-07 | Added the use of fault passage indicators and sectionalising. |
| 3 | 2025-09-01 | Limited test closes to one, from the control room only. Prohibited test closing on SWG-KGM-11. Added a check for third-party damage before any test close and Priority Services Register customers. |
