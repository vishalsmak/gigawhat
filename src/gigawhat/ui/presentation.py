"""How the chat shows things: the Markdown for answers, approvals, personas and tables.

Pure functions, so the look can be tested without Chainlit. Nothing here changes what the
assistant decided; it only frames it.

Boxed callouts use Chainlit's `:::variant` syntax, which works only on one paragraph of plain
text: bold, lists or blank lines inside stop the box rendering. Their titles are in
`.chainlit/translations/en-US.json`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from gigawhat.assistant.oversight import Approval
from gigawhat.assistant.responses import ResponseKind
from gigawhat.assistant.service import Turn
from gigawhat.assistant.tiers import Tier
from gigawhat.corpus.catalogue import StoredVersion
from gigawhat.corpus.register import DocumentStatus
from gigawhat.personas import Persona, PersonaProfile, profile_of

PENDING_HINT = (
    "In this demo, switch to the Authorised Person persona for that unit to release or decline "
    "it, then come back to see the outcome."
)
DEMO_NOTE = "_Fictional demo: Harrowmere Energy, its procedures and its records are invented._"


@dataclass(frozen=True)
class Badge:
    icon: str
    label: str

    def __str__(self) -> str:
        return f"{self.icon} **{self.label}**"


RESPONSE_BADGES = {
    ResponseKind.ANSWER: Badge("✅", "Answer"),
    ResponseKind.PENDING: Badge("⏳", "Waiting for an Authorised Person"),
    ResponseKind.RELEASED: Badge("🟢", "Released by an Authorised Person"),
    ResponseKind.DECLINED: Badge("🔴", "Declined by an Authorised Person"),
    ResponseKind.EMERGENCY: Badge("🚨", "Emergency"),
    ResponseKind.REFUSAL: Badge("⛔", "Not something GigaWhat can help with"),
    ResponseKind.ABSTAIN: Badge("🔍", "No approved procedure found"),
    ResponseKind.PAUSED: Badge("⏸️", "GigaWhat is paused"),
    ResponseKind.ERROR: Badge("⚠️", "Couldn't finish"),
}
# Only these kinds depend on the tier; for the rest it would be noise.
TIERED_KINDS = {ResponseKind.ANSWER, ResponseKind.PENDING}
TIER_LABELS = {
    Tier.ROUTINE: "Routine",
    Tier.SAFETY_RELEVANT: "Safety-relevant",
    Tier.SAFETY_CRITICAL: "Safety-critical",
    Tier.EMERGENCY: "Emergency",
}
APPROVAL_BADGES = {
    "pending": Badge("🟡", "Pending"),
    "released": Badge("🟢", "Released"),
    "declined": Badge("🔴", "Declined"),
}
DOCUMENT_STATUS_ICONS = {
    DocumentStatus.APPROVED: "✅",
    DocumentStatus.SUPERSEDED: "🗂️",
    DocumentStatus.DRAFT: "📝",
    DocumentStatus.WITHDRAWN: "⛔",
}
ASKER_HINT = (
    "Pick a question below or ask your own. Safety-critical answers wait for an Authorised "
    "Person to release them."
)
RELEASER_HINT = (
    "Colleagues' safety-critical requests for your unit appear here to release or decline."
)
REVIEWER_HINTS = {
    Persona.DOCUMENT_CONTROLLER: "The document register opens here, with every version's status.",
    Persona.AUDITOR: "This browser's audit trail opens here.",
}


def persona_welcome(profile: PersonaProfile) -> str:
    """What a persona sees before asking anything, and in the persona menu."""
    role = f" · {profile.role}" if profile.role != profile.title else ""
    return "\n\n".join(
        [f"**{profile.title}**{role}", profile.description, f"_{_hint(profile)}_", DEMO_NOTE]
    )


def turn_markdown(turn: Turn) -> str:
    """A response under a status line, with its notices and any next action in callouts."""
    response = turn.response
    kind = ResponseKind(response.kind)
    parts = [_status_line(kind, turn.tier), response.text]
    parts += [callout("warning", notice) for notice in response.notices]
    if kind == ResponseKind.PENDING:
        parts.append(callout("pending", PENDING_HINT))
    return "\n\n".join(parts)


def approval_card(approval: Approval) -> str:
    """No preview of the extract: a truncated safety-critical extract could be misread. The id
    is left unformatted so Chainlit turns it into a link to the full extract in the side panel."""
    requester = profile_of(Persona(approval.requester_persona)).title
    return "\n\n".join(
        [
            f"{approval_badge(approval.status)} · {approval.approval_id}",
            f"**From** {requester} at {approval.created_at:%H:%M} · **cites** "
            f"{', '.join(approval.citations)}",
            f"> {_one_line(approval.question)}",
            f"_Read the full extract in {approval.approval_id} before you decide._",
        ]
    )


def callout(variant: str, text: str) -> str:
    """A boxed note; `text` must be one paragraph of plain text (see the module docstring).

    The first colon is escaped: Chainlit also runs remark-directive, which would otherwise take
    the block as a directive before its alert plugin, which matches plain text, can see it.
    """
    return f"\\:::{variant}\n{text}\n:::"


def approval_badge(status: str) -> str:
    return str(APPROVAL_BADGES.get(status, Badge("•", status.capitalize())))


def requests_table(approvals: Iterable[Approval]) -> str:
    rows = [
        f"| {approval_badge(a.status)} | `{a.approval_id}` | {_cell(a.question)} |"
        for a in approvals
    ]
    return "\n".join(
        ["**Your requests**", "", "| Status | Request | Question |", "|---|---|---|", *rows]
    )


def audit_table(events: list[dict[str, Any]]) -> str:
    rows = [
        f"| {event['occurred_at'][11:19]} | {event['persona']} | {event['event_type']} "
        f"| {event['tier'] or ''} | {_top_source(event['sources'])} | `{event['prompt_version']}` "
        f"| {(event['latency_ms'] or 0) / 1000:.1f} |"
        for event in events
    ]
    header = [
        "**Audit trail for this browser** · append-only; the full record, including every "
        "answer, is at `/api/audit`",
        "",
        "| Time | Persona | Event | Tier | Top source | Prompt | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    return "\n".join(header + rows)


def register_table(versions: list[StoredVersion], today: date) -> str:
    rows = [
        f"| {v.doc_id} | v{v.version} | {DOCUMENT_STATUS_ICONS[DocumentStatus(v.status)]} "
        f"{v.status} | {v.review_due or ''}{' ⚠️ **overdue**' if v.review_overdue(today) else ''} "
        f"| {v.title} |"
        for v in versions
    ]
    header = [
        "**Document register** · every stored version and its status",
        "",
        "| Document | Version | Status | Review due | Title |",
        "|---|---|---|---|---|",
    ]
    return "\n".join(header + rows)


def _hint(profile: PersonaProfile) -> str:
    if profile.persona in REVIEWER_HINTS:
        return REVIEWER_HINTS[profile.persona]
    return RELEASER_HINT if profile.can_release else ASKER_HINT


def _status_line(kind: ResponseKind, tier: str | None) -> str:
    badge = str(RESPONSE_BADGES[kind])
    if kind in TIERED_KINDS and tier:
        return f"{badge} · {TIER_LABELS[Tier(tier)]}"
    return badge


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _cell(text: str) -> str:
    """Text a user typed, made safe for a Markdown table cell."""
    return _one_line(text).replace("|", "\\|")


def _top_source(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "none"
    first = sources[0].get("citation") or sources[0].get("record", "")
    more = f" +{len(sources) - 1}" if len(sources) > 1 else ""
    return f"{first}{more}"
