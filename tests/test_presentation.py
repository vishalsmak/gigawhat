"""How the chat frames responses, approvals and personas, without Chainlit."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from gigawhat.identity.personas import PROFILES, Persona
from gigawhat.ingestion.catalogue import StoredVersion
from gigawhat.orchestration.responses import Response, ResponseKind
from gigawhat.orchestration.service import Turn
from gigawhat.oversight.store import Approval
from gigawhat.ui.presentation import (
    PENDING_HINT,
    RESPONSE_BADGES,
    approval_card,
    callout,
    persona_welcome,
    register_table,
    requests_table,
    turn_markdown,
)
from gigawhat.ui.starters import STARTERS

PUBLIC = Path(__file__).parents[1] / "public"
VENT_EXTRACT = "6.2.2 Fit the vent stack so that its outlet is at least 2.5 m above ground level."


def turn(kind: ResponseKind, tier: str | None = None, notices: tuple[str, ...] = ()) -> Turn:
    return Turn("thread", Response(kind=kind, text="Body.", notices=list(notices)), tier)


def approval(**overrides: Any) -> Approval:
    values: dict[str, Any] = {
        "approval_id": "APR-1A2B3C",
        "thread_id": "thread",
        "created_at": datetime(2026, 10, 14, 13, 54),
        "requester_visitor": "v",
        "requester_persona": "gas_field_engineer",
        "business_unit": "gas",
        "question": "How high must the vent stack be?",
        "citations": ["PR-GAS-031 v3 §6.2"],
        "extract": VENT_EXTRACT,
        "status": "pending",
        "decided_at": None,
        "decider_visitor": None,
        "decider_persona": None,
        "decision_note": None,
    }
    return Approval(**(values | overrides))


def test_every_response_kind_has_a_status() -> None:
    assert set(RESPONSE_BADGES) == set(ResponseKind)


def test_answer_status_names_its_safety_tier() -> None:
    text = turn_markdown(turn(ResponseKind.ANSWER, tier="safety_relevant"))

    assert text.startswith("✅ **Answer** · Safety-relevant")


def test_refusal_status_leaves_out_the_tier() -> None:
    text = turn_markdown(turn(ResponseKind.REFUSAL, tier="safety_critical"))

    assert text.split("\n\n")[0] == "⛔ **Not something GigaWhat can help with**"


def test_each_notice_gets_its_own_box() -> None:
    text = turn_markdown(turn(ResponseKind.ANSWER, "routine", ("Overdue.", "Revised.")))

    assert text.count("\\:::warning") == 2


def test_pending_reply_ends_with_what_happens_next() -> None:
    text = turn_markdown(turn(ResponseKind.PENDING, tier="safety_critical"))

    assert text.endswith(callout("pending", PENDING_HINT))


def test_callout_escapes_its_fence_so_chainlit_renders_the_box() -> None:
    assert callout("note", "Nothing yet.") == "\\:::note\nNothing yet.\n:::"


def test_approval_card_never_shows_a_truncated_extract() -> None:
    assert VENT_EXTRACT not in approval_card(approval())


def test_approval_card_leaves_the_id_unformatted_for_chainlit_to_link() -> None:
    assert "`APR-1A2B3C`" not in approval_card(approval())


def test_requests_table_shows_each_requests_status() -> None:
    table = requests_table([approval(status="released"), approval(status="declined")])

    assert ("🟢 **Released**" in table, "🔴 **Declined**" in table) == (True, True)


@pytest.mark.parametrize(
    ("persona", "hint"),
    [
        (Persona.GAS_FIELD_ENGINEER, "Pick a question below"),
        (Persona.GAS_AUTHORISED_PERSON, "release or decline"),
        (Persona.AUDITOR, "audit trail opens here"),
    ],
)
def test_welcome_tells_each_persona_what_to_do(persona: Persona, hint: str) -> None:
    assert hint in persona_welcome(PROFILES[persona])


def test_welcome_leaves_out_a_role_that_repeats_the_title() -> None:
    assert persona_welcome(PROFILES[Persona.AUDITOR]).startswith("**Auditor**\n\n")


def test_register_flags_an_overdue_review() -> None:
    overdue = StoredVersion(
        "PR-GAS-010", "Governors", "gas", 4, "approved", None, date(2026, 1, 1), True, 3
    )

    assert "⚠️ **overdue**" in register_table([overdue], date(2026, 10, 14))


@pytest.mark.parametrize("persona", list(Persona))
def test_every_persona_has_an_icon(persona: Persona) -> None:
    assert (PUBLIC / "personas" / f"{persona.value}.svg").is_file()


def test_every_example_question_has_an_icon() -> None:
    icons = {example.icon for examples in STARTERS.values() for example in examples}

    assert all((PUBLIC / "icons" / f"{icon}.svg").is_file() for icon in icons)


def test_question_with_a_pipe_or_line_break_stays_in_its_table_cell() -> None:
    table = requests_table([approval(question="Is it A | B?\nOr C?")])

    assert table.splitlines()[-1].endswith("| Is it A \\| B? Or C? |")
