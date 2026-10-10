"""The Chainlit chat interface. Visitors pick a persona; there is no sign-up."""

import asyncio
from datetime import date
from typing import Any

import chainlit as cl

from gigawhat.assistant.oversight import (
    Approval,
    ApprovalError,
    Decision,
    DecisionRequest,
    Feedback,
)
from gigawhat.assistant.responses import Response, ResponseKind
from gigawhat.assistant.service import Question, Turn
from gigawhat.config import get_settings
from gigawhat.corpus.catalogue import StoredVersion, stored_versions
from gigawhat.db import create_db_engine
from gigawhat.personas import PROFILES, Persona, PersonaProfile, profile_of
from gigawhat.ui.runtime import get_assistant, limiter
from gigawhat.ui.starters import STARTERS
from gigawhat.ui.visitor import visitor_from_cookie_header

DEMO_BANNER = "_Demo with fictional data. Harrowmere Energy and its records are invented._"
EXTRACT_PREVIEW = 600
AUDIT_ROWS = 15


@cl.set_chat_profiles
async def chat_profiles(user: cl.User | None) -> list[cl.ChatProfile]:
    return [
        cl.ChatProfile(
            name=profile.persona.value,
            display_name=profile.title,
            markdown_description=f"{profile.description}\n\n{DEMO_BANNER}",
            default=profile.persona is Persona.GAS_FIELD_ENGINEER,
            starters=[cl.Starter(label=label, message=text) for label, text in STARTERS[persona]],
        )
        for persona, profile in PROFILES.items()
    ]


@cl.on_chat_start
async def start() -> None:
    """Askers start on an empty chat so Chainlit shows their example questions; reviewer
    personas open on their queue, the audit trail or the register."""
    profile = profile_of(_persona())
    if profile.can_release:
        await _welcome(profile)
        await _show_queue(profile)
    elif profile.persona == Persona.AUDITOR:
        await _welcome(profile)
        await _show_audit()
    elif profile.persona == Persona.DOCUMENT_CONTROLLER:
        await _welcome(profile)
        await _show_register()
    else:
        await _show_my_requests()


async def _welcome(profile: PersonaProfile) -> None:
    units = ", ".join(unit.value for unit in profile.business_units)
    role = f" ({profile.role})" if profile.role != profile.title else ""
    await cl.Message(
        f"**{profile.title}**{role} · sees {units} documents and records\n\n"
        f"{profile.description}\n\n{DEMO_BANNER}"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    visitor = _visitor()
    if not limiter.allow(visitor):
        await cl.Message("You've reached the demo limit for this hour. Please try later.").send()
        return
    assistant = await get_assistant()
    async with cl.Step(name="How GigaWhat handled this", type="run") as step:

        async def show(label: str) -> None:
            await step.stream_token(f"✓ {label}\n")

        turn = await assistant.ask(Question(message.content, _persona(), visitor), on_step=show)
    await _send_turn(turn)


@cl.action_callback("release")
async def on_release(action: cl.Action) -> None:
    await _decide(action, Decision.RELEASED, "Checked against the permit and site conditions.")


@cl.action_callback("decline")
async def on_decline(action: cl.Action) -> None:
    reply = await cl.AskUserMessage("Why are you declining? This goes to the requester.").send()
    note = reply["output"] if reply else "No reason given."
    await _decide(action, Decision.DECLINED, note)


@cl.action_callback("show_outcome")
async def on_show_outcome(action: cl.Action) -> None:
    assistant = await get_assistant()
    await _send_turn(await assistant.outcome(action.payload["thread_id"]))


@cl.action_callback("feedback")
async def on_feedback(action: cl.Action) -> None:
    assistant = await get_assistant()
    await assistant.oversight.record_feedback(
        Feedback(
            action.payload["thread_id"], _visitor(), _persona().value, action.payload["helpful"]
        )
    )
    await action.remove()
    await cl.Message("Thanks, your feedback is recorded.").send()


async def _decide(action: cl.Action, decision: Decision, note: str) -> None:
    assistant = await get_assistant()
    request = DecisionRequest(action.payload["approval_id"], decision, _visitor(), _persona(), note)
    try:
        await assistant.decide(request)
    except ApprovalError as error:
        await cl.Message(f"Not done: {error}.").send()
        return
    await action.remove()
    outcome = "released" if decision is Decision.RELEASED else "declined"
    await cl.Message(
        f"{request.approval_id} {outcome}. The requester sees it under **Your requests** "
        "when they switch back to their persona."
    ).send()


async def _send_turn(turn: Turn) -> None:
    response = turn.response
    notices = "".join(f"\n\n> **Notice:** {notice}" for notice in response.notices)
    elements = [
        cl.Text(name=source.label, content=source.text, display="side")
        for source in response.sources
    ]
    await cl.Message(
        content=f"{response.text}{notices}{_pending_note(response)}",
        elements=elements,
        actions=_actions_for(turn),
    ).send()


def _pending_note(response: Response) -> str:
    if response.kind != ResponseKind.PENDING:
        return ""
    return (
        f"\n\n**Waiting for an Authorised Person ({response.approval_id}).** Switch to the "
        "Authorised Person persona for your unit to release or decline it."
    )


def _actions_for(turn: Turn) -> list[cl.Action]:
    if turn.response.kind == ResponseKind.PENDING:
        return [_action("show_outcome", "Check status", thread_id=turn.thread_id)]
    if turn.response.kind == ResponseKind.ANSWER:
        return [
            _action("feedback", "Helpful", thread_id=turn.thread_id, helpful=True),
            _action("feedback", "Not helpful", thread_id=turn.thread_id, helpful=False),
        ]
    return []


async def _show_queue(profile: PersonaProfile) -> None:
    assistant = await get_assistant()
    visitor = _visitor() if get_settings().demo_mode else None
    queue = await assistant.pending_approvals(profile.persona, visitor)
    if not queue:
        await cl.Message(
            "No requests are waiting for you. Ask a safety-critical question as a field "
            "engineer or control room persona, then come back here to release or decline it."
        ).send()
        return
    for approval in queue:
        await cl.Message(
            content=_approval_card(approval),
            actions=[
                _action("release", "Release", approval_id=approval.approval_id),
                _action("decline", "Decline", approval_id=approval.approval_id),
            ],
        ).send()


def _approval_card(approval: Approval) -> str:
    requester = profile_of(Persona(approval.requester_persona)).title
    extract = approval.extract[:EXTRACT_PREVIEW]
    more = "…" if len(approval.extract) > EXTRACT_PREVIEW else ""
    return (
        f"**{approval.approval_id}** from {requester} at {approval.created_at:%H:%M}\n\n"
        f"> {approval.question}\n\nCites {', '.join(approval.citations)}\n\n{extract}{more}"
    )


async def _show_my_requests() -> None:
    assistant = await get_assistant()
    requests = await assistant.oversight.requests_of(_visitor())
    if not requests:
        return
    lines = ["**Your requests**"]
    actions = []
    for approval in requests:
        lines.append(f"- {approval.approval_id}: {approval.status} · _{approval.question}_")
        if approval.status != "pending":
            label = f"Show {approval.approval_id}"
            actions.append(_action("show_outcome", label, thread_id=approval.thread_id))
    await cl.Message(content="\n".join(lines), actions=actions).send()


async def _show_audit() -> None:
    assistant = await get_assistant()
    events = await assistant.oversight.events_for(_visitor())
    if not events:
        await cl.Message("No audit events yet for this browser. Ask something first.").send()
        return
    rows = [
        "| Time | Persona | Event | Tier | Top source | Prompt | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for event in events[:AUDIT_ROWS]:
        rows.append(
            f"| {event['occurred_at'][11:19]} | {event['persona']} | {event['event_type']} "
            f"| {event['tier']} | {_top_source(event['sources'])} | {event['prompt_version']} "
            f"| {(event['latency_ms'] or 0) / 1000:.1f} |"
        )
    await cl.Message(
        "**Audit trail for this browser** (append-only; the full record, including every "
        "answer, is at `/api/audit`)\n\n" + "\n".join(rows)
    ).send()


def _top_source(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "none"
    first = sources[0].get("citation") or sources[0].get("record", "")
    more = f" +{len(sources) - 1}" if len(sources) > 1 else ""
    return f"{first}{more}"


async def _show_register() -> None:
    versions = await asyncio.to_thread(_stored_versions)
    rows = ["| Document | Ver | Status | Review due | Title |", "|---|---|---|---|---|"]
    today = date.today()
    for stored in versions:
        overdue = " **overdue**" if stored.review_overdue(today) else ""
        rows.append(
            f"| {stored.doc_id} | {stored.version} | {stored.status} "
            f"| {stored.review_due or ''}{overdue} | {stored.title} |"
        )
    await cl.Message("**Document register**\n\n" + "\n".join(rows)).send()


def _stored_versions() -> list[StoredVersion]:
    engine = create_db_engine(get_settings())
    try:
        with engine.connect() as connection:
            return stored_versions(connection)
    finally:
        engine.dispose()


def _action(name: str, label: str, **payload: object) -> cl.Action:
    return cl.Action(name=name, label=label, payload=payload)


def _persona() -> Persona:
    chosen = cl.user_session.get("chat_profile")
    return Persona(chosen) if chosen else Persona.GAS_FIELD_ENGINEER


def _visitor() -> str:
    environ = getattr(cl.context.session, "environ", None) or {}
    return visitor_from_cookie_header(environ.get("HTTP_COOKIE")) or cl.context.session.id
