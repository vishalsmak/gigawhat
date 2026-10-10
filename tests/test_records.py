from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError

from gigawhat.records.load import load_records
from gigawhat.schema import alarms, incidents, inspections

pytestmark = pytest.mark.integration


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
