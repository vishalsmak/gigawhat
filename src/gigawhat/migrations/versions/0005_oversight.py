"""Human oversight records: approvals, an append-only audit trail, and feedback.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.Text, primary_key=True),
        sa.Column("thread_id", sa.Text, nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("requester_visitor", sa.Text, nullable=False),
        sa.Column("requester_persona", sa.Text, nullable=False),
        sa.Column("business_unit", sa.Text, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("citations", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("extract", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decider_visitor", sa.Text),
        sa.Column("decider_persona", sa.Text),
        sa.Column("decision_note", sa.Text),
        sa.CheckConstraint("status IN ('pending', 'released', 'declined')", name="valid_status"),
        sa.CheckConstraint(
            "(status = 'pending') = (decided_at IS NULL)", name="decision_has_timestamp"
        ),
        # Separation of duties: whoever asked cannot release their own request.
        sa.CheckConstraint(
            "decider_persona IS NULL OR decider_persona <> requester_persona",
            name="decider_is_not_requester",
        ),
    )
    op.create_index("approvals_pending", "approvals", ["business_unit", "status"])

    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("thread_id", sa.Text, nullable=False),
        sa.Column("visitor_id", sa.Text, nullable=False),
        sa.Column("persona", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("tier", sa.Text),
        sa.Column("question", sa.Text),
        sa.Column("pii_entities", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("guardrails", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("sources", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("response_kind", sa.Text),
        sa.Column("response", sa.Text),
        sa.Column("verification", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("models", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("prompt_version", sa.Text, nullable=False),
        sa.Column("latency_ms", sa.Integer),
    )
    op.create_index("audit_by_time", "audit_events", ["occurred_at"])
    op.create_index("audit_by_thread", "audit_events", ["thread_id"])
    op.execute(
        """
        CREATE FUNCTION refuse_audit_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION refuse_audit_change()
        """
    )

    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("thread_id", sa.Text, nullable=False),
        sa.Column("visitor_id", sa.Text, nullable=False),
        sa.Column("persona", sa.Text, nullable=False),
        sa.Column("helpful", sa.Boolean, nullable=False),
        sa.Column("comment", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.execute("DROP TRIGGER audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION refuse_audit_change()")
    op.drop_table("audit_events")
    op.drop_table("approvals")
