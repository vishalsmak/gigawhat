"""Integrity checks on the committed fictional dataset, so edits cannot silently break demos."""

import csv
from pathlib import Path

import pytest
import yaml
from sqlalchemy import Engine

from gigawhat.config import Settings
from gigawhat.corpus.register import DocType, load_register
from gigawhat.records.load import load_records

SETTINGS = Settings(_env_file=None)
REGISTER = load_register(SETTINGS.register_path)
INCIDENTS = yaml.safe_load((SETTINGS.records_dir / "incidents.yaml").read_text())["incidents"]


def read_csv(name: str) -> list[dict[str, str]]:
    with (SETTINGS.records_dir / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


ASSET_SITES = {row["asset_id"]: row["site_id"] for row in read_csv("assets.csv")}
DOC_IDS = {document.doc_id for document in REGISTER.documents}


@pytest.mark.parametrize(
    "path",
    [
        version.file
        for document in REGISTER.documents
        if document.doc_type is DocType.PROCEDURE
        for version in document.versions
    ],
)
def test_every_registered_procedure_file_exists(path: str) -> None:
    assert (SETTINGS.corpus_dir / path).exists()


def test_every_procedure_file_is_registered() -> None:
    registered = {
        (SETTINGS.corpus_dir / version.file).resolve()
        for document in REGISTER.documents
        for version in document.versions
    }
    on_disk = {path.resolve() for path in Path(SETTINGS.corpus_dir).glob("procedures/*/*.md")}

    assert on_disk <= registered


@pytest.mark.parametrize("incident", INCIDENTS, ids=lambda incident: incident["incident_id"])
def test_incident_asset_belongs_to_its_site(incident: dict[str, str]) -> None:
    asset = incident["asset_id"]

    assert asset is None or ASSET_SITES[asset] == incident["site_id"]


@pytest.mark.parametrize("incident", INCIDENTS, ids=lambda incident: incident["incident_id"])
def test_incident_links_only_registered_procedures(incident: dict[str, list[str]]) -> None:
    assert set(incident["linked_procedures"]) <= DOC_IDS


def test_incident_ids_are_unique() -> None:
    ids = [incident["incident_id"] for incident in INCIDENTS]

    assert len(ids) == len(set(ids))


@pytest.mark.integration
def test_committed_records_satisfy_database_constraints(database: Engine) -> None:
    loaded = {table.table: table.rows for table in load_records(database, SETTINGS.records_dir)}

    assert loaded["incidents"] == len(INCIDENTS)
