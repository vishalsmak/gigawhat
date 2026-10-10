"""Table definitions used by application queries. Migrations own the DDL."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TSVECTOR

metadata = MetaData()

document_status = ENUM(
    "draft", "approved", "superseded", "withdrawn", name="document_status", create_type=False
)

documents = Table(
    "documents",
    metadata,
    Column("doc_id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("doc_type", Text, nullable=False),
    Column("business_unit", Text, nullable=False),
    Column("owner", Text, nullable=False),
    Column("source_url", Text),
)

document_versions = Table(
    "document_versions",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("doc_id", Text, ForeignKey("documents.doc_id"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("status", document_status, nullable=False),
    Column("effective_from", Date),
    Column("review_due", Date),
    Column("approver", Text),
    Column("safety_critical", Boolean, nullable=False),
    Column("sites", ARRAY(Text), nullable=False),
    Column("asset_classes", ARRAY(Text), nullable=False),
    Column("source_path", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("embedding_model", Text, nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

chunks = Table(
    "chunks",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "version_id",
        Uuid,
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("ordinal", Integer, nullable=False),
    Column("section_path", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("embedding", Vector(), nullable=False),
    Column("content_tsv", TSVECTOR),
)

sites = Table(
    "sites",
    metadata,
    Column("site_id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("business_unit", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("rating", Text),
)

assets = Table(
    "assets",
    metadata,
    Column("asset_id", Text, primary_key=True),
    Column("site_id", Text, ForeignKey("sites.site_id"), nullable=False),
    Column("asset_class", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("installed_year", Integer),
    Column("criticality", Text, nullable=False),
)

work_orders = Table(
    "work_orders",
    metadata,
    Column("wo_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("assets.asset_id"), nullable=False),
    Column("work_type", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("priority", SmallInteger, nullable=False),
    Column("raised_on", Date, nullable=False),
    Column("due_on", Date),
    Column("completed_on", Date),
    Column("notes", Text),
)

inspections = Table(
    "inspections",
    metadata,
    Column("inspection_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("assets.asset_id"), nullable=False),
    Column("inspected_on", Date, nullable=False),
    Column("inspection_type", Text, nullable=False),
    Column("inspector_role", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("findings", Text, nullable=False),
    Column("readings", JSONB, nullable=False),
)

incidents = Table(
    "incidents",
    metadata,
    Column("incident_id", Text, primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("business_unit", Text, nullable=False),
    Column("site_id", Text, ForeignKey("sites.site_id"), nullable=False),
    Column("asset_id", Text, ForeignKey("assets.asset_id")),
    Column("category", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("riddor_reportable", Boolean, nullable=False),
    Column("summary", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("immediate_actions", Text, nullable=False),
    Column("root_cause", Text),
    Column("status", Text, nullable=False),
    Column("linked_procedures", ARRAY(Text), nullable=False),
    Column("search_tsv", TSVECTOR),
)

alarms = Table(
    "alarms",
    metadata,
    Column("alarm_id", BigInteger, primary_key=True),
    Column("asset_id", Text, ForeignKey("assets.asset_id"), nullable=False),
    Column("raised_at", DateTime(timezone=True), nullable=False),
    Column("cleared_at", DateTime(timezone=True)),
    Column("priority", SmallInteger, nullable=False),
    Column("code", Text, nullable=False),
    Column("message", Text, nullable=False),
    Column("value", Numeric),
    Column("unit", Text),
)

approvals = Table(
    "approvals",
    metadata,
    Column("approval_id", Text, primary_key=True),
    Column("thread_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("requester_visitor", Text, nullable=False),
    Column("requester_persona", Text, nullable=False),
    Column("business_unit", Text, nullable=False),
    Column("question", Text, nullable=False),
    Column("citations", ARRAY(Text), nullable=False),
    Column("extract", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("decided_at", DateTime(timezone=True)),
    Column("decider_visitor", Text),
    Column("decider_persona", Text),
    Column("decision_note", Text),
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("event_id", BigInteger, primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("thread_id", Text, nullable=False),
    Column("visitor_id", Text, nullable=False),
    Column("persona", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("tier", Text),
    Column("question", Text),
    Column("pii_entities", ARRAY(Text), nullable=False),
    Column("guardrails", JSONB, nullable=False),
    Column("sources", JSONB, nullable=False),
    Column("response_kind", Text),
    Column("response", Text),
    Column("verification", JSONB, nullable=False),
    Column("models", JSONB, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("latency_ms", Integer),
)

feedback = Table(
    "feedback",
    metadata,
    Column("feedback_id", BigInteger, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("thread_id", Text, nullable=False),
    Column("visitor_id", Text, nullable=False),
    Column("persona", Text, nullable=False),
    Column("helpful", Boolean, nullable=False),
    Column("comment", Text),
)
