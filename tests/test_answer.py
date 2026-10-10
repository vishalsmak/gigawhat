from gigawhat.assistant.answer import (
    Claim,
    Conflict,
    DraftAnswer,
    NextStep,
    Reference,
    quote_found,
    verify,
)

SOURCE = "6.2.2 Fit the vent stack so that its outlet is at least 2.5 m above ground level."
REFERENCES = [
    Reference("S1", "PR-GAS-031 v3 §6.2", "Purging", SOURCE, "procedure", "PR-GAS-031"),
    Reference(
        "S2", "PR-GAS-031 v3 §6.3", "Purging", "Use nitrogen first.", "procedure", "PR-GAS-031"
    ),
    Reference(
        "S3",
        "PR-CORP-004 v3 §6.4",
        "Lone Working",
        "Never switch alone.",
        "procedure",
        "PR-CORP-004",
    ),
    Reference("E1", "INC-2025-031", "incident", "Vented gas drifted towards a car.", "record"),
]


def claim(quote: str, source_ids: list[str] | None = None) -> Claim:
    return Claim(text="The stack is 2.5 m high.", source_ids=source_ids or ["S1"], quote=quote)


def draft(**fields: object) -> DraftAnswer:
    values: dict[str, object] = {
        "summary": "",
        "claims": [claim("outlet is at least 2.5 m above ground level")],
        "next_steps": [],
        "conflicts": [],
        "gaps": [],
    }
    return DraftAnswer.model_validate(values | fields)


def test_exact_quote_is_found() -> None:
    assert quote_found("at least 2.5 m above ground level", SOURCE)


def test_quote_matching_ignores_case_and_spacing() -> None:
    assert quote_found("AT LEAST   2.5 m above\nground level", SOURCE)


def test_quote_matching_accepts_typographic_punctuation() -> None:
    assert quote_found("Fit the vent stack so that its outlet is at least 2.5 m", SOURCE)


def test_quote_with_ellipsis_must_match_each_fragment_in_order() -> None:
    assert quote_found("Fit the vent stack … above ground level", SOURCE)


def test_quote_fragments_out_of_order_are_rejected() -> None:
    assert not quote_found("above ground level … Fit the vent stack", SOURCE)


def test_altered_number_in_quote_is_rejected() -> None:
    assert not quote_found("at least 3.5 m above ground level", SOURCE)


def test_very_short_quote_is_rejected() -> None:
    assert not quote_found("2.5 m", SOURCE)


def test_supported_claim_is_kept() -> None:
    assert len(verify(draft(), REFERENCES).claims) == 1


def test_claim_citing_an_unknown_source_is_dropped() -> None:
    result = verify(draft(claims=[claim("at least 2.5 m above ground", ["S9"])]), REFERENCES)

    assert not result.has_content


def test_claim_without_citation_is_dropped() -> None:
    result = verify(draft(claims=[Claim(text="x", source_ids=[], quote="x")]), REFERENCES)

    assert result.dropped == ("claim 'x': no citation",)


def test_quote_is_checked_against_the_first_cited_source() -> None:
    result = verify(draft(claims=[claim("at least 2.5 m above ground level", ["E1"])]), REFERENCES)

    assert not result.has_content


def test_summary_with_unsupported_figure_is_dropped() -> None:
    result = verify(draft(summary="The stack must be 4 m high."), REFERENCES)

    assert result.summary == ""


def test_summary_repeating_a_claimed_figure_is_kept() -> None:
    result = verify(draft(summary="The stack must be 2.5 m high."), REFERENCES)

    assert result.summary == "The stack must be 2.5 m high."


def test_conflict_needs_two_different_documents() -> None:
    same_document = Conflict(description="x", source_ids=["S1", "S2"])

    assert verify(draft(conflicts=[same_document]), REFERENCES).conflicts == ()


def test_conflict_between_two_documents_is_kept() -> None:
    two_documents = Conflict(description="x", source_ids=["S1", "S3"])

    assert len(verify(draft(conflicts=[two_documents]), REFERENCES).conflicts) == 1


def test_next_step_citing_unknown_source_is_dropped() -> None:
    step = NextStep(text="Phone the AP.", source_ids=["S7"], needs_authorisation=True)

    assert verify(draft(next_steps=[step]), REFERENCES).next_steps == ()


def test_quote_with_non_breaking_hyphens_matches_plain_hyphens() -> None:
    assert quote_found(
        "Fit the vent stack so that its outlet is at least 2.5\u2011m",
        SOURCE.replace("2.5 m", "2.5-m"),
    )


def test_quote_with_non_breaking_spaces_matches() -> None:
    assert quote_found("at least 2.5\u00a0m above ground level", SOURCE)


def test_quote_with_minus_sign_matches_hyphen() -> None:
    assert quote_found("readings of minus\u22125 are rejected", "Readings of minus-5 are rejected.")
