from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError

from gigawhat.records.load import load_records
from gigawhat.schema import alarms, incidents, inspections

pytestmark = pytest.mark.integration

FILES = {
    "sites.csv": (
        "site_id,name,business_unit,kind,rating\n"
        "GPR-MLN,Mill Lane District Governor,gas,district_governor,MP to LP 75 mbar\n"
    ),
    "assets.csv": (
        "asset_id,site_id,asset_class,description,installed_year,criticality\n"
        "G-112,GPR-MLN,district_governor,MP to LP district governor,2006,high\n"
        "SSV-112,GPR-MLN,slam_shut_valve,Governor slam-shut valve,,high\n"
    ),
    "work_orders.csv": (
        "wo_id,asset_id,work_type,title,status,priority,raised_on,due_on,completed_on,notes\n"
        "WO-1,G-112,planned,Annual maintenance,completed,3,2026-01-05,2026-01-30,2026-01-12,\n"
        "WO-2,G-112,reactive,Investigate outlet creep,open,2,2026-08-20,2026-09-03,,Recurring\n"
    ),
    "inspections.csv": (
        "inspection_id,asset_id,inspected_on,inspection_type,inspector_role,outcome,findings,readings\n"
        "INS-1,G-112,2026-08-14,monthly,Competent Person (Pressure Systems),defects_found,"
        'Outlet creep,"{""outlet_lockup_mbar"": 43.5}"\n'
    ),
    "alarms.csv": (
        "alarm_id,asset_id,raised_at,cleared_at,priority,code,message,value,unit\n"
        "1,G-112,2026-08-14T02:10:00+01:00,2026-08-14T05:40:00+01:00,2,OUTLET_HIGH,"
        "Outlet pressure high,44.0,mbar\n"
    ),
    "incidents.yaml": """
incidents:
  - incident_id: INC-2026-027
    occurred_at: 2026-08-14T02:10:00+01:00
    business_unit: gas
    site_id: GPR-MLN
    asset_id: G-112
    category: equipment_failure
    severity: medium
    riddor_reportable: false
    summary: G-112 outlet pressure creep recurred.
    description: Overnight lock-up pressure rose above the set point.
    immediate_actions: Increased monitoring.
    root_cause: null
    status: open
    linked_procedures: [PR-GAS-010]
""",
}


@pytest.fixture
def records_dir(tmp_path: Path) -> Path:
    for name, content in FILES.items():
        (tmp_path / name).write_text(content)
    return tmp_path


def count(engine: Engine, table_name: str) -> int:
    table = {"alarms": alarms, "incidents": incidents, "inspections": inspections}[table_name]
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


def test_loads_every_table(database: Engine, records_dir: Path) -> None:
    loaded = {item.table: item.rows for item in load_records(database, records_dir)}

    assert loaded == {
        "sites": 1,
        "assets": 2,
        "work_orders": 2,
        "inspections": 1,
        "alarms": 1,
        "incidents": 1,
    }


def test_loading_twice_replaces_rather_than_duplicates(database: Engine, records_dir: Path) -> None:
    load_records(database, records_dir)
    load_records(database, records_dir)

    assert count(database, "alarms") == 1


def test_readings_are_stored_as_json(database: Engine, records_dir: Path) -> None:
    load_records(database, records_dir)

    with database.connect() as connection:
        readings = connection.execute(select(inspections.c.readings)).scalar_one()
    assert readings == {"outlet_lockup_mbar": 43.5}


def test_incident_text_is_searchable(database: Engine, records_dir: Path) -> None:
    load_records(database, records_dir)

    query = select(incidents.c.incident_id).where(incidents.c.search_tsv.match("creep"))
    with database.connect() as connection:
        assert connection.execute(query).scalars().all() == ["INC-2026-027"]


def test_bad_file_leaves_previous_records_in_place(database: Engine, records_dir: Path) -> None:
    load_records(database, records_dir)
    (records_dir / "alarms.csv").write_text(
        "alarm_id,asset_id,raised_at,cleared_at,priority,code,message,value,unit\n"
        "9,NO-SUCH-ASSET,2026-08-14T02:10:00+01:00,,2,X,Unknown asset,,\n"
    )

    with pytest.raises(IntegrityError):
        load_records(database, records_dir)

    assert count(database, "alarms") == 1
