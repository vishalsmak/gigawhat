# PR-ELEC-044 Transformer Oil Sampling and Dissolved Gas Analysis

| Field | Value |
|---|---|
| Document ID | PR-ELEC-044 |
| Version | 3 |
| Effective from | 2025-04-01 |
| Review due | 2028-04-01 |
| Owner | Head of Electricity Network Operations |
| Approved by | Senior Authorised Person (HV) |
| Applies to | All Harrowmere Electricity sites: grid, primary and distribution transformers |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how insulating oil samples are taken from transformers, how dissolved gas analysis (DGA) results are interpreted and what action is taken on them, so that developing internal faults are found before they cause failure.

## 2 Scope

This procedure applies to oil-filled transformers with a sampling valve at all Harrowmere Electricity sites: GT-1 and GT-2 (ESS-RVL), T-104 and T-105 (ESS-ASH), T-201 and T-202 (ESS-KGM), TX-BRK-01 (ESS-BRK) and TX-ORC-01 (ESS-ORC).

## 3 References

- PR-ELEC-015 Switching Programmes on the 11 kV and 33 kV Networks
- PR-ELEC-020 Permit-to-Work and Sanction-for-Test (Electrical)
- PR-ELEC-047 Response to Transformer Temperature Alarms
- PR-ELEC-052 Routine Substation Inspection
- PR-CORP-001 Reporting Incidents and Near Misses
- HSE HSG85 Electricity at work: Safe working practices
- Electricity at Work Regulations 1989

## 4 Definitions

DGA: laboratory measurement of the gases dissolved in transformer oil, reported in parts per million (ppm) by volume.

Caution threshold: the gas level at which closer monitoring is needed.

Action threshold: the gas level at which an engineering review and further action are needed.

Designated sampling valve: a ground-level valve, marked with a green label, that can be used with the transformer energised.

## 5 Responsibilities

Senior Authorised Person (HV): leads engineering reviews and decides on load restrictions or removal from service.

Authorised Person (HV): reviews results within five working days of receipt and sets the next sampling date.

Competent Person (HV): takes, labels and dispatches samples.

Control Engineer: applies load restrictions and arranges switching when a transformer must be taken off load.

## 6 Procedure

### 6.1 Sampling intervals and triggers

| Transformers | Routine interval |
|---|---|
| GT-1, GT-2 (grid) | 6 months |
| T-104, T-105, T-201, T-202 (primary) | 12 months |
| TX-BRK-01, TX-ORC-01 (distribution) | 4 years |

6.1.1 Take an additional sample within 24 hours of a Buchholz gas alarm.

6.1.2 Take an additional sample within 7 days of a Stage 2 temperature alarm under PR-ELEC-047 or a through-fault trip.

6.1.3 Sample at the increased frequency set in 6.6 for any transformer above a caution or action threshold.

### 6.2 Preparing to sample

WARNING: Sampling valves that are not designated may be within the safety distance of live connections. Approaching them on an energised transformer risks electric shock or flashover.

6.2.1 Sample an energised transformer only from its designated sampling valve. Otherwise arrange an outage and a Permit-to-Work under PR-ELEC-020.

6.2.2 Inform the Control Engineer before starting and on completion.

6.2.3 Check the oil level gauge. Do not sample if the level is below normal.

6.2.4 Record the top-oil temperature, winding temperature, load and ambient temperature.

6.2.5 Wear nitrile gloves and eye protection, and place a drip tray and spill kit under the valve.

### 6.3 Taking the sample

6.3.1 Remove the valve cap and clean the outlet with a lint-free cloth.

6.3.2 Fit the sampling adaptor, open the valve slowly and flush at least 1 litre of oil into a waste container.

6.3.3 Rinse a 50 ml glass syringe twice with flowing oil, then fill it without drawing in air and close its tap.

6.3.4 Check the syringe for gas bubbles. If any are present, discard the sample and repeat.

6.3.5 Fill a 1 litre amber glass bottle for moisture, acidity and breakdown voltage tests.

6.3.6 Close the valve, refit the cap and check for leaks.

CAUTION: Distribution transformers hold a small oil volume. Taking more than 3 litres can lower the oil level enough to expose live parts inside the tank.

6.3.7 Limit the total oil taken from a distribution transformer to 3 litres, and recheck the oil level gauge.

### 6.4 Labelling and dispatch

6.4.1 Label each container with the asset ID, site ID, date, time, top-oil temperature and reason (routine or triggered).

6.4.2 Pack syringes in the laboratory's protective boxes, out of sunlight.

6.4.3 Dispatch samples within 2 working days. Mark triggered samples URGENT for a 48-hour turnaround.

### 6.5 Interpreting DGA results

| Gas | Caution (ppm) | Action (ppm) | Usual indication |
|---|---|---|---|
| Hydrogen (H2) | 100 | 300 | Partial discharge |
| Methane (CH4) | 120 | 400 | Low-temperature overheating |
| Ethane (C2H6) | 65 | 150 | Low-temperature overheating |
| Ethylene (C2H4) | 50 | 150 | High-temperature overheating |
| Acetylene (C2H2) | 2 | 5 | Arcing |
| Carbon monoxide (CO) | 400 | 800 | Overheating of paper insulation |
| Carbon dioxide (CO2) | 4000 | 10000 | Ageing of paper insulation |

6.5.1 Classify the transformer as normal, caution or action by the highest band reached by any gas.

6.5.2 Treat a gas as one band higher if it has risen by more than 50% since the previous sample and is above half its caution threshold.

6.5.3 Where carbon monoxide is above its caution threshold and the CO2 to CO ratio is below 3, treat the result as action for possible paper overheating.

6.5.4 Report the first appearance of any acetylene to the Senior Authorised Person (HV) on the same day, even below the caution threshold.

### 6.6 Actions on results

6.6.1 Normal: continue at the routine interval.

6.6.2 Caution: resample within 3 months and review the trend. After two consecutive caution results, sample every 3 months.

6.6.3 Action, any gas other than acetylene: take a confirmation sample within 2 weeks. If confirmed, sample monthly and hold an engineering review within 10 working days.

6.6.4 Acetylene above 5 ppm: sample weekly, hold an engineering review within 5 working days and ask the Control Engineer to limit the load to the ONAN rating until the review is complete.

WARNING: A rapid rise in acetylene indicates active arcing inside the tank, which can lead to violent failure and fire.

6.6.5 If acetylene exceeds 15 ppm or rises by more than 3 ppm between samples, refer the transformer at once to the Senior Authorised Person (HV), who decides whether to take it off load under PR-ELEC-015.

6.6.6 Return to the routine interval only after three consecutive stable samples below caution, with Senior Authorised Person (HV) approval.

## 7 Records

- Laboratory results, kept in the transformer condition record for the life of the transformer.
- Sample sheets, including load and temperatures at the time of sampling.
- Engineering review notes and decisions.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2015-04-07 | First issue. |
| 2 | 2021-04-06 | Added oil quality tests and a sampling interval for distribution transformers. |
| 3 | 2025-04-01 | Revised caution and action thresholds. Added the rate-of-rise rule, CO2 to CO ratio check and acetylene escalation. Added sampling after Stage 2 temperature alarms. |
