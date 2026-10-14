"""The Chainlit chat interface. Visitors pick a persona; there is no sign-up.

The Markdown for every message comes from `presentation.py`; this module wires Chainlit's
events to the assistant. Icons, the logo, the theme and the stylesheet live in `public/`.
"""

import asyncio
from dataclasses import dataclass
from datetime import date

import chainlit as cl

from gigawhat.config import get_settings
from gigawhat.identity.personas import PROFILES, Persona, PersonaProfile, profile_of
from gigawhat.ingestion.catalogue import StoredVersion, stored_versions
from gigawhat.orchestration.responses import ResponseKind
from gigawhat.orchestration.service import Question, Turn
from gigawhat.oversight.store import ApprovalError, Decision, DecisionRequest, Feedback
from gigawhat.storage.db import create_db_engine
from gigawhat.ui import presentation
from gigawhat.ui.runtime import get_assistant, limiter
from gigawhat.ui.starters import STARTERS
from gigawhat.ui.visitor import visitor_from_cookie_header

NOTE_TIMEOUT_SECONDS = 600
NO_REQUESTS = (
    "No requests are waiting for you. Ask a safety-critical question as a field engineer or "
    "control room persona, then come back here to release or decline it."
)
NO_EVENTS = "No audit events yet for this browser. Ask something first."
AUDIT_ROWS = 15


@dataclass(frozen=True)
class Button:
    """An action under a message: the callback it triggers and its Lucide icon."""

    callback: str
    icon: str


RELEASE = Button("release", "shield-check")
DECLINE = Button("decline", "shield-x")
SHOW_OUTCOME = Button("show_outcome", "refresh-cw")
FEEDBACK_UP = Button("feedback", "thumbs-up")
FEEDBACK_DOWN = Button("feedback", "thumbs-down")


@cl.set_chat_profiles
async def chat_profiles(user: cl.User | None) -> list[cl.ChatProfile]:
    """With an icon, Chainlit shows it and the description on the empty chat, above the
    example questions: the persona's welcome."""
    return [
        cl.ChatProfile(
            name=profile.persona.value,
            display_name=profile.title,
            icon=f"/public/personas/{profile.persona.value}.svg",
            markdown_description=presentation.persona_welcome(profile),
            default=profile.persona is Persona.GAS_FIELD_ENGINEER,
            starters=[
                cl.Starter(label=example.label, message=example.question, icon=example.icon_url)
                for example in STARTERS[persona]
            ],
        )
        for persona, profile in PROFILES.items()
    ]


@cl.on_chat_start
async def start() -> None:
    """Askers start on an empty chat so Chainlit shows their welcome and example questions;
    reviewer personas open on their queue, the audit trail or the register."""
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
    await cl.Message(presentation.persona_welcome(profile)).send()


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


@cl.action_callback(RELEASE.callback)
async def on_release(action: cl.Action) -> None:
    note = await _ask_for_note(
        "What did you check before releasing? For example the permit number and site conditions. "
        "This is recorded in the audit trail."
    )
    if note:
        await _decide(action, Decision.RELEASED, note)


@cl.action_callback(DECLINE.callback)
async def on_decline(action: cl.Action) -> None:
    note = await _ask_for_note("Why are you declining? This goes to the requester.")
    if note:
        await _decide(action, Decision.DECLINED, note)


async def _ask_for_note(prompt: str) -> str | None:
    """A decision always needs a note in the decider's own words; no reply means no decision."""
    reply = await cl.AskUserMessage(prompt, timeout=NOTE_TIMEOUT_SECONDS).send()
    note = (reply or {}).get("output", "").strip()
    if not note:
        await cl.Message("Nothing was decided: a note is needed.").send()
        return None
    return note


@cl.action_callback(SHOW_OUTCOME.callback)
async def on_show_outcome(action: cl.Action) -> None:
    assistant = await get_assistant()
    await _send_turn(await assistant.outcome(action.payload["thread_id"]))


@cl.action_callback(FEEDBACK_UP.callback)
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
    await cl.Message(
        f"{presentation.approval_badge(decision.value)} · `{request.approval_id}`\n\n"
        "The requester sees it under **Your requests** when they switch back to their persona."
    ).send()


async def _send_turn(turn: Turn) -> None:
    elements = [
        cl.Text(name=source.label, content=source.text, display="side")
        for source in turn.response.sources
        if source.text
    ]
    await cl.Message(
        content=presentation.turn_markdown(turn), elements=elements, actions=_actions_for(turn)
    ).send()


def _actions_for(turn: Turn) -> list[cl.Action]:
    if turn.response.kind == ResponseKind.PENDING:
        return [_action(SHOW_OUTCOME, "Check status", thread_id=turn.thread_id)]
    if turn.response.kind == ResponseKind.ANSWER:
        return [
            _action(FEEDBACK_UP, "Helpful", thread_id=turn.thread_id, helpful=True),
            _action(FEEDBACK_DOWN, "Not helpful", thread_id=turn.thread_id, helpful=False),
        ]
    return []


async def _show_queue(profile: PersonaProfile) -> None:
    assistant = await get_assistant()
    visitor = _visitor() if get_settings().demo_mode else None
    queue = await assistant.pending_approvals(profile.persona, visitor)
    if not queue:
        await cl.Message(presentation.callout("note", NO_REQUESTS)).send()
        return
    for approval in queue:
        await cl.Message(
            content=presentation.approval_card(approval),
            elements=[cl.Text(name=approval.approval_id, content=approval.extract, display="side")],
            actions=[
                _action(RELEASE, "Release", approval_id=approval.approval_id),
                _action(DECLINE, "Decline", approval_id=approval.approval_id),
            ],
        ).send()


async def _show_my_requests() -> None:
    assistant = await get_assistant()
    requests = await assistant.oversight.requests_of(_visitor())
    if not requests:
        return
    actions = [
        _action(SHOW_OUTCOME, f"Show {approval.approval_id}", thread_id=approval.thread_id)
        for approval in requests
        if approval.status != "pending"
    ]
    await cl.Message(content=presentation.requests_table(requests), actions=actions).send()


async def _show_audit() -> None:
    assistant = await get_assistant()
    events = await assistant.oversight.events_for(_visitor())
    if not events:
        await cl.Message(presentation.callout("note", NO_EVENTS)).send()
        return
    await cl.Message(presentation.audit_table(events[:AUDIT_ROWS])).send()


async def _show_register() -> None:
    versions = await asyncio.to_thread(_stored_versions)
    await cl.Message(presentation.register_table(versions, date.today())).send()


def _stored_versions() -> list[StoredVersion]:
    engine = create_db_engine(get_settings())
    try:
        with engine.connect() as connection:
            return stored_versions(connection)
    finally:
        engine.dispose()


def _action(button: Button, label: str, **payload: object) -> cl.Action:
    return cl.Action(name=button.callback, label=label, icon=button.icon, payload=payload)


def _persona() -> Persona:
    chosen = cl.user_session.get("chat_profile")
    return Persona(chosen) if chosen else Persona.GAS_FIELD_ENGINEER


def _visitor() -> str:
    environ = getattr(cl.context.session, "environ", None) or {}
    return visitor_from_cookie_header(environ.get("HTTP_COOKIE")) or cl.context.session.id
