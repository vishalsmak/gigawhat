"""Approvals and the audit trail.

Written with the owner role; the reader role used for retrieval cannot see either table. The
database also enforces the key rules: audit events can't be changed or deleted, and a request
can't be released by the persona that made it.
"""

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from gigawhat.personas import Persona, profile_of
from gigawhat.schema import approvals, audit_events, feedback

RECENT_EVENTS = 50
# A request nobody decides within this time can no longer be released; the requester asks again.
APPROVAL_TTL = timedelta(hours=24)


class ApprovalError(Exception):
    """A release or decline that the rules don't allow."""


class Decision(StrEnum):
    RELEASED = "released"
    DECLINED = "declined"


@dataclass(frozen=True)
class ApprovalRequest:
    thread_id: str
    requester_visitor: str
    requester_persona: Persona
    business_unit: str
    question: str
    citations: tuple[str, ...]
    extract: str


@dataclass(frozen=True)
class Approval:
    approval_id: str
    thread_id: str
    created_at: datetime
    requester_visitor: str
    requester_persona: str
    business_unit: str
    question: str
    citations: list[str]
    extract: str
    status: str
    decided_at: datetime | None
    decider_visitor: str | None
    decider_persona: str | None
    decision_note: str | None


@dataclass(frozen=True)
class DecisionRequest:
    approval_id: str
    decision: Decision
    decider_visitor: str
    decider_persona: Persona
    note: str


@dataclass(frozen=True)
class Feedback:
    thread_id: str
    visitor_id: str
    persona: str
    helpful: bool


@dataclass(frozen=True)
class AuditEvent:
    thread_id: str
    visitor_id: str
    persona: str
    event_type: str
    prompt_version: str
    tier: str | None = None
    question: str | None = None
    pii_entities: tuple[str, ...] = ()
    guardrails: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    response_kind: str | None = None
    response: str | None = None
    verification: dict[str, Any] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)
    latency_ms: int | None = None


class Oversight:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def request_approval(self, request: ApprovalRequest) -> str:
        approval_id = f"APR-{secrets.token_hex(3).upper()}"
        async with self._engine.begin() as connection:
            await connection.execute(
                insert(approvals).values(
                    approval_id=approval_id,
                    thread_id=request.thread_id,
                    requester_visitor=request.requester_visitor,
                    requester_persona=request.requester_persona.value,
                    business_unit=request.business_unit,
                    question=request.question,
                    citations=list(request.citations),
                    extract=request.extract,
                    status="pending",
                )
            )
        return approval_id

    async def get(self, approval_id: str) -> Approval:
        rows = await self._approvals(approvals.c.approval_id == approval_id)
        if not rows:
            raise ApprovalError(f"{approval_id} does not exist")
        return rows[0]

    async def pending_for(self, persona: Persona, visitor: str | None) -> list[Approval]:
        """Requests this Authorised Person may decide. In demo mode a visitor only sees the
        requests they made themselves, so visitors don't see each other's questions."""
        unit = profile_of(persona).releases_for
        if unit is None:
            return []
        conditions = [
            approvals.c.business_unit == unit.value,
            approvals.c.status == "pending",
            approvals.c.created_at > datetime.now().astimezone() - APPROVAL_TTL,
        ]
        if visitor is not None:
            conditions.append(approvals.c.requester_visitor == visitor)
        return await self._approvals(*conditions)

    async def requests_of(self, visitor: str) -> list[Approval]:
        return await self._approvals(approvals.c.requester_visitor == visitor)

    async def decide(self, request: DecisionRequest) -> Approval:
        approval = await self.get(request.approval_id)
        _check_may_decide(approval, request)
        async with self._engine.begin() as connection:
            result = await connection.execute(
                update(approvals)
                .where(approvals.c.approval_id == request.approval_id)
                .where(approvals.c.status == "pending")
                .values(
                    status=request.decision.value,
                    decided_at=datetime.now().astimezone(),
                    decider_visitor=request.decider_visitor,
                    decider_persona=request.decider_persona.value,
                    decision_note=request.note,
                )
            )
            # Another decision may have landed between the check and this update.
            if result.rowcount != 1:
                raise ApprovalError(f"{request.approval_id} was decided by someone else first")
        return await self.get(request.approval_id)

    async def record(self, event: AuditEvent) -> None:
        values = asdict(event) | {"pii_entities": list(event.pii_entities)}
        async with self._engine.begin() as connection:
            await connection.execute(insert(audit_events).values(**values))

    async def events_for(self, visitor_id: str | None) -> list[dict[str, Any]]:
        """Newest first. In demo mode, only the given visitor's events."""
        query = select(audit_events).order_by(audit_events.c.event_id.desc()).limit(RECENT_EVENTS)
        if visitor_id is not None:
            query = query.where(audit_events.c.visitor_id == visitor_id)
        async with self._engine.connect() as connection:
            rows = (await connection.execute(query)).mappings().all()
        return [json.loads(json.dumps(dict(row), default=str)) for row in rows]

    async def record_feedback(self, given: Feedback) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(insert(feedback).values(**asdict(given)))

    async def _approvals(self, *conditions: Any) -> list[Approval]:
        query = select(approvals).where(*conditions).order_by(approvals.c.created_at.desc())
        async with self._engine.connect() as connection:
            rows = (await connection.execute(query)).mappings().all()
        return [Approval(**row) for row in rows]


def _check_may_decide(approval: Approval, request: DecisionRequest) -> None:
    profile = profile_of(request.decider_persona)
    if approval.status != "pending":
        raise ApprovalError(f"{approval.approval_id} was already {approval.status}")
    if approval.created_at < datetime.now().astimezone() - APPROVAL_TTL:
        raise ApprovalError(f"{approval.approval_id} has expired; the requester must ask again")
    if profile.releases_for is None or profile.releases_for.value != approval.business_unit:
        raise ApprovalError(f"{profile.title} can't decide {approval.business_unit} requests")
    if request.decider_persona.value == approval.requester_persona:
        raise ApprovalError("The person who asked can't release their own request")
