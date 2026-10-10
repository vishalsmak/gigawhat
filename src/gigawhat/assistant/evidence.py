"""Read-only evidence tools over operational records, and the agent that chooses which to call.

Every query runs on the persona's row-level-security engine, so the tools can only see records
in the persona's business units. None of them can change anything.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool
from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncEngine

from gigawhat.assistant.prompts import EVIDENCE_PROMPT

MAX_TOOL_CALLS = 5
INSPECTIONS_SHOWN = 6
ALARM_DAYS = 120
INCIDENTS_SHOWN = 5
RECORDS_INTENT = (
    "alarm",
    "trip",
    "incident",
    "inspection",
    "work order",
    "history",
    "trend",
    "recent",
    "last",
    "reading",
    "dga",
    "acetylene",
    "creep",
    "defect",
    "summar",
)


@dataclass(frozen=True)
class EvidenceItem:
    record_id: str
    kind: str
    text: str


@dataclass
class EvidenceCollector:
    """Runs the tools and keeps every record they return, so answers can cite them."""

    engine: AsyncEngine
    items: list[EvidenceItem] = field(default_factory=list)

    def tools(self) -> list[BaseTool]:
        return [
            _tool(self.asset_details, "Site, class, age and criticality of an asset, e.g. T-104."),
            _tool(self.recent_inspections, "The latest inspections of an asset, with readings."),
            _tool(self.recent_alarms, f"Alarms on an asset in the last {ALARM_DAYS} days."),
            _tool(self.work_orders, "Open work orders and the latest closed ones for an asset."),
            _tool(self.search_incidents, "Search incident reports by words, optionally by asset."),
        ]

    async def asset_details(self, asset_id: str) -> str:
        rows = await self._query(
            "SELECT a.asset_id, a.asset_class, a.description, a.installed_year, a.criticality,"
            " s.site_id, s.name AS site FROM assets a JOIN sites s USING (site_id)"
            " WHERE a.asset_id = :asset_id",
            {"asset_id": asset_id.upper()},
        )
        return self._keep(
            "asset",
            [
                (
                    row.asset_id,
                    f"{row.asset_id}: {row.description} at {row.site} ({row.site_id}), "
                    f"installed {row.installed_year}, criticality {row.criticality}",
                )
                for row in rows
            ],
        )

    async def recent_inspections(self, asset_id: str) -> str:
        rows = await self._query(
            "SELECT inspection_id, inspected_on, inspection_type, outcome, findings, readings"
            " FROM inspections WHERE asset_id = :asset_id"
            " ORDER BY inspected_on DESC LIMIT :limit",
            {"asset_id": asset_id.upper(), "limit": INSPECTIONS_SHOWN},
        )
        return self._keep(
            "inspection",
            [
                (
                    row.inspection_id,
                    f"{row.inspection_id} {row.inspected_on} {row.inspection_type}: "
                    f"{row.outcome}. {row.findings} Readings: {row.readings}",
                )
                for row in rows
            ],
        )

    async def recent_alarms(self, asset_id: str) -> str:
        rows = await self._query(
            "SELECT alarm_id, raised_at, cleared_at, code, message, value, unit FROM alarms"
            " WHERE asset_id = :asset_id"
            " AND raised_at > (SELECT max(raised_at) FROM alarms) - make_interval(days => :days)"
            " ORDER BY raised_at DESC",
            {"asset_id": asset_id.upper(), "days": ALARM_DAYS},
        )
        return self._keep(
            "alarm",
            [
                (
                    f"ALM-{row.alarm_id:05d}",
                    f"ALM-{row.alarm_id:05d} {row.raised_at:%Y-%m-%d %H:%M} {row.code}: "
                    f"{row.message} {row.value or ''} {row.unit or ''}".rstrip(),
                )
                for row in rows
            ],
        )

    async def work_orders(self, asset_id: str) -> str:
        rows = await self._query(
            "(SELECT * FROM work_orders WHERE asset_id = :asset_id AND status <> 'completed')"
            " UNION ALL (SELECT * FROM work_orders WHERE asset_id = :asset_id"
            " AND status = 'completed' ORDER BY completed_on DESC LIMIT 3)"
            " ORDER BY raised_on DESC",
            {"asset_id": asset_id.upper()},
        )
        return self._keep(
            "work_order",
            [
                (
                    row.wo_id,
                    f"{row.wo_id} raised {row.raised_on}, due {row.due_on}, {row.status}: "
                    f"{row.title}. {row.notes or ''}".rstrip(),
                )
                for row in rows
            ],
        )

    async def search_incidents(self, words: str, asset_id: str = "") -> str:
        rows = await self._query(
            "SELECT incident_id, occurred_at, site_id, asset_id, category, severity, status,"
            " summary, root_cause FROM incidents"
            " WHERE (search_tsv @@ websearch_to_tsquery('english', :words)"
            "        OR (:asset_id <> '' AND asset_id = :asset_id))"
            " ORDER BY occurred_at DESC LIMIT :limit",
            {"words": words, "asset_id": asset_id.upper(), "limit": INCIDENTS_SHOWN},
        )
        return self._keep(
            "incident",
            [
                (
                    row.incident_id,
                    f"{row.incident_id} {row.occurred_at:%Y-%m-%d} {row.site_id} "
                    f"{row.asset_id or ''} {row.category}, {row.severity}, {row.status}: "
                    f"{row.summary} Root cause: {row.root_cause or 'under investigation'}",
                )
                for row in rows
            ],
        )

    async def _query(self, sql: str, parameters: dict[str, object]) -> Sequence[Row[object]]:
        async with self.engine.connect() as connection:
            return (await connection.execute(text(sql), parameters)).all()

    def _keep(self, kind: str, records: list[tuple[str, str]]) -> str:
        known = {item.record_id for item in self.items}
        for record_id, description in records:
            if record_id not in known:
                self.items.append(EvidenceItem(record_id, kind, description))
        return "\n".join(description for _, description in records) or "No matching records."


def wants_records(question: str, asset_ids: tuple[str, ...]) -> bool:
    """Gather records only when the question is about an asset or its history."""
    lowered = question.lower()
    return bool(asset_ids) or any(word in lowered for word in RECORDS_INTENT)


async def gather_evidence(
    model: BaseChatModel, collector: EvidenceCollector, question: str
) -> list[EvidenceItem]:
    agent = create_agent(
        model,
        tools=collector.tools(),
        system_prompt=EVIDENCE_PROMPT,
        middleware=[ToolCallLimitMiddleware(run_limit=MAX_TOOL_CALLS, exit_behavior="end")],
    )
    await agent.ainvoke({"messages": [HumanMessage(question)]})
    return collector.items


def _tool(function: object, description: str) -> BaseTool:
    return StructuredTool.from_function(coroutine=function, description=description)  # type: ignore[arg-type]
