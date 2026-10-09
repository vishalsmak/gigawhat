from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from sqlalchemy import Engine, func, insert, select, text
from sqlalchemy.exc import IntegrityError

from gigawhat.config import Settings
from gigawhat.corpus.catalogue import stored_versions
from gigawhat.corpus.chunking import SectionChunk
from gigawhat.corpus.ingest import (
    MIN_BODY_CHARS,
    DocumentControlError,
    Ingestor,
    Outcome,
    contextual_content,
)
from gigawhat.corpus.register import DocumentEntry
from gigawhat.models import embedding_model
from gigawhat.schema import chunks, document_versions

pytestmark = pytest.mark.integration

DOC_ID = "PR-GAS-099"
STEPS_V1 = "6.1.1 Confirm the main is isolated at both ends before purging.\n\n" * 2
STEPS_V2 = "6.1.1 Confirm isolation at both ends and record it on the permit.\n\n" * 3


class ParagraphChunker:
    """Splits on blank lines, so tests control chunk counts exactly."""

    def split(self, path: Path) -> list[SectionChunk]:
        paragraphs = [p for p in path.read_text().split("\n\n") if p.strip()]
        return [SectionChunk(("6 Procedure", "6.1 Isolation"), p) for p in paragraphs]


def version(number: int, status: str) -> dict[str, Any]:
    return {
        "version": number,
        "status": status,
        "effective_from": "2026-01-05",
        "review_due": "2029-01-05",
        "approver": "Gas Safety Manager",
        "safety_critical": True,
        "sites": ["GPR-MLN"],
        "asset_classes": ["main_lp"],
        "file": f"PR-GAS-099_v{number}.md",
    }


def make_document(*versions: dict[str, Any]) -> DocumentEntry:
    return DocumentEntry.model_validate(
        {
            "doc_id": DOC_ID,
            "title": "Purging Test Mains",
            "business_unit": "gas",
            "doc_type": "procedure",
            "owner": "Head of Gas Network Operations",
            "versions": list(versions),
        }
    )


@pytest.fixture
def ingestor(database: Engine, test_settings: Settings, tmp_path: Path) -> Iterator[Ingestor]:
    with database.begin() as connection:
        connection.execute(text("TRUNCATE documents CASCADE"))
    model = embedding_model(test_settings)
    yield Ingestor(
        engine=database,
        chunker=ParagraphChunker(),
        embeddings=DeterministicFakeEmbedding(size=model.dimensions),
        embedding_model="fake",
        corpus_dir=tmp_path,
    )


def write(ingestor: Ingestor, number: int, content: str) -> None:
    (ingestor.corpus_dir / f"PR-GAS-099_v{number}.md").write_text(content)


def stored_chunk_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(chunks)).scalar_one()


def statuses(engine: Engine) -> dict[int, str]:
    with engine.connect() as connection:
        return {v.version: v.status for v in stored_versions(connection)}


def test_new_version_is_ingested_as_chunks(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)

    [report] = ingestor.ingest_document(make_document(version(1, "approved")))

    assert (report.outcome, report.chunk_count) == (Outcome.INGESTED, 2)


def test_stored_status_comes_from_the_register(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)

    ingestor.ingest_document(make_document(version(1, "approved")))

    assert statuses(ingestor.engine) == {1: "approved"}


def test_reingesting_unchanged_file_reports_unchanged(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    document = make_document(version(1, "approved"))
    ingestor.ingest_document(document)

    [report] = ingestor.ingest_document(document)

    assert report.outcome is Outcome.UNCHANGED


def test_reingesting_unchanged_file_adds_no_chunks(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    document = make_document(version(1, "approved"))
    ingestor.ingest_document(document)

    ingestor.ingest_document(document)

    assert stored_chunk_count(ingestor.engine) == 2


def test_new_version_supersedes_old_one(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    ingestor.ingest_document(make_document(version(1, "approved")))
    write(ingestor, 2, STEPS_V2)

    ingestor.ingest_document(make_document(version(1, "superseded"), version(2, "approved")))

    assert statuses(ingestor.engine) == {1: "superseded", 2: "approved"}


def test_editing_a_published_version_is_refused(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    document = make_document(version(1, "approved"))
    ingestor.ingest_document(document)
    write(ingestor, 1, STEPS_V2)

    with pytest.raises(DocumentControlError, match="Issue a new version number"):
        ingestor.ingest_document(document)


def test_refused_edit_leaves_database_untouched(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    ingestor.ingest_document(make_document(version(1, "approved")))
    write(ingestor, 1, STEPS_V2)
    write(ingestor, 2, STEPS_V2)

    with pytest.raises(DocumentControlError):
        ingestor.ingest_document(make_document(version(1, "superseded"), version(2, "approved")))

    assert statuses(ingestor.engine) == {1: "approved"}


def test_missing_file_is_reported_not_stored(ingestor: Ingestor) -> None:
    [report] = ingestor.ingest_document(make_document(version(1, "approved")))

    assert report.outcome is Outcome.MISSING_FILE
    assert statuses(ingestor.engine) == {}


def test_drafts_are_stored_as_drafts(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)

    ingestor.ingest_document(make_document(version(1, "draft")))

    assert statuses(ingestor.engine) == {1: "draft"}


def test_fragment_one_character_short_of_minimum_is_dropped(ingestor: Ingestor) -> None:
    write(ingestor, 1, "x" * (MIN_BODY_CHARS - 1) + "\n\n" + STEPS_V1)

    [report] = ingestor.ingest_document(make_document(version(1, "approved")))

    assert report.chunk_count == 2


def test_fragment_at_minimum_length_is_kept(ingestor: Ingestor) -> None:
    write(ingestor, 1, "x" * MIN_BODY_CHARS + "\n\n" + STEPS_V1)

    [report] = ingestor.ingest_document(make_document(version(1, "approved")))

    assert report.chunk_count == 3


def test_file_path_through_a_parent_directory_is_found(ingestor: Ingestor) -> None:
    outside = ingestor.corpus_dir / "raw"
    outside.mkdir(exist_ok=True)
    (outside / "PR-GAS-099_v1.md").write_text(STEPS_V1)
    entry = version(1, "approved") | {"file": "../raw/PR-GAS-099_v1.md"}
    nested = replace(ingestor, corpus_dir=ingestor.corpus_dir / "not-created-yet")

    [report] = nested.ingest_document(make_document(entry))

    assert report.outcome is Outcome.INGESTED


def test_database_rejects_a_second_approved_version(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    ingestor.ingest_document(make_document(version(1, "approved")))
    second = {
        "doc_id": DOC_ID,
        "version": 2,
        "status": "approved",
        "safety_critical": True,
        "sites": [],
        "asset_classes": [],
        "source_path": "x",
        "content_hash": "x",
        "embedding_model": "fake",
    }

    with pytest.raises(IntegrityError), ingestor.engine.begin() as connection:
        connection.execute(insert(document_versions).values(**second))


def test_forget_document_removes_versions_and_chunks(ingestor: Ingestor) -> None:
    write(ingestor, 1, STEPS_V1)
    ingestor.ingest_document(make_document(version(1, "approved")))

    ingestor.forget_document(DOC_ID)

    assert statuses(ingestor.engine) == {}


def test_contextual_content_starts_with_breadcrumb() -> None:
    document = make_document(version(1, "approved"))
    section = SectionChunk(("PR-GAS-099 Purging Test Mains", "6 Procedure"), "6.1.1 Isolate.")

    content = contextual_content(document, document.versions[0], section)

    assert content.startswith("PR-GAS-099 v1 · Purging Test Mains › 6 Procedure\n\n")
