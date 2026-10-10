"""Row-level security for the assistant's reader role, and the current_chunks search view.

The assistant queries as gigawhat_reader, never as the table owner. Each connection declares the
persona's business units in app.business_units; with nothing declared, nothing is visible.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

READER = "gigawhat_reader"
UNIT_SCOPED = ("documents", "sites", "incidents")
ASSET_SCOPED = ("work_orders", "inspections", "alarms")
READABLE = (
    "documents",
    "document_versions",
    "chunks",
    "sites",
    "assets",
    "work_orders",
    "inspections",
    "incidents",
    "alarms",
)


def upgrade() -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{READER}') THEN
                CREATE ROLE {READER} NOLOGIN;
            END IF;
        END $$
        """
    )
    op.execute(f"GRANT {READER} TO CURRENT_USER")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {READER}")
    op.execute(
        """
        CREATE FUNCTION visible_business_units() RETURNS text[] LANGUAGE sql STABLE AS $$
            SELECT string_to_array(nullif(current_setting('app.business_units', true), ''), ',')
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION drafts_visible() RETURNS boolean LANGUAGE sql STABLE AS $$
            SELECT coalesce(current_setting('app.include_drafts', true), 'off') = 'on'
        $$
        """
    )
    op.execute(
        """
        CREATE VIEW current_chunks WITH (security_invoker = true) AS
        SELECT c.id, c.content, c.embedding, c.content_tsv, c.body, c.section_path, c.ordinal,
               c.version_id, v.doc_id, v.version, v.safety_critical, v.review_due,
               v.effective_from, d.title, d.business_unit, d.doc_type, d.owner
        FROM chunks c
        JOIN document_versions v ON v.id = c.version_id
        JOIN documents d ON d.doc_id = v.doc_id
        WHERE v.status = 'approved'
          AND (v.effective_from IS NULL OR v.effective_from <= current_date)
        """
    )

    for table in READABLE:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT ON {table} TO {READER}")
    op.execute(f"GRANT SELECT ON current_chunks TO {READER}")

    for table in UNIT_SCOPED:
        _policy(table, "business_unit = ANY (visible_business_units())")
    _policy(
        "document_versions",
        "EXISTS (SELECT 1 FROM documents d WHERE d.doc_id = document_versions.doc_id)"
        " AND (status <> 'draft' OR drafts_visible())",
    )
    _policy("chunks", "EXISTS (SELECT 1 FROM document_versions v WHERE v.id = chunks.version_id)")
    _policy("assets", "EXISTS (SELECT 1 FROM sites s WHERE s.site_id = assets.site_id)")
    for table in ASSET_SCOPED:
        _policy(table, f"EXISTS (SELECT 1 FROM assets a WHERE a.asset_id = {table}.asset_id)")


def downgrade() -> None:
    op.execute("DROP VIEW current_chunks")
    for table in READABLE:
        op.execute(f"DROP POLICY reader_scope ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE SELECT ON {table} FROM {READER}")
    op.execute("DROP FUNCTION drafts_visible()")
    op.execute("DROP FUNCTION visible_business_units()")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {READER}")


def _policy(table: str, condition: str) -> None:
    op.execute(f"CREATE POLICY reader_scope ON {table} FOR SELECT TO {READER} USING ({condition})")
