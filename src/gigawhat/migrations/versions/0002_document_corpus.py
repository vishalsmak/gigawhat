"""Document register, versions and searchable chunks.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from gigawhat.config import get_settings
from gigawhat.models import embedding_model

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Each profile has its own database, so the vector size follows the profile's embedding model.
    settings = context.config.attributes.get("settings") or get_settings()
    dimensions = embedding_model(settings).dimensions

    status = postgresql.ENUM("draft", "approved", "superseded", "withdrawn", name="document_status")
    status.create(op.get_bind())

    op.create_table(
        "documents",
        sa.Column("doc_id", sa.Text, primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("doc_type", sa.Text, nullable=False),
        sa.Column("business_unit", sa.Text, nullable=False),
        sa.Column("owner", sa.Text, nullable=False),
        sa.Column("source_url", sa.Text),
        sa.CheckConstraint("doc_type IN ('procedure', 'guidance')", name="valid_doc_type"),
        sa.CheckConstraint(
            "business_unit IN ('electricity', 'gas', 'shared')", name="valid_business_unit"
        ),
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("doc_id", sa.Text, sa.ForeignKey("documents.doc_id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="document_status", create_type=False),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date),
        sa.Column("review_due", sa.Date),
        sa.Column("approver", sa.Text),
        sa.Column("safety_critical", sa.Boolean, nullable=False),
        sa.Column("sites", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("asset_classes", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("source_path", sa.Text, nullable=False),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("embedding_model", sa.Text, nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("doc_id", "version", name="one_row_per_version"),
    )
    # Document control enforced by the database: never two current versions of one document.
    op.create_index(
        "one_approved_version_per_document",
        "document_versions",
        ["doc_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid,
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("section_path", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(dimensions), nullable=False),
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR,
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=False,
        ),
        sa.UniqueConstraint("version_id", "ordinal", name="one_chunk_per_position"),
    )
    op.execute(
        "CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.create_index("chunks_content_tsv_gin", "chunks", ["content_tsv"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_index("one_approved_version_per_document", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_table("documents")
    postgresql.ENUM(name="document_status").drop(op.get_bind())
