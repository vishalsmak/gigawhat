from datetime import date, timedelta
from typing import Any

from gigawhat.assistant.answer import Claim, Reference, Verification
from gigawhat.assistant.responses import (
    AI_NOTE,
    REVISION_NOTICE_PERIOD,
    STRICT_MIN_RELEVANCE,
    render_answer,
    render_extracts,
    strict_extracts,
)
from gigawhat.retrieval.search import Passage

TODAY = date(2026, 10, 10)


def passage(relevance: float = 0.9, **overrides: Any) -> Passage:
    values: dict[str, Any] = {
        "doc_id": "PR-GAS-031",
        "version": 3,
        "title": "Purging and Commissioning of Polyethylene Mains",
        "section_path": "6 Procedure › 6.2 Vent stack and exclusion zone",
        "text": "6.2.2 Fit the vent stack at least 2.5 m above ground level.",
        "relevance": relevance,
        "doc_type": "procedure",
        "business_unit": "gas",
        "safety_critical": True,
        "review_due": date(2029, 4, 1),
        "owner": "Head of Gas Network Operations",
    }
    return Passage(**(values | overrides))


def test_extract_at_the_strict_threshold_is_kept() -> None:
    assert strict_extracts((passage(STRICT_MIN_RELEVANCE),))


def test_extract_just_below_the_strict_threshold_is_dropped() -> None:
    assert not strict_extracts((passage(STRICT_MIN_RELEVANCE - 0.01),))


def test_guidance_is_never_a_strict_extract() -> None:
    assert not strict_extracts((passage(doc_type="guidance"),))


def test_revision_history_is_never_a_strict_extract() -> None:
    assert not strict_extracts((passage(section_path="9 Revision history"),))


def verification(gaps: tuple[str, ...] = ()) -> Verification:
    claim = Claim(text="The stack must be 2.5 m high.", source_ids=["S1"], quote="2.5 m above")
    return Verification((claim,), (), (), "Summary.", (), gaps)


REFERENCES = [Reference("S1", "PR-GAS-031 v3 §6.2", "Purging", "text", "source")]


def test_answer_lists_what_the_sources_do_not_cover() -> None:
    text = render_answer(verification(("Who signs the permit.",)), REFERENCES, TODAY).text

    assert "**Not covered by the sources**\n- Who signs the permit." in text


def test_answer_without_gaps_has_no_gaps_section() -> None:
    assert "Not covered" not in render_answer(verification(), REFERENCES, TODAY).text


def test_answer_says_it_was_written_by_ai() -> None:
    assert AI_NOTE in render_answer(verification(), REFERENCES, TODAY).text


def revision_notices(version: int, effective_from: date) -> list[str]:
    extract = passage(version=version, effective_from=effective_from)
    return render_extracts([extract], TODAY).notices


def test_recent_revision_warns_about_older_copies() -> None:
    notices = revision_notices(3, TODAY - REVISION_NOTICE_PERIOD)

    assert notices == [
        "PR-GAS-031 v3 replaced an earlier version on 10 October 2025. "
        "Make sure nobody is working from an older printed or saved copy."
    ]


def test_revision_more_than_a_year_old_is_not_mentioned() -> None:
    assert revision_notices(3, TODAY - REVISION_NOTICE_PERIOD - timedelta(days=1)) == []


def test_first_version_has_no_earlier_version_to_warn_about() -> None:
    assert revision_notices(1, TODAY) == []


def test_two_sections_of_one_revised_document_give_one_notice() -> None:
    sections = [passage(effective_from=TODAY), passage(effective_from=TODAY, section_path="6.3")]

    assert len(render_extracts(sections, TODAY).notices) == 1
