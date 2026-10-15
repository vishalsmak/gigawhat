"""Integrity checks on the committed fictional dataset, so edits cannot silently break demos."""

import csv
import hashlib
from pathlib import Path

import pypdfium2
import pytest
import yaml
from sqlalchemy import Engine

from gigawhat.config import Settings
from gigawhat.ingestion.register import DocType, load_register
from gigawhat.records.load import load_records
from gigawhat.retrieval.query import DOC_ID

SETTINGS = Settings(_env_file=None)
REGISTER = load_register(SETTINGS.register_path)
INCIDENTS = yaml.safe_load((SETTINGS.records_dir / "incidents.yaml").read_text())["incidents"]


def read_csv(name: str) -> list[dict[str, str]]:
    with (SETTINGS.records_dir / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


ASSET_SITES = {row["asset_id"]: row["site_id"] for row in read_csv("assets.csv")}
DOC_IDS = {document.doc_id for document in REGISTER.documents}
PROCEDURE_FILES = [
    version.file
    for document in REGISTER.documents
    if document.doc_type is DocType.PROCEDURE
    for version in document.versions
]
# Written by scripts/render_procedures.py into each procedure PDF's metadata.
SOURCE_KEY = "source-sha256:"


@pytest.mark.parametrize("doc_id", sorted(DOC_IDS))
def test_every_registered_document_id_is_recognised_in_questions(doc_id: str) -> None:
    assert DOC_ID.fullmatch(doc_id)


@pytest.mark.parametrize("path", PROCEDURE_FILES)
def test_every_registered_procedure_file_exists(path: str) -> None:
    assert (SETTINGS.corpus_dir / path).exists()


def test_every_procedure_file_is_registered() -> None:
    registered = {
        (SETTINGS.corpus_dir / version.file).resolve()
        for document in REGISTER.documents
        for version in document.versions
    }
    on_disk = {path.resolve() for path in Path(SETTINGS.corpus_dir).glob("procedures/*/*.pdf")}

    assert on_disk <= registered


def test_every_procedure_source_is_published_as_a_registered_pdf() -> None:
    published = {(SETTINGS.corpus_dir / path).resolve() for path in PROCEDURE_FILES}
    sources = Path(SETTINGS.corpus_dir).glob("procedures/*/*.md")

    assert {source.resolve().with_suffix(".pdf") for source in sources} <= published


@pytest.mark.parametrize("path", PROCEDURE_FILES)
def test_every_procedure_pdf_was_published_from_its_current_source(path: str) -> None:
    pdf = SETTINGS.corpus_dir / path
    source = hashlib.sha256(pdf.with_suffix(".md").read_bytes()).hexdigest()

    keywords = pypdfium2.PdfDocument(pdf).get_metadata_dict()["Keywords"]

    assert keywords == SOURCE_KEY + source, "run: uv run scripts/render_procedures.py"


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


def test_every_codeowners_path_exists() -> None:
    """A path that no longer exists silently drops the review its owner must give."""
    codeowners = Path(".github/CODEOWNERS").read_text().splitlines()
    paths = [line.split()[0].lstrip("/") for line in codeowners if line.startswith("/")]

    assert [path for path in paths if not Path(path).exists()] == []
