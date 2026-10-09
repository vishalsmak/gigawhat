"""Load operational records from data/records, replacing whatever is in the database."""

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, Table, insert, text

from gigawhat.schema import alarms, assets, incidents, inspections, sites, work_orders

Converter = Callable[[str], Any]
Row = dict[str, Any]


def _optional(convert: Converter) -> Converter:
    return lambda value: convert(value) if value else None


@dataclass(frozen=True)
class CsvSource:
    table: Table
    filename: str
    converters: dict[str, Converter]


# Parents before children, so foreign keys hold during the insert.
CSV_SOURCES = (
    CsvSource(sites, "sites.csv", {"rating": _optional(str)}),
    CsvSource(assets, "assets.csv", {"installed_year": _optional(int)}),
    CsvSource(
        work_orders,
        "work_orders.csv",
        {
            "priority": int,
            "raised_on": date.fromisoformat,
            "due_on": _optional(date.fromisoformat),
            "completed_on": _optional(date.fromisoformat),
            "notes": _optional(str),
        },
    ),
    CsvSource(
        inspections, "inspections.csv", {"inspected_on": date.fromisoformat, "readings": json.loads}
    ),
    CsvSource(
        alarms,
        "alarms.csv",
        {
            "alarm_id": int,
            "raised_at": datetime.fromisoformat,
            "cleared_at": _optional(datetime.fromisoformat),
            "priority": int,
            "value": _optional(float),
            "unit": _optional(str),
        },
    ),
)
INCIDENTS_FILE = "incidents.yaml"


@dataclass(frozen=True)
class LoadedTable:
    table: str
    rows: int


def load_records(engine: Engine, records_dir: Path) -> list[LoadedTable]:
    """Replace all records in one transaction, so readers never see a half-loaded set."""
    batches = [(source.table, read_csv(records_dir, source)) for source in CSV_SOURCES]
    batches.append((incidents, read_incidents(records_dir / INCIDENTS_FILE)))
    table_names = ", ".join(table.name for table, _ in batches)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names}"))
        for table, rows in batches:
            if rows:
                connection.execute(insert(table), rows)
    return [LoadedTable(table.name, len(rows)) for table, rows in batches]


def read_csv(records_dir: Path, source: CsvSource) -> list[Row]:
    with (records_dir / source.filename).open(newline="") as handle:
        return [_convert(row, source.converters) for row in csv.DictReader(handle)]


def _convert(row: dict[str, str], converters: dict[str, Converter]) -> Row:
    return {column: converters.get(column, str)(value) for column, value in row.items()}


def read_incidents(path: Path) -> list[Row]:
    rows: list[Row] = yaml.safe_load(path.read_text())["incidents"]
    return rows
