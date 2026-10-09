# PR-ELEC-058 Substation Battery Maintenance

| Field | Value |
|---|---|
| Document ID | PR-ELEC-058 |
| Version | 2 |
| Effective from | 2025-02-03 |
| Review due | 2028-02-03 |
| Owner | Head of Electricity Network Operations |
| Approved by | Senior Authorised Person (HV) |
| Applies to | All Harrowmere Electricity sites: substation batteries |

FICTIONAL DOCUMENT. Created for the GigaWhat demo. Not for real operational use.

## 1 Purpose

This procedure sets out how the 110 V substation batteries and their chargers are maintained and tested, so that the DC supply for protection, tripping and closing is always available.

## 2 Scope

This procedure applies to BAT-RVL (ESS-RVL), BAT-ASH (ESS-ASH) and BAT-KGM (ESS-KGM). Each is a 110 V nominal lead-acid battery of 55 cells. BAT-RVL and BAT-ASH are valve-regulated (VRLA). BAT-KGM is a vented type with accessible electrolyte.

## 3 References

- PR-ELEC-001 Distribution Safety Rules - Summary for Operational Staff
- PR-ELEC-020 Permit-to-Work and Sanction-for-Test (Electrical)
- PR-ELEC-052 Routine Substation Inspection
- PR-CORP-001 Reporting Incidents and Near Misses
- HSE HSG85 Electricity at work: Safe working practices
- Electricity at Work Regulations 1989
- Management of Health and Safety at Work Regulations 1999

## 4 Definitions

Float voltage: the voltage the charger holds the battery at in normal service.

Discharge test: a test that discharges the battery through a load bank to measure its capacity.

Impedance test: a measurement of each cell's internal impedance, compared with its baseline to detect deterioration.

## 5 Responsibilities

Senior Authorised Person (HV): approves battery replacement and temporary battery arrangements.

Authorised Person (HV): plans maintenance, makes sure the DC supply is maintained and reviews results.

Competent Person (HV): carries out the checks and tests.

Control Engineer: is informed before and after work and responds to DC alarms.

## 6 Procedure

### 6.1 Maintenance intervals

| Task | Interval |
|---|---|
| Float voltage and charger alarms | Monthly, during inspection under PR-ELEC-052 |
| Cell voltages, electrolyte, connections | Quarterly |
| Impedance and connection resistance tests | Annually |
| Discharge test | Every 4 years, or annually once capacity is below 90% |

### 6.2 Safety precautions

WARNING: A 110 V substation battery can deliver thousands of amperes into a short circuit, causing severe burns and explosive arcing. Batteries also give off hydrogen, which can explode if ignited.

6.2.1 Remove watches, rings and other metal jewellery, and use insulated tools only.

6.2.2 Wear a face visor, acid-resistant gloves and an apron when working on vented cells, and check an eyewash station is available.

6.2.3 Check the battery room ventilation is working. Do not smoke, use naked flames or make sparks in the room.

6.2.4 Never place tools or other objects on top of cells.

6.2.5 Inform the Control Engineer before starting and when finished.

### 6.3 Quarterly checks

6.3.1 Record the charger output voltage and current. The float voltage should be between 123 V and 125 V.

6.3.2 Measure each cell voltage. Report any cell below 2.18 V, above 2.35 V or more than 0.05 V from the battery average.

6.3.3 On BAT-KGM, check electrolyte levels are between the marks, top up with deionised water only, and measure pilot cell specific gravity, which should not be below 1.200 at 20 °C.

6.3.4 On BAT-RVL and BAT-ASH, check for swollen, cracked or leaking cases, and report any cell more than 5 °C above room temperature.

6.3.5 Clean any corrosion from terminals and connectors, and apply a thin coat of petroleum jelly.

6.3.6 Check the DC earth fault monitor shows no earth fault.

6.3.7 With the Control Engineer's agreement, switch off the charger AC supply for no more than 5 minutes to confirm the charger fail alarm reaches the control room.

### 6.4 Annual checks

6.4.1 Measure the internal impedance of each cell. Report any cell more than 25% above its baseline.

6.4.2 Measure intercell connection resistance and retighten any connection more than 20% above the battery average.

6.4.3 On BAT-KGM, measure the specific gravity of every cell.

6.4.4 Check the charger voltage and current limit settings against the charger label.

### 6.5 Discharge test

WARNING: While the station battery is disconnected, circuit breakers at the site may not trip on a fault unless a temporary battery is connected.

6.5.1 Connect a temporary 110 V battery to the DC distribution board and confirm the board voltage before disconnecting the station battery.

HOLD POINT: The Authorised Person (HV) must confirm the temporary battery is connected and supplying the board before the station battery is disconnected.

6.5.2 Discharge the station battery through the load bank at its 3-hour rate until it reaches 99 V (1.80 V per cell).

6.5.3 Record the time taken and calculate the capacity as a percentage of rated capacity, corrected for temperature.

6.5.4 Recharge the station battery, reconnect it, confirm the float voltage and then remove the temporary battery.

6.5.5 Replace the battery if capacity is below 80%, with Senior Authorised Person (HV) approval.

### 6.6 Alarms, defects and spills

6.6.1 As Control Engineer, on a charger fail alarm, send a Competent Person (HV) to arrive within 4 hours. The battery supports the DC load for at least 8 hours.

6.6.2 On a DC low volts alarm (105 V), send staff at once and avoid switching at that site until the supply is restored.

6.6.3 On a DC earth fault alarm, investigate within 24 hours, because a second earth fault can cause unwanted tripping or prevent tripping.

6.6.4 Neutralise electrolyte spills with the sodium bicarbonate spill kit. If acid enters an eye, irrigate at the eyewash for at least 15 minutes and call 999.

6.6.5 Report injuries and near misses under PR-CORP-001.

## 7 Records

- Battery test sheets, kept for the life of the battery plus six years.
- Discharge test results and capacity trend.
- Defect records in the works management system.

## 8 Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 2021-02-01 | First issue, combining the battery instructions for ESS-RVL, ESS-ASH and ESS-KGM. |
| 2 | 2025-02-03 | Added VRLA cell temperature checks, impedance testing and capacity-based discharge test frequency. Required a temporary battery during discharge tests. |
