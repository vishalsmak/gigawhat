"""Generate the fictional work orders, inspections and alarms in data/records.

Seeded, so every run writes identical files. Most rows are routine. A few patterns are planted on
purpose, each matching a threshold in the procedures and dated from incidents.yaml, so demo
questions about them have real evidence behind them:

- T-104 acetylene rises through the caution (2 ppm) and action (5 ppm) thresholds in PR-ELEC-044,
  crosses action at INC-2026-029, then is sampled weekly as PR-ELEC-044 6.6.4 requires.
- T-104 raises top-oil Stage 1 alarms (85 °C, PR-ELEC-047) in the July 2026 heatwave, and a
  Stage 2 alarm (95 °C) when its cooling fans fail at INC-2026-022.
- G-112's logged maximum outlet pressure creeps past PR-GAS-058's flag (set point + 5 mbar)
  before the SSV-112 over-pressure trip at INC-2026-011, and again before INC-2026-027.
- BAT-ASH has cells below PR-ELEC-058's 2.18 V limit at INC-2025-008.
- GPR-HRW odorant falls below PR-GAS-066's 5.0 mg/m3 at INC-2026-019.
- SWG-KGM-11, 1974 oil switchgear, collects defects and fails to trip at INC-2024-007.

Usage: uv run python scripts/generate_records.py
"""

import csv
import json
import math
import random
from collections.abc import Callable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

SEED = 20261009
START = date(2024, 10, 1)
END = date(2026, 10, 8)
LONDON = ZoneInfo("Europe/London")
RECORDS_DIR = Path(__file__).resolve().parent.parent / "data" / "records"

HV_INSPECTOR = "Competent Person (HV)"
GAS_INSPECTOR = "Competent Person (Pressure Systems)"

# Thresholds copied from the procedures named beside them.
OTI_STAGE_1_C = 85  # PR-ELEC-047
OTI_STAGE_2_C = 95  # PR-ELEC-047
GOVERNOR_SET_POINTS_MBAR = {"G-112": 35.0, "G-118": 30.0, "G-124": 40.0}  # PR-GAS-010
LOGGER_FLAG_MARGIN_MBAR = 5.0  # PR-GAS-058 6.4.3
TELEMETRY_HIGH_MARGIN_MBAR = 8.0
OPSO_TRIPS_MBAR = {"SSV-112": 60.0, "SSV-118": 55.0, "SSV-124": 63.0}  # PR-GAS-014
ODORANT_NORMAL_MG_M3 = (5.0, 10.0)  # PR-GAS-066
MIN_CELL_VOLTS = 2.18  # PR-ELEC-058

REQUIRED_INCIDENTS = (
    "INC-2024-007",
    "INC-2025-008",
    "INC-2025-019",
    "INC-2025-040",
    "INC-2026-011",
    "INC-2026-019",
    "INC-2026-022",
    "INC-2026-027",
    "INC-2026-029",
)


@dataclass(frozen=True)
class Asset:
    asset_id: str
    site_id: str
    asset_class: str


@dataclass(frozen=True)
class Inspection:
    asset_id: str
    inspected_on: date
    inspection_type: str
    inspector_role: str
    outcome: str
    findings: str
    readings: Mapping[str, float | str]


@dataclass(frozen=True)
class WorkOrder:
    asset_id: str
    work_type: str
    title: str
    status: str
    priority: int
    raised_on: date
    due_on: date
    completed_on: date | None
    notes: str = ""


@dataclass(frozen=True)
class Alarm:
    asset_id: str
    raised_at: datetime
    cleared_at: datetime | None
    priority: int
    code: str
    message: str
    value: float | None = None
    unit: str = ""


@dataclass
class Records:
    inspections: list[Inspection] = field(default_factory=list)
    work_orders: list[WorkOrder] = field(default_factory=list)
    alarms: list[Alarm] = field(default_factory=list)


def main() -> None:
    rng = random.Random(SEED)
    assets = read_assets()
    incidents = read_incident_times()
    records = Records()
    for asset in assets:
        inspect = INSPECTORS.get(asset.asset_class)
        if inspect:
            records.inspections.extend(inspect(asset, rng, incidents))
    records.alarms.extend(transformer_alarms(assets, rng, incidents))
    records.alarms.extend(network_alarms(rng, incidents))
    records.work_orders.extend(planned_work_orders(assets, rng))
    records.work_orders.extend(defect_work_orders(records.inspections, rng))
    records.work_orders.extend(incident_work_orders(incidents))
    write_records(records)


# ---------------------------------------------------------------------------------- inputs


def read_assets() -> list[Asset]:
    with (RECORDS_DIR / "assets.csv").open(newline="") as handle:
        return [
            Asset(row["asset_id"], row["site_id"], row["asset_class"])
            for row in csv.DictReader(handle)
        ]


def read_incident_times() -> dict[str, datetime]:
    rows = yaml.safe_load((RECORDS_DIR / "incidents.yaml").read_text())["incidents"]
    times = {row["incident_id"]: row["occurred_at"] for row in rows}
    missing = [incident for incident in REQUIRED_INCIDENTS if incident not in times]
    if missing:
        raise SystemExit(f"incidents.yaml is missing planted incidents: {', '.join(missing)}")
    return times


# ------------------------------------------------------------------------------ calendars


def monthly(day_of_month: int, every_months: int = 1) -> Iterator[date]:
    year, month = START.year, START.month
    while (current := date(year, month, day_of_month)) <= END:
        if current >= START:
            yield current
        month += every_months
        year, month = year + (month - 1) // 12, (month - 1) % 12 + 1


def ambient_c(day: date) -> float:
    """Daily maximum air temperature: a UK seasonal curve plus the two summer heatwaves."""
    seasonal = 13.5 + 8.5 * math.sin(2 * math.pi * (day.timetuple().tm_yday - 110) / 365)
    heatwave = 9.0 if date(2025, 7, 10) <= day <= date(2025, 7, 16) else 0.0
    if date(2026, 7, 13) <= day <= date(2026, 7, 24):
        heatwave = 11.0
    return seasonal + heatwave


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=LONDON)


def between(first: date, last: date, day: date) -> bool:
    return first <= day <= last


# ------------------------------------------------------------------------ transformers


def transformer_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    for day in monthly(rng.randint(3, 12)):
        top_oil_max = round(ambient_c(day) + rng.uniform(38, 46) + aging_offset_c(asset), 1)
        breather_spent = rng.random() < 0.06
        yield Inspection(
            asset.asset_id,
            day,
            "routine_visual",
            HV_INSPECTOR,
            "defects_found" if breather_spent else "satisfactory",
            "Silica gel breather more than two-thirds discoloured; replacement requested."
            if breather_spent
            else "Oil level normal, no leaks, gauges and maximum pointers read and reset.",
            {"top_oil_max_pointer_c": min(top_oil_max, OTI_STAGE_2_C - 1), "oil_level": "normal"},
        )
    yield from dga_samples(asset, rng, incidents)


# Top-oil rise above ambient at typical summer peak load.
TOP_OIL_RISE_C = {"primary_transformer": 49.0, "grid_transformer": 42.0}


def aging_offset_c(asset: Asset) -> float:
    return 4.0 if asset.asset_id == "T-104" else 0.0


def dga_samples(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    acetylene = t104_acetylene_ppm(incidents) if asset.asset_id == "T-104" else {}
    quarterly = {day: 0.0 for day in monthly(20, every_months=3)}
    for day, c2h2 in sorted((quarterly | acetylene).items()):
        readings = baseline_gases_ppm(rng) | {"acetylene": c2h2}
        if c2h2 > 0:
            readings["hydrogen"] = round(readings["hydrogen"] + 9 * c2h2, 1)
            readings["ethylene"] = round(readings["ethylene"] + 2.2 * c2h2, 1)
        outcome, findings = interpret_dga(c2h2)
        yield Inspection(
            asset.asset_id, day, "oil_sample_dga", HV_INSPECTOR, outcome, findings, readings
        )


def t104_acetylene_ppm(incidents: dict[str, datetime]) -> dict[date, float]:
    """Arcing that starts in 2025 and accelerates after the July 2026 Stage 2 alarm."""
    stage_2 = incidents["INC-2026-022"].date()
    action = incidents["INC-2026-029"].date()
    trend = {
        date(2025, 4, 20): 0.4,
        date(2025, 7, 20): 0.6,
        date(2025, 10, 20): 0.9,
        date(2026, 1, 20): 1.4,
        date(2026, 4, 20): 2.6,
        stage_2 + timedelta(days=5): 4.1,
        date(2026, 8, 19): 4.6,
        action: 5.8,
    }
    for week, ppm in enumerate((6.1, 6.5, 6.9), start=1):
        if (sample := action + timedelta(weeks=week)) <= END:
            trend[sample] = ppm
    return trend


def baseline_gases_ppm(rng: random.Random) -> dict[str, float]:
    return {
        "hydrogen": round(rng.uniform(12, 30), 1),
        "methane": round(rng.uniform(8, 22), 1),
        "ethane": round(rng.uniform(4, 15), 1),
        "ethylene": round(rng.uniform(3, 12), 1),
        "carbon_monoxide": round(rng.uniform(180, 320)),
        "carbon_dioxide": round(rng.uniform(1600, 2900)),
    }


def interpret_dga(acetylene_ppm: float) -> tuple[str, str]:
    if acetylene_ppm >= 5:
        return "unsatisfactory", (
            f"Acetylene {acetylene_ppm} ppm, above the 5 ppm action threshold (PR-ELEC-044). "
            "Weekly sampling, engineering review and ONAN load limit required."
        )
    if acetylene_ppm >= 2:
        return "defects_found", (
            f"Acetylene {acetylene_ppm} ppm, above the 2 ppm caution threshold (PR-ELEC-044). "
            "Increased sampling and trend review."
        )
    if acetylene_ppm > 0:
        return "satisfactory", (
            f"Acetylene detected at {acetylene_ppm} ppm, below caution. Reported to Senior "
            "Authorised Person (HV) as first appearance or continued presence."
        )
    return "satisfactory", "All dissolved gases below caution thresholds."


def transformer_alarms(
    assets: list[Asset], rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Alarm]:
    fan_failure = incidents["INC-2026-022"]
    for asset in assets:
        if asset.asset_class not in {"grid_transformer", "primary_transformer"}:
            continue
        day = START
        while day <= END:
            rise = TOP_OIL_RISE_C[asset.asset_class] + aging_offset_c(asset)
            top_oil = ambient_c(day) + rise + rng.uniform(-3, 3)
            if top_oil >= OTI_STAGE_1_C and day != fan_failure.date():
                raised = at(day, rng.randint(14, 17), rng.randint(0, 59))
                yield Alarm(
                    asset.asset_id,
                    raised,
                    raised + timedelta(minutes=rng.randint(40, 200)),
                    2,
                    "OTI_STAGE_1",
                    "Top-oil temperature Stage 1",
                    round(min(top_oil, OTI_STAGE_2_C - 0.5), 1),
                    "°C",
                )
            day += timedelta(days=1)
    yield Alarm(
        "T-104",
        fan_failure,
        fan_failure + timedelta(hours=3, minutes=10),
        1,
        "OTI_STAGE_2",
        "Top-oil temperature Stage 2: cooling fan bank 2 not running",
        96.5,
        "°C",
    )


# ----------------------------------------------------------------- other electrical assets


def switchgear_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    old_oil_switchgear = asset.asset_id == "SWG-KGM-11"
    for day in monthly(rng.randint(3, 12), every_months=3):
        discharge_db = round(rng.uniform(18, 34) if old_oil_switchgear else rng.uniform(2, 9), 1)
        defective = old_oil_switchgear and discharge_db > 26
        yield Inspection(
            asset.asset_id,
            day,
            "routine_visual",
            HV_INSPECTOR,
            "defects_found" if defective else "satisfactory",
            f"Partial discharge {discharge_db} dB TEV on panel 3; oil weep at a breaker tank seal."
            if defective
            else "No discharge activity of concern, panels clean, interlocks and labels correct.",
            {"tev_max_db": discharge_db},
        )
    failed_test = incidents["INC-2024-007"].date()
    yield Inspection(
        asset.asset_id,
        failed_test,
        "protection_test",
        HV_INSPECTOR,
        "unsatisfactory" if old_oil_switchgear else "satisfactory",
        "Circuit breaker on panel 5 failed to trip on secondary injection test."
        if old_oil_switchgear
        else "All circuit breakers tripped within time on secondary injection.",
        {"slowest_trip_ms": 999.0 if old_oil_switchgear else round(rng.uniform(55, 80))},
    )


def battery_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    weak_cells_found = incidents["INC-2025-008"].date()
    for day in monthly(rng.randint(3, 12)):
        lowest_cell = round(rng.uniform(2.20, 2.26), 3)
        if asset.asset_id == "BAT-ASH" and between(weak_cells_found, weak_cells_found, day):
            lowest_cell = 2.11
        weak = lowest_cell < MIN_CELL_VOLTS
        yield Inspection(
            asset.asset_id,
            day,
            "battery_check",
            HV_INSPECTOR,
            "defects_found" if weak else "satisfactory",
            f"Cells 17 and 41 at {lowest_cell} V and 2.14 V, below 2.18 V (PR-ELEC-058)."
            if weak
            else "Float voltage within 123 to 125 V; all cells within limits.",
            {"float_volts": round(rng.uniform(123.3, 124.7), 1), "lowest_cell_volts": lowest_cell},
        )
    if asset.asset_id == "BAT-ASH":
        yield Inspection(
            asset.asset_id,
            weak_cells_found,
            "battery_check",
            HV_INSPECTOR,
            "defects_found",
            "Cells 17 and 41 at 2.11 V and 2.14 V, below 2.18 V (PR-ELEC-058).",
            {"float_volts": 123.6, "lowest_cell_volts": 2.11},
        )


def secondary_substation_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    for day in monthly(rng.randint(3, 12), every_months=3):
        yield Inspection(
            asset.asset_id,
            day,
            "routine_visual",
            HV_INSPECTOR,
            "satisfactory",
            "No damage, oil level normal, enclosure secure.",
            {},
        )


def tunnel_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    for day in monthly(rng.randint(3, 12)):
        yield Inspection(
            asset.asset_id,
            day,
            "shaft_head_visual",
            HV_INSPECTOR,
            "satisfactory",
            "Shaft covers locked, fixed fan running, gas detector healthy at surface panel.",
            {"oxygen_pct": round(rng.uniform(20.7, 20.9), 1), "flammable_pct_lel": 0.0},
        )


# --------------------------------------------------------------------------- gas network


def governor_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    set_point = GOVERNOR_SET_POINTS_MBAR[asset.asset_id]
    for day in monthly(rng.randint(3, 12)):
        logged_max = round(
            set_point + rng.uniform(1.5, 3.5) + g112_creep_mbar(asset, day, incidents), 1
        )
        creeping = logged_max > set_point + LOGGER_FLAG_MARGIN_MBAR
        yield Inspection(
            asset.asset_id,
            day,
            "monthly_pressure_check",
            GAS_INSPECTOR,
            "defects_found" if creeping else "satisfactory",
            f"Logger maximum outlet {logged_max} mbar, more than 5 mbar above the "
            f"{set_point:g} mbar set point (PR-GAS-058 6.4.3). Overnight creep suspected."
            if creeping
            else "Outlet pressure steady at set point; slam-shut open and latched.",
            {
                "inlet_bar": round(rng.uniform(1.78, 1.92), 2),
                "outlet_mbar": round(set_point + rng.uniform(-0.6, 0.6), 1),
                "logger_max_outlet_mbar": logged_max,
                "logger_min_outlet_mbar": round(set_point - rng.uniform(2, 5), 1),
            },
        )


def g112_creep_mbar(asset: Asset, day: date, incidents: dict[str, datetime]) -> float:
    """Creep that builds before the March 2026 trip, is cured by the seat repair, then returns."""
    if asset.asset_id != "G-112":
        return 0.0
    trip = incidents["INC-2026-011"].date()
    recurrence = incidents["INC-2026-027"].date()
    if between(trip - timedelta(days=75), trip, day):
        return 6.0 + 4.0 * (75 - (trip - day).days) / 75
    if between(recurrence - timedelta(days=45), END, day):
        return 5.5 + 3.0 * min((day - recurrence).days + 45, 90) / 90
    return 0.0


def slam_shut_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    if asset.asset_id not in OPSO_TRIPS_MBAR:
        yield from station_slam_shut_tests(asset, rng)
        return
    for day in monthly(rng.randint(3, 12), every_months=12):
        yield Inspection(
            asset.asset_id,
            day,
            "function_test",
            GAS_INSPECTOR,
            "satisfactory",
            "Both trips within tolerance (PR-GAS-014). Valve reset and latched.",
            {
                "opso_trip_mbar": round(
                    OPSO_TRIPS_MBAR[asset.asset_id] + rng.uniform(-1.5, 1.5), 1
                ),
                "upso_trip_mbar": round(12 + rng.uniform(-1, 1), 1),
            },
        )


def station_slam_shut_tests(asset: Asset, rng: random.Random) -> Iterator[Inspection]:
    for day in monthly(rng.randint(3, 12), every_months=6):
        yield Inspection(
            asset.asset_id,
            day,
            "function_test",
            GAS_INSPECTOR,
            "satisfactory",
            "Standby stream slam-shut tripped within 1.90 bar plus or minus 0.04 bar (PR-GAS-014).",
            {"opso_trip_bar": round(1.90 + rng.uniform(-0.03, 0.03), 2)},
        )


def station_inspections(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    low_odorant = incidents["INC-2026-019"].date()
    for day in [*monthly(rng.randint(3, 12)), low_odorant]:
        odorant = round(rng.uniform(5.8, 8.6), 1) if day != low_odorant else 3.9
        low = odorant < ODORANT_NORMAL_MG_M3[0]
        yield Inspection(
            asset.asset_id,
            day,
            "monthly_station_check",
            GAS_INSPECTOR,
            "defects_found" if low else "satisfactory",
            f"Outlet odorant {odorant} mg/m3, below the 5.0 mg/m3 minimum (PR-GAS-066). "
            "Injection pump not delivering."
            if low
            else "Duty stream holding 1.60 bar; filter and odorant within limits.",
            {
                "inlet_bar": round(rng.uniform(6.3, 6.9), 2),
                "outlet_bar": round(1.60 + rng.uniform(-0.02, 0.02), 2),
                "odorant_mg_m3": odorant,
                "filter_dp_mbar": round(rng.uniform(110, 230)),
            },
        )


def mains_surveys(
    asset: Asset, rng: random.Random, incidents: dict[str, datetime]
) -> Iterator[Inspection]:
    months = {"MAIN-LP-22": 6, "MAIN-LP-17": 36}.get(asset.asset_id, 12)
    cast_iron = asset.asset_id == "MAIN-LP-22"
    for day in monthly(rng.randint(3, 25), every_months=months):
        found = rng.randint(1, 3) if cast_iron else int(rng.random() < 0.15)
        yield Inspection(
            asset.asset_id,
            day,
            "leakage_survey",
            GAS_INSPECTOR,
            "defects_found" if found else "satisfactory",
            f"{found} gas indication(s) recorded along the route and reported for repair."
            if found
            else "No gas indications along the route.",
            {"indications_found": found},
        )


Inspector = Callable[[Asset, random.Random, dict[str, datetime]], Iterator[Inspection]]
INSPECTORS: dict[str, Inspector] = {
    "grid_transformer": transformer_inspections,
    "primary_transformer": transformer_inspections,
    "switchgear": switchgear_inspections,
    "battery": battery_inspections,
    "distribution_transformer": secondary_substation_inspections,
    "ring_main_unit": secondary_substation_inspections,
    "cable_tunnel": tunnel_inspections,
    "district_governor": governor_inspections,
    "slam_shut_valve": slam_shut_inspections,
    "pressure_reduction_station": station_inspections,
    "main_ip": mains_surveys,
    "main_mp": mains_surveys,
    "main_lp": mains_surveys,
}


def network_alarms(rng: random.Random, incidents: dict[str, datetime]) -> Iterator[Alarm]:
    trip = incidents["INC-2026-011"]
    yield Alarm(
        "SSV-112",
        trip,
        trip + timedelta(hours=4, minutes=5),
        1,
        "SSV_CLOSED",
        "Slam-shut closed on over-pressure",
        60.4,
        "mbar",
    )
    for night in (trip - timedelta(days=offset) for offset in (9, 6, 4, 2, 1)):
        yield Alarm(
            "G-112",
            night.replace(hour=3, minute=rng.randint(0, 59)),
            night.replace(hour=5, minute=rng.randint(0, 59)),
            2,
            "OUTLET_HIGH",
            "Governor outlet pressure high",
            round(rng.uniform(43.2, 46.8), 1),
            "mbar",
        )
    recurrence = incidents["INC-2026-027"]
    for offset in (-12, -5, 0, 9, 23, 37):
        night = (recurrence + timedelta(days=offset)).replace(hour=2, minute=rng.randint(0, 59))
        if night.date() <= END:
            yield Alarm(
                "G-112",
                night,
                night + timedelta(hours=3),
                2,
                "OUTLET_HIGH",
                "Governor outlet pressure high",
                round(rng.uniform(43.1, 44.9), 1),
                "mbar",
            )
    odorant = incidents["INC-2026-019"]
    yield Alarm(
        "PRS-HRW-01",
        odorant,
        odorant + timedelta(hours=26),
        2,
        "ODORANT_LOW",
        "Outlet odorant concentration low",
        3.9,
        "mg/m3",
    )
    tunnel = incidents["INC-2025-019"]
    yield Alarm(
        "CT-KGM-01",
        tunnel,
        tunnel + timedelta(minutes=50),
        1,
        "GAS_DETECTOR_O2_LOW",
        "Tunnel oxygen below 19.5%",
        19.0,
        "%",
    )
    failed_trip = incidents["INC-2024-007"]
    yield Alarm(
        "SWG-KGM-11",
        failed_trip,
        failed_trip + timedelta(hours=2),
        1,
        "CB_FAIL_TO_TRIP",
        "Circuit breaker failed to trip on test, panel 5",
    )
    for feeder, faults_per_year in (("FDR-KGM-03", 3), ("FDR-ASH-07", 1), ("FDR-ASH-09", 1)):
        for _ in range(faults_per_year * 2):
            day = START + timedelta(days=rng.randint(0, (END - START).days))
            raised = at(day, rng.randint(0, 23), rng.randint(0, 59))
            yield Alarm(
                feeder,
                raised,
                raised + timedelta(minutes=rng.randint(55, 240)),
                1,
                "FEEDER_TRIP",
                "Feeder circuit breaker tripped on earth fault",
            )
    for battery in ("BAT-RVL", "BAT-ASH", "BAT-KGM"):
        day = START + timedelta(days=rng.randint(0, (END - START).days))
        raised = at(day, rng.randint(0, 23), rng.randint(0, 59))
        yield Alarm(
            battery,
            raised,
            raised + timedelta(hours=rng.randint(2, 9)),
            2,
            "CHARGER_FAULT",
            "Battery charger fault",
        )


# ----------------------------------------------------------------------------- work orders

ANNUAL_MAINTENANCE = {
    "grid_transformer": "Annual transformer maintenance and protection checks",
    "primary_transformer": "Annual transformer maintenance and protection checks",
    "switchgear": "Annual switchgear maintenance",
    "battery": "Annual battery impedance test (PR-ELEC-058)",
    "district_governor": "Annual governor maintenance (PR-GAS-010)",
    "pressure_reduction_station": "Annual station maintenance and stream changeover (PR-GAS-036)",
    "ring_main_unit": "Ring main unit maintenance",
}


def planned_work_orders(assets: list[Asset], rng: random.Random) -> Iterator[WorkOrder]:
    for asset in assets:
        title = ANNUAL_MAINTENANCE.get(asset.asset_class)
        if title is None:
            continue
        for due in monthly(rng.randint(1, 28), every_months=12):
            raised = due - timedelta(days=30)
            done = due - timedelta(days=rng.randint(0, 20))
            finished = done <= END - timedelta(days=7)
            yield WorkOrder(
                asset.asset_id,
                "planned",
                title,
                "completed" if finished else "open",
                3,
                raised,
                due,
                done if finished else None,
            )


def defect_work_orders(inspections: list[Inspection], rng: random.Random) -> Iterator[WorkOrder]:
    for inspection in inspections:
        if inspection.outcome == "satisfactory":
            continue
        raised = inspection.inspected_on + timedelta(days=1)
        urgent = inspection.outcome == "unsatisfactory"
        due = raised + timedelta(days=7 if urgent else 28)
        done = raised + timedelta(days=rng.randint(2, 25))
        finished = done <= END - timedelta(days=14)
        yield WorkOrder(
            inspection.asset_id,
            "reactive",
            f"Remedy defect: {inspection.findings[:80]}",
            "completed" if finished else "in_progress",
            1 if urgent else 2,
            raised,
            due,
            done if finished else None,
            f"Raised from {inspection.inspection_type}.",
        )


def incident_work_orders(incidents: dict[str, datetime]) -> Iterator[WorkOrder]:
    """Work that the incidents set in motion, dated from them so timescales match the procedures."""
    trip = incidents["INC-2026-011"].date()
    yield WorkOrder(
        "G-112",
        "reactive",
        "Replace worn main valve seat after SSV-112 over-pressure trip",
        "completed",
        1,
        trip,
        trip + timedelta(days=7),
        trip + timedelta(days=6),
        "Root cause of INC-2026-011. Seat replaced under PR-GAS-010 and PR-GAS-021.",
    )
    creep = incidents["INC-2026-027"].date()
    yield WorkOrder(
        "G-112",
        "reactive",
        "Investigate recurring overnight outlet pressure creep",
        "in_progress",
        2,
        creep,
        creep + timedelta(days=70),
        None,
        "Linked to INC-2026-027. Creep relief and pilot under suspicion; 7-day logger fitted.",
    )
    action = incidents["INC-2026-029"].date()
    yield WorkOrder(
        "T-104",
        "reactive",
        "Engineering review of rising acetylene (PR-ELEC-044 6.6.4)",
        "completed",
        1,
        action,
        action + timedelta(days=7),
        action + timedelta(days=6),
        "Linked to INC-2026-029. Review found probable arcing at the tap changer selector. "
        "Load limited to the ONAN rating and weekly sampling until the outage.",
    )
    yield WorkOrder(
        "T-104",
        "planned",
        "Outage for internal inspection of tap changer selector",
        "open",
        1,
        action + timedelta(days=6),
        date(2026, 11, 27),
        None,
        "Action from the INC-2026-029 engineering review. Needs a switching programme under "
        "PR-ELEC-015 to transfer load to T-105 first.",
    )
    fans = incidents["INC-2026-022"].date()
    yield WorkOrder(
        "T-104",
        "reactive",
        "Replace failed cooling fan contactor, bank 2",
        "completed",
        1,
        fans,
        fans + timedelta(days=1),
        fans + timedelta(days=1),
        "Linked to INC-2026-022.",
    )
    yield WorkOrder(
        "SWG-KGM-11",
        "planned",
        "Replace 1974 oil switchboard with vacuum switchgear",
        "open",
        2,
        incidents["INC-2024-007"].date() + timedelta(days=90),
        date(2027, 6, 30),
        None,
        "Capital project after INC-2024-007 and recurring partial discharge findings.",
    )
    yield WorkOrder(
        "MAIN-LP-22",
        "planned",
        "Replace Station Road cast iron main with PE (mains replacement)",
        "open",
        2,
        incidents["INC-2025-040"].date() + timedelta(days=30),
        date(2027, 3, 31),
        None,
        "Brought forward after INC-2025-040.",
    )


# ---------------------------------------------------------------------------------- output


def write_records(records: Records) -> None:
    inspections = sorted(records.inspections, key=lambda row: (row.inspected_on, row.asset_id))
    work_orders = sorted(records.work_orders, key=lambda row: (row.raised_on, row.asset_id))
    alarms = sorted(records.alarms, key=lambda row: (row.raised_at, row.asset_id))
    write_csv(
        "inspections.csv",
        [
            {"inspection_id": f"INS-{n:05d}"} | asdict(row) | {"readings": json.dumps(row.readings)}
            for n, row in enumerate(inspections, start=1)
        ],
    )
    write_csv(
        "work_orders.csv",
        [{"wo_id": f"WO-{n:05d}"} | asdict(row) for n, row in enumerate(work_orders, start=1)],
    )
    write_csv(
        "alarms.csv",
        [
            {"alarm_id": n}
            | asdict(row)
            | {
                "raised_at": row.raised_at.isoformat(),
                "cleared_at": row.cleared_at.isoformat() if row.cleared_at else "",
            }
            for n, row in enumerate(alarms, start=1)
        ],
    )


def write_csv(filename: str, rows: list[dict[str, object]]) -> None:
    with (RECORDS_DIR / filename).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            {key: "" if value is None else value for key, value in row.items()} for row in rows
        )
    print(f"  {filename:<16} {len(rows):>5} rows")


if __name__ == "__main__":
    main()
