# Harrowmere Energy: the fictional world behind the demo

**Everything in `data/` except the HSE guidance is fictional.** Harrowmere Energy, its sites, assets, people, procedures and records were invented for the GigaWhat demo. Do not use any of it for real operational work.

Harrowmere Energy is a UK multi-utility with two operating business units and a small corporate function:

| Business unit | Code | Runs |
|---|---|---|
| Harrowmere Electricity | `electricity` | A 132/33/11 kV distribution network around the town of Harrowmere and the Vale |
| Harrowmere Gas | `gas` | A gas distribution network from intermediate pressure (7 bar) down to low pressure (75 mbar) |
| Corporate HSE | `shared` | Company-wide procedures that apply to both units |

## Roles

These job titles appear as document owners, approvers and in records. There are no named people.

| Role | Unit |
|---|---|
| Head of Electricity Network Operations | electricity |
| Electricity Safety Manager | electricity |
| Senior Authorised Person (HV) | electricity |
| Authorised Person (HV) | electricity |
| Competent Person (HV) | electricity |
| Control Engineer | electricity |
| Head of Gas Network Operations | gas |
| Gas Safety Manager | gas |
| Authorised Person (Gas) | gas |
| Competent Person (Pressure Systems) | gas |
| First Call Operative | gas |
| Gas Network Controller | gas |
| Head of Health, Safety and Environment | shared |
| Chief Operating Officer | shared |

An **Authorised Person** issues permits and releases safety-critical work. A **Competent Person** does the work under a permit. Control Engineers (electricity) and Gas Network Controllers (gas) run the control room.

UK gas pressure tiers used throughout: low pressure (LP) up to 75 mbar, medium pressure (MP) 75 mbar to 2 bar, intermediate pressure (IP) 2 to 7 bar.

## Sites and assets

### Electricity

| Site ID | Site | Voltage | Assets |
|---|---|---|---|
| `ESS-RVL` | Riverside Lane Grid Substation | 132/33 kV | `GT-1`, `GT-2` grid transformers (90 MVA, 1987 and 1991); `SWG-RVL-33` 33 kV switchboard; `BAT-RVL` 110 V battery |
| `ESS-ASH` | Ashford Road Primary Substation | 33/11 kV | `T-104`, `T-105` primary transformers (24 MVA, ONAN/ONAF, 1979 and 2004); `SWG-ASH-11` 11 kV switchboard (vacuum circuit breakers, 2012); `FDR-ASH-07` 11 kV feeder Ashford Road to Kingsmead; `FDR-ASH-09` 11 kV feeder Ashford Road to Orchard Way; `BAT-ASH` 110 V battery |
| `ESS-KGM` | Kingsmead Primary Substation | 33/11 kV | `T-201`, `T-202` primary transformers (15 MVA, 1996); `SWG-KGM-11` 11 kV switchboard (oil circuit breakers, 1974, due for replacement); `FDR-KGM-03` 11 kV feeder Kingsmead to Brookfield; `BAT-KGM` 110 V battery; `CT-KGM-01` Kingsmead cable tunnel (420 m, a confined space) |
| `ESS-BRK` | Brookfield Secondary Substation | 11 kV/LV | `TX-BRK-01` distribution transformer (1000 kVA); `RMU-BRK-01` ring main unit |
| `ESS-ORC` | Orchard Way Secondary Substation | 11 kV/LV | `TX-ORC-01` distribution transformer (500 kVA); `RMU-ORC-01` ring main unit |
| `DEP-ASH` | Ashford Road Electricity Depot | | none |

### Gas

| Site ID | Site | Pressure | Assets |
|---|---|---|---|
| `GPR-HRW` | Harrowmere Pressure Reduction Station | IP 7 bar to MP 2 bar | `PRS-HRW-01` station (two streams, A and B); `SSV-HRW-A`, `SSV-HRW-B` slam-shut valves; `FLT-HRW-01` filter |
| `GPR-MLN` | Mill Lane District Governor | MP to LP 75 mbar | `G-112` district governor (2006); `SSV-112` slam-shut valve; `FLT-112` filter |
| `GPR-STN` | Station Road District Governor | MP to LP 75 mbar | `G-118` district governor (1998); `SSV-118` slam-shut valve |
| `GPR-KAV` | Kingsmead Avenue District Governor | MP to LP 75 mbar | `G-124` district governor (2015); `SSV-124` slam-shut valve |
| `GNA-HRW` | Harrowmere gas network (mains) | | `MAIN-IP-01` Harrowmere to Vale IP steel main (7 bar, 300 mm, 1968); `MAIN-MP-03` Vale Road MP PE main (2 bar, 180 mm, 2009); `MAIN-LP-17` Mill Lane LP PE main (75 mbar, 125 mm, 2014); `MAIN-LP-22` Station Road LP cast iron main (75 mbar, 6 inch, 1932, on the replacement programme) |
| `DEP-VAL` | Vale Gas Depot | | none |

## Asset classes

`grid_transformer`, `primary_transformer`, `distribution_transformer`, `switchgear`, `ring_main_unit`, `feeder`, `battery`, `cable_tunnel`, `pressure_reduction_station`, `district_governor`, `slam_shut_valve`, `filter`, `main_ip`, `main_mp`, `main_lp`.

## Files

| Path | What |
|---|---|
| `corpus/register.yaml` | The document register: every document, every version, its status and who it applies to. **The register, not the file, decides whether a version is current.** |
| `corpus/procedures/` | Harrowmere procedures as Markdown, one file per version |
| `records/` | Sites, assets, work orders, inspections, incidents and alarms |
| `raw/hse/` | HSE guidance PDFs, downloaded by `gigawhat data fetch-hse` and not committed |

## Deliberate test cases

Some details are planted so the assistant's behaviour can be tested. Don't "fix" them without updating the evaluation set.

| Case | Where | What the assistant should do |
|---|---|---|
| Superseded versions | PR-ELEC-012 v3, PR-GAS-031 v2 | Never cite them for current practice; explain what changed if asked |
| Draft | PR-ELEC-070 v1 | Never use it; say the procedure is not yet approved |
| Withdrawn | PR-GAS-071 v2 | Never use it; point to PR-GAS-003 v8, which absorbed its content |
| Overdue review | PR-ELEC-052 v4 (review due 2026-06-30) | Answer, but say the document is past its review date |
| Conflicting procedures | PR-CORP-004 v3 says HV switching is never done alone; PR-ELEC-001 v6 §6.5.3 allows it with the Control Engineer's agreement | Cite both, say they conflict, refer to the document owners; do not pick one |
| Conflict found while building the evaluation set | PR-GAS-010 v4 §6.4.4 proves a governor isolation over 5 minutes; PR-GAS-021 v5 §6.2.5 requires 10 minutes for MP plant | Same as above. It was not planted; published versions are never edited silently, so it stays until a new version resolves it |
| T-104 acetylene trend | `inspections.csv`, INC-2026-029 | Show the rise through PR-ELEC-044's caution (2 ppm) and action (5 ppm) thresholds |
| G-112 pressure creep | `inspections.csv`, `alarms.csv`, INC-2026-011, INC-2026-027 | Connect the logger readings to both incidents and PR-GAS-058's 5 mbar flag |

Records other than incidents are generated by `scripts/generate_records.py`, which documents each planted pattern.
