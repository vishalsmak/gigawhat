"""Load the document register into Postgres: parse, chunk, embed, and apply document control.

Slow work (parsing and embedding) happens before any database write. Each document is then
written in a single transaction, so a new version and its predecessor's change to
`superseded` become visible together.
"""

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection, Engine, delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from gigawhat.corpus.chunking import Chunker, SectionChunk
from gigawhat.corpus.register import DocumentEntry, DocumentStatus, VersionEntry
from gigawhat.schema import chunks, document_versions, documents

EMBED_BATCH_SIZE = 64
# Shorter chunks are table-of-contents and page furniture, not content worth searching.
MIN_BODY_CHARS = 40
SECTION_SEPARATOR = " › "


class DocumentControlError(Exception):
    """A stored version's content changed without a new version number."""


class Outcome(StrEnum):
    INGESTED = "ingested"
    UNCHANGED = "unchanged"
    MISSING_FILE = "missing file"


@dataclass(frozen=True)
class PreparedChunk:
    section_path: str
    body: str
    content: str
    embedding: list[float]


@dataclass(frozen=True)
class VersionReport:
    doc_id: str
    version: int
    status: DocumentStatus
    outcome: Outcome
    chunk_count: int = 0

    @classmethod
    def missing(cls, doc_id: str, entry: VersionEntry) -> "VersionReport":
        return cls(doc_id, entry.version, entry.status, Outcome.MISSING_FILE)


@dataclass(frozen=True)
class PreparedVersion:
    doc_id: str
    entry: VersionEntry
    content_hash: str
    embedding_model: str
    new_chunks: tuple[PreparedChunk, ...]

    def report(self) -> VersionReport:
        outcome = Outcome.INGESTED if self.new_chunks else Outcome.UNCHANGED
        return VersionReport(
            self.doc_id, self.entry.version, self.entry.status, outcome, len(self.new_chunks)
        )


@dataclass(frozen=True)
class Ingestor:
    engine: Engine
    chunker: Chunker
    embeddings: Embeddings
    embedding_model: str
    corpus_dir: Path

    def ingest_document(self, document: DocumentEntry) -> list[VersionReport]:
        stored_hashes = self._stored_hashes(document.doc_id)
        prepared: list[PreparedVersion] = []
        reports: list[VersionReport] = []
        for entry in document.versions:
            if not self._path(entry).exists():
                reports.append(VersionReport.missing(document.doc_id, entry))
                continue
            version = self._prepare(document, entry, stored_hashes)
            prepared.append(version)
            reports.append(version.report())

        with self.engine.begin() as connection:
            _upsert_document(connection, document)
            for version in prepared:
                if version.new_chunks:
                    _insert_version(connection, version)
            _apply_register_statuses(connection, document)
        return reports

    def forget_document(self, doc_id: str) -> None:
        """Delete every stored version so the next ingest rebuilds it. For development only:
        in production, versions are never deleted."""
        with self.engine.begin() as connection:
            connection.execute(
                delete(document_versions).where(document_versions.c.doc_id == doc_id)
            )

    def _stored_hashes(self, doc_id: str) -> dict[int, str]:
        query = select(document_versions.c.version, document_versions.c.content_hash).where(
            document_versions.c.doc_id == doc_id
        )
        with self.engine.connect() as connection:
            return {row.version: row.content_hash for row in connection.execute(query)}

    def _path(self, entry: VersionEntry) -> Path:
        return (self.corpus_dir / entry.file).resolve()

    def _prepare(
        self, document: DocumentEntry, entry: VersionEntry, stored: dict[int, str]
    ) -> PreparedVersion:
        path = self._path(entry)
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        stored_hash = stored.get(entry.version)
        if stored_hash is None:
            new_chunks = self._build_chunks(document, entry, path)
        elif stored_hash == content_hash:
            new_chunks = ()
        else:
            raise DocumentControlError(
                f"{document.doc_id} v{entry.version} changed after it was ingested. "
                "Issue a new version number instead of editing a published one."
            )
        return PreparedVersion(
            document.doc_id, entry, content_hash, self.embedding_model, new_chunks
        )

    def _build_chunks(
        self, document: DocumentEntry, entry: VersionEntry, path: Path
    ) -> tuple[PreparedChunk, ...]:
        sections = [
            section
            for section in self.chunker.split(path)
            if len(section.body.strip()) >= MIN_BODY_CHARS
        ]
        contents = [contextual_content(document, entry, section) for section in sections]
        vectors = self._embed(contents)
        return tuple(
            PreparedChunk(section_path(document, section), section.body, content, vector)
            for section, content, vector in zip(sections, contents, vectors, strict=True)
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            vectors.extend(self.embeddings.embed_documents(batch))
        return vectors


def section_path(document: DocumentEntry, section: SectionChunk) -> str:
    """The heading trail below the document title, e.g. '6 Procedure › 6.2 Nitrogen purge'."""
    headings = [heading for heading in section.headings if not heading.startswith(document.doc_id)]
    return SECTION_SEPARATOR.join(headings) or document.title


def contextual_content(document: DocumentEntry, entry: VersionEntry, section: SectionChunk) -> str:
    """What gets embedded and searched: a breadcrumb header, then the chunk text."""
    header = (
        f"{document.doc_id} v{entry.version} · {document.title}"
        f"{SECTION_SEPARATOR}{section_path(document, section)}"
    )
    return f"{header}\n\n{section.body}"


def _upsert_document(connection: Connection, document: DocumentEntry) -> None:
    values = {
        "title": document.title,
        "doc_type": document.doc_type.value,
        "business_unit": document.business_unit.value,
        "owner": document.owner,
        "source_url": document.source_url,
    }
    statement = pg_insert(documents).values(doc_id=document.doc_id, **values)
    connection.execute(statement.on_conflict_do_update(index_elements=["doc_id"], set_=values))


def _insert_version(connection: Connection, version: PreparedVersion) -> None:
    # Inserted as draft; _apply_register_statuses sets the real status in the same transaction,
    # after any previously approved version has been demoted.
    version_id: UUID = connection.execute(
        insert(document_versions)
        .values(
            doc_id=version.doc_id,
            version=version.entry.version,
            status=DocumentStatus.DRAFT.value,
            safety_critical=version.entry.safety_critical,
            sites=list(version.entry.sites),
            asset_classes=list(version.entry.asset_classes),
            source_path=version.entry.file,
            content_hash=version.content_hash,
            embedding_model=version.embedding_model,
        )
        .returning(document_versions.c.id)
    ).scalar_one()
    connection.execute(
        insert(chunks),
        [
            {
                "version_id": version_id,
                "ordinal": ordinal,
                "section_path": chunk.section_path,
                "body": chunk.body,
                "content": chunk.content,
                "embedding": chunk.embedding,
            }
            for ordinal, chunk in enumerate(version.new_chunks)
        ],
    )


def _apply_register_statuses(connection: Connection, document: DocumentEntry) -> None:
    """Copy status and applicability from the register. Approved goes last so the
    one-approved-version index never sees two at once."""
    approved_last = sorted(
        document.versions, key=lambda entry: entry.status is DocumentStatus.APPROVED
    )
    for entry in approved_last:
        connection.execute(
            update(document_versions)
            .where(
                document_versions.c.doc_id == document.doc_id,
                document_versions.c.version == entry.version,
            )
            .values(
                status=entry.status.value,
                effective_from=entry.effective_from,
                review_due=entry.review_due,
                approver=entry.approver,
                safety_critical=entry.safety_critical,
                sites=list(entry.sites),
                asset_classes=list(entry.asset_classes),
            )
        )
