"""Operational records: sites, assets, work orders, inspections, incidents and alarms.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("site_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("business_unit", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("rating", sa.Text),
        sa.CheckConstraint(
            "business_unit IN ('electricity', 'gas', 'shared')", name="valid_business_unit"
        ),
    )
    op.create_table(
        "assets",
        sa.Column("asset_id", sa.Text, primary_key=True),
        sa.Column("site_id", sa.Text, sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("asset_class", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("installed_year", sa.Integer),
        sa.Column("criticality", sa.Text, nullable=False),
        sa.CheckConstraint("criticality IN ('low', 'medium', 'high')", name="valid_criticality"),
    )
    op.create_table(
        "work_orders",
        sa.Column("wo_id", sa.Text, primary_key=True),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("work_type", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("priority", sa.SmallInteger, nullable=False),
        sa.Column("raised_on", sa.Date, nullable=False),
        sa.Column("due_on", sa.Date),
        sa.Column("completed_on", sa.Date),
        sa.Column("notes", sa.Text),
        sa.CheckConstraint("work_type IN ('planned', 'reactive')", name="valid_work_type"),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')", name="valid_wo_status"
        ),
        sa.CheckConstraint(
            "(status = 'completed') = (completed_on IS NOT NULL)", name="completed_has_date"
        ),
    )
    op.create_index("work_orders_by_asset", "work_orders", ["asset_id", "raised_on"])
    op.create_table(
        "inspections",
        sa.Column("inspection_id", sa.Text, primary_key=True),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("inspected_on", sa.Date, nullable=False),
        sa.Column("inspection_type", sa.Text, nullable=False),
        sa.Column("inspector_role", sa.Text, nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("findings", sa.Text, nullable=False),
        sa.Column("readings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.CheckConstraint(
            "outcome IN ('satisfactory', 'defects_found', 'unsatisfactory')", name="valid_outcome"
        ),
    )
    op.create_index("inspections_by_asset", "inspections", ["asset_id", "inspected_on"])
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Text, primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("business_unit", sa.Text, nullable=False),
        sa.Column("site_id", sa.Text, sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("assets.asset_id")),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("riddor_reportable", sa.Boolean, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("immediate_actions", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("linked_procedures", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR,
            sa.Computed(
                "to_tsvector('english', summary || ' ' || description || ' '"
                " || coalesce(root_cause, ''))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('near_miss', 'gas_escape', 'equipment_failure', 'injury',"
            " 'dangerous_occurrence', 'environmental', 'security')",
            name="valid_category",
        ),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name="valid_severity"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="valid_incident_status"),
    )
    op.create_index("incidents_by_asset", "incidents", ["asset_id", "occurred_at"])
    op.create_index("incidents_search", "incidents", ["search_tsv"], postgresql_using="gin")
    op.create_table(
        "alarms",
        sa.Column("alarm_id", sa.BigInteger, primary_key=True),
        sa.Column("asset_id", sa.Text, sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True)),
        sa.Column("priority", sa.SmallInteger, nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("value", sa.Numeric),
        sa.Column("unit", sa.Text),
    )
    op.create_index("alarms_by_asset", "alarms", ["asset_id", "raised_at"])


def downgrade() -> None:
    for table in ("alarms", "incidents", "inspections", "work_orders", "assets", "sites"):
        op.drop_table(table)
