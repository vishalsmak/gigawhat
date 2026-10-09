# PR-ELEC-047 Response to Transformer Temperature Alarms

| Field | Value |
|---|---|
| Document ID | PR-ELEC-047 |
| Version | 2 |
| Effective from | 2026-01-12 |
| Review due | 2028-01-12 |
| Owner | Head of Electricity Network Operations |
| Approved by | Electricity Safety Manager |
| Applies to | All Harrowmere Electricity sites: grid and primary transformers |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how the control room and site staff respond to top-oil and winding temperature alarms on grid and primary transformers, to prevent insulation damage, oil fires and unplanned loss of supply.

## 2 Scope

This procedure applies to GT-1 and GT-2 at ESS-RVL, T-104 and T-105 at ESS-ASH, and T-201 and T-202 at ESS-KGM. Distribution transformers do not have temperature alarms to SCADA and are not covered.

## 3 References

- PR-ELEC-001 Distribution Safety Rules - Summary for Operational Staff
- PR-ELEC-015 Switching Programmes on the 11 kV and 33 kV Networks
- PR-ELEC-044 Transformer Oil Sampling and Dissolved Gas Analysis
- PR-ELEC-052 Routine Substation Inspection
- PR-ELEC-063 Substation Access, Keys and Visitors
- PR-CORP-001 Reporting Incidents and Near Misses
- HSE HSG85 Electricity at work: Safe working practices
- Electricity at Work Regulations 1989

## 4 Definitions

Top-oil temperature (OTI): the oil temperature at the top of the tank, shown by the oil temperature indicator.

Winding temperature (WTI): the simulated hot-spot temperature of the windings, shown by the winding temperature indicator.

ONAN rating: the load the transformer can carry with natural oil and air cooling, fans off.

ONAF rating: the higher load the transformer can carry with its cooling fans running.

Maximum pointer: the drag pointer on a temperature dial that shows the highest temperature since it was last reset.

## 5 Responsibilities

Senior Authorised Person (HV): decides when a transformer may return to service after being taken off load or tripped on temperature.

Authorised Person (HV): attends site, carries out site and fan checks, and carries out switching.

Competent Person (HV): may carry out site and fan checks under the direction of the Authorised Person (HV).

Control Engineer: responds to alarms, arranges load transfers and takes a transformer off load when this procedure requires it.

## 6 Procedure

### 6.1 Alarm settings and ratings

| Indication | Stage 1 alarm | Stage 2 alarm | Trip |
|---|---|---|---|
| Top-oil temperature (OTI) | 85 °C | 95 °C | 105 °C |
| Winding temperature (WTI) | 105 °C | 120 °C | 135 °C |

NOTE: On ONAN/ONAF transformers the fans start automatically when WTI reaches 75 °C and stop when it falls below 65 °C. For example, primary transformers T-104 and T-105 are rated 12 MVA ONAN and 24 MVA ONAF, so any load above 12 MVA depends on the fans. Check the rating plate and the site rating schedule for each unit.

6.1.1 As Control Engineer, read the ratings and settings for the transformer from the site rating schedule before acting on any alarm.

### 6.2 Control room response to a Stage 1 alarm

6.2.1 Acknowledge the alarm and record the time, OTI, WTI, load, ambient temperature and fan status.

6.2.2 Compare the load with the transformer's ONAN and ONAF ratings.

6.2.3 If the fans are shown as stopped while WTI is above 75 °C, start them by remote control where available.

6.2.4 Check the temperature trend over the previous 2 hours, and the load and temperatures of the other transformer at the site.

6.2.5 Dispatch an Authorised Person (HV) or Competent Person (HV) to arrive at site within 4 hours.

6.2.6 If the temperature is still rising 30 minutes after the alarm, prepare a load transfer under 6.6.

### 6.3 Control room response to a Stage 2 alarm

WARNING: At Stage 2 temperatures the paper insulation ages rapidly and gas bubbles can form in the oil, which can lead to internal flashover, oil fire or transformer failure.

6.3.1 Treat the alarm as urgent and record the readings as in 6.2.1.

6.3.2 Dispatch an Authorised Person (HV) to attend at once, aiming to arrive within 1 hour.

6.3.3 Start a load transfer under 6.6 straight away, to bring the load below the ONAN rating, or below the ONAF rating if the fans are confirmed running.

6.3.4 Inform the Senior Authorised Person (HV).

6.3.5 Take the transformer off load under 6.6 if the temperature is still rising 15 minutes after the load transfer, or comes within 5 °C of the trip setting.

6.3.6 Never inhibit or override a temperature trip.

### 6.4 Site checks

WARNING: An overheating transformer can fail violently. If there is smoke, fire, oil discharge from the pressure relief device or a loud abnormal noise, do not approach. Withdraw, call 999 and inform the Control Engineer.

6.4.1 Inform the Control Engineer on arrival and sign the site log under PR-ELEC-063.

6.4.2 From outside the compound, look for smoke, oil leaks, a raised pressure relief flag or abnormal noise.

6.4.3 Read the local OTI and WTI dials and maximum pointers, and report any difference of more than 5 °C from SCADA.

6.4.4 Do not reset the maximum pointers until their readings have been recorded and reported.

6.4.5 Check the conservator oil level gauge and the Buchholz relay window for gas.

6.4.6 Check that radiator valves are open and that radiators are free of debris, nests or vegetation blocking the airflow.

### 6.5 Cooling fan checks

CAUTION: Fans can start automatically at any time. Keep hands and tools clear of fan guards, and isolate the fan supply at the cooler control cabinet before touching any fan.

6.5.1 Check the cooler control cabinet: fan supply circuit breaker on, selector in AUTO and no fan fault indication.

6.5.2 Switch the selector to MANUAL and check that every fan runs, turns in the right direction and moves air through the radiators.

6.5.3 Reset a tripped fan supply circuit breaker once only. If it trips again, leave it off and report it.

6.5.4 Leave the fans in MANUAL until the temperature has been below the Stage 1 setting for 2 hours, then return to AUTO with the Control Engineer's agreement.

6.5.5 If any fan group is out of service, tell the Control Engineer, who limits the transformer to its ONAN rating until the fans are repaired.

### 6.6 Load transfer and taking a transformer off load

6.6.1 Transfer load by a switching programme under PR-ELEC-015, or by fault switching instructions under PR-ELEC-015 when the alarm is Stage 2.

6.6.2 Before transferring load, confirm that the receiving transformer or feeders can carry it within their ratings.

6.6.3 At a two-transformer site such as ESS-ASH, move 11 kV load to adjacent primaries through normally open points, such as FDR-ASH-07 to ESS-KGM, rather than overloading the remaining transformer.

6.6.4 Take the transformer off load if the conditions in 6.3.5 are met, if OTI reaches 100 °C or WTI 130 °C, if a Buchholz alarm occurs with a temperature alarm, or if site staff report smoke, oil discharge or abnormal noise.

6.6.5 Do not delay taking a transformer off load to avoid interrupting customers.

HOLD POINT: A transformer taken off load or tripped on temperature must not be re-energised until the Senior Authorised Person (HV) has reviewed the event, the site checks in 6.4 are complete and an oil sample has been taken for DGA under PR-ELEC-044.

6.6.6 Re-energise only on the instruction of the Control Engineer, following a switching programme under PR-ELEC-015.

### 6.7 After the alarm and emergencies

6.7.1 After any Stage 2 alarm, take an oil sample for DGA within 7 days under PR-ELEC-044, even if the transformer did not trip.

6.7.2 Record the event and the maximum pointer readings in the transformer condition record, then reset the pointers.

6.7.3 Raise defects for faulty fans, indicators or radiators, and report any trip or damage under PR-CORP-001.

6.7.4 If there is a fire or anyone is injured, call 999, keep everyone clear and inform the Control Engineer, who isolates the transformer remotely.

6.7.5 Ask members of the public who report a power cut to call 105.

## 7 Records

- Control log entries for each alarm, with readings and actions.
- Transformer condition record, including maximum pointer readings and fan defects.
- Senior Authorised Person (HV) review notes for any transformer taken off load or tripped.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2022-10-03 | First issue. |
| 2 | 2026-01-12 | Added Stage 2 load transfer timescales and the conditions for taking a transformer off load. Added cooling fan checks and the hold point before re-energisation. Aligned DGA sampling after Stage 2 alarms with PR-ELEC-044 v3 and switching with PR-ELEC-015 v5. |
