"""Read-only views of what has been ingested."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, func, select

from gigawhat.schema import chunks, document_versions, documents


@dataclass(frozen=True)
class StoredVersion:
    doc_id: str
    title: str
    business_unit: str
    version: int
    status: str
    effective_from: date | None
    review_due: date | None
    safety_critical: bool
    chunk_count: int

    def review_overdue(self, today: date) -> bool:
        return self.review_due is not None and self.review_due < today


def stored_versions(connection: Connection) -> list[StoredVersion]:
    query = (
        select(
            documents.c.doc_id,
            documents.c.title,
            documents.c.business_unit,
            document_versions.c.version,
            document_versions.c.status,
            document_versions.c.effective_from,
            document_versions.c.review_due,
            document_versions.c.safety_critical,
            func.count(chunks.c.id).label("chunk_count"),
        )
        .join(document_versions, document_versions.c.doc_id == documents.c.doc_id)
        .outerjoin(chunks, chunks.c.version_id == document_versions.c.id)
        .group_by(documents.c.doc_id, document_versions.c.id)
        .order_by(documents.c.doc_id, document_versions.c.version)
    )
    return [StoredVersion(**row._mapping) for row in connection.execute(query)]
