"""Named checks on a drafted answer, run in order before anything is shown.

Each check sees the draft as the earlier checks left it, removes what it can't stand behind, and
reports what it did. All of them are deterministic code: no model decides what counts as
verified. The last check withholds an answer that has nothing supported left, and the workflow
then abstains instead of showing it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from gigawhat.generation.answer import Claim, Conflict, DraftAnswer, NextStep, Reference
from gigawhat.validation.quotes import NUMBER, quote_found

# How much of a dropped item's text the reason repeats.
EXCERPT_CHARS = 60

Sources = dict[str, Reference]


class Outcome(StrEnum):
    PASSED = "passed"
    REPAIRED = "repaired"  # Something was dropped; the rest can be shown.
    WITHHELD = "withheld"  # Nothing supported is left: the answer must not be shown.


@dataclass(frozen=True)
class CheckResult:
    name: str
    outcome: Outcome
    dropped: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verification:
    claims: tuple[Claim, ...]
    next_steps: tuple[NextStep, ...]
    conflicts: tuple[Conflict, ...]
    summary: str
    dropped: tuple[str, ...]
    gaps: tuple[str, ...] = ()
    checks: tuple[CheckResult, ...] = ()

    @property
    def has_content(self) -> bool:
        return bool(self.claims)


Check = Callable[[DraftAnswer, Sources], tuple[DraftAnswer, CheckResult]]


def validate(draft: DraftAnswer, references: list[Reference]) -> Verification:
    sources = {ref.ref_id: ref for ref in references}
    results = []
    for check in CHECKS:
        draft, result = check(draft, sources)
        results.append(result)
    return Verification(
        claims=tuple(draft.claims),
        next_steps=tuple(draft.next_steps),
        conflicts=tuple(draft.conflicts),
        summary=draft.summary,
        dropped=tuple(reason for result in results for reason in result.dropped),
        gaps=tuple(draft.gaps),
        checks=tuple(results),
    )


def claims_have_support(draft: DraftAnswer, sources: Sources) -> tuple[DraftAnswer, CheckResult]:
    """Every claim cites at least one source or record."""
    kept = [claim for claim in draft.claims if claim.source_ids]
    reasons = [_claim_reason(c, "no citation") for c in draft.claims if not c.source_ids]
    return _with(draft, claims=kept), _result("claims_have_support", reasons)


def cited_sources_were_retrieved(
    draft: DraftAnswer, sources: Sources
) -> tuple[DraftAnswer, CheckResult]:
    """Claims and next steps cite only the sources and records that were given to the model."""
    claims = [claim for claim in draft.claims if _all_known(claim.source_ids, sources)]
    steps = [step for step in draft.next_steps if _all_known(step.source_ids, sources)]
    reasons = [
        _claim_reason(claim, "cites a source that was not provided")
        for claim in draft.claims
        if claim not in claims
    ] + [
        f"next step '{step.text[:EXCERPT_CHARS]}': unknown source"
        for step in draft.next_steps
        if step not in steps
    ]
    repaired = _with(draft, claims=claims, next_steps=steps)
    return repaired, _result("cited_sources_were_retrieved", reasons)


def quotes_match_sources(draft: DraftAnswer, sources: Sources) -> tuple[DraftAnswer, CheckResult]:
    """Each claim's quote appears in the first source it cites."""
    kept = [claim for claim in draft.claims if _quote_matches(claim, sources)]
    reasons = [
        _claim_reason(claim, "quote not found in the cited source")
        for claim in draft.claims
        if claim not in kept
    ]
    return _with(draft, claims=kept), _result("quotes_match_sources", reasons)


def conflicts_span_two_documents(
    draft: DraftAnswer, sources: Sources
) -> tuple[DraftAnswer, CheckResult]:
    """A reported conflict is between two different documents, not two parts of one."""
    kept = [c for c in draft.conflicts if _distinct_documents(c.source_ids, sources) >= 2]
    reasons = [
        f"conflict '{c.description[:EXCERPT_CHARS]}': needs two documents"
        for c in draft.conflicts
        if c not in kept
    ]
    return _with(draft, conflicts=kept), _result("conflicts_span_two_documents", reasons)


def summary_numbers_supported(
    draft: DraftAnswer, sources: Sources
) -> tuple[DraftAnswer, CheckResult]:
    """The summary repeats only figures found in a kept claim or its quote."""
    supported = " ".join(f"{c.text} {c.quote}" for c in draft.claims)
    if all(number in supported for number in NUMBER.findall(draft.summary)):
        return draft, _result("summary_numbers_supported", [])
    reason = "summary: contains numbers not found in any kept claim"
    return _with(draft, summary=""), _result("summary_numbers_supported", [reason])


def answer_has_support(draft: DraftAnswer, sources: Sources) -> tuple[DraftAnswer, CheckResult]:
    """Something supported is left to show."""
    outcome = Outcome.PASSED if draft.claims else Outcome.WITHHELD
    return draft, CheckResult("answer_has_support", outcome)


CHECKS: tuple[Check, ...] = (
    claims_have_support,
    cited_sources_were_retrieved,
    quotes_match_sources,
    conflicts_span_two_documents,
    summary_numbers_supported,
    answer_has_support,
)


def _result(name: str, reasons: list[str]) -> CheckResult:
    return CheckResult(name, Outcome.REPAIRED if reasons else Outcome.PASSED, tuple(reasons))


def _with(draft: DraftAnswer, **changes: object) -> DraftAnswer:
    return draft.model_copy(update=changes)


def _claim_reason(claim: Claim, problem: str) -> str:
    return f"claim '{claim.text[:EXCERPT_CHARS]}': {problem}"


def _quote_matches(claim: Claim, sources: Sources) -> bool:
    return quote_found(claim.quote, sources[claim.source_ids[0]].text)


def _all_known(ids: list[str], sources: Sources) -> bool:
    return bool(ids) and all(ref_id in sources for ref_id in ids)


def _distinct_documents(ids: list[str], sources: Sources) -> int:
    if not _all_known(ids, sources):
        return 0
    return len({sources[ref_id].doc_id or ref_id for ref_id in ids})
