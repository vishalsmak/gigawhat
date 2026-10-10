"""Cited answers: the schema the model fills, the checks run on it in code, and the sources it
may cite. The model never decides what counts as verified."""

import re
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from gigawhat.assistant.evidence import EvidenceItem
from gigawhat.assistant.prompts import ANSWER_PROMPT
from gigawhat.retrieval.search import Passage, Revision

MIN_QUOTE_FRAGMENT = 12
# Near-exact matching for long quotes: most of the quote must be one unbroken match.
NEAR_MATCH_MIN_LENGTH = 40
NEAR_MATCH_SHARE = 0.85
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


class Claim(BaseModel):
    text: str = Field(description="One factual statement.")
    source_ids: list[str] = Field(description="Ids it comes from, e.g. ['S1'] or ['E2'].")
    quote: str = Field(description="Words copied exactly from the first cited source or record.")


class NextStep(BaseModel):
    text: str = Field(description="A suggested next step taken from the sources.")
    source_ids: list[str] = Field(description="Ids the step comes from.")
    needs_authorisation: bool = Field(
        description="True if the procedure requires an Authorised Person, permit or hold point."
    )


class Conflict(BaseModel):
    description: str = Field(description="What the sources disagree about.")
    source_ids: list[str] = Field(description="The ids that disagree; at least two.")


class DraftAnswer(BaseModel):
    summary: str = Field(description="At most two sentences, adding nothing beyond the claims.")
    claims: list[Claim]
    next_steps: list[NextStep]
    conflicts: list[Conflict]
    gaps: list[str] = Field(description="Parts of the question the sources do not answer.")


@dataclass(frozen=True)
class Reference:
    """A source (S1, S2…) or record (E1, E2…) the model may cite."""

    ref_id: str
    label: str
    title: str
    text: str
    kind: str
    doc_id: str | None = None
    review_due: date | None = None
    revision: Revision | None = None


@dataclass(frozen=True)
class Verification:
    claims: tuple[Claim, ...]
    next_steps: tuple[NextStep, ...]
    conflicts: tuple[Conflict, ...]
    summary: str
    dropped: tuple[str, ...]
    gaps: tuple[str, ...] = ()

    @property
    def has_content(self) -> bool:
        return bool(self.claims)


def build_references(
    passages: tuple[Passage, ...], evidence: list[EvidenceItem]
) -> list[Reference]:
    sources = [
        Reference(
            f"S{n}", p.citation, p.title, p.text, p.doc_type, p.doc_id, p.review_due, p.revision
        )
        for n, p in enumerate(passages, start=1)
    ]
    records = [
        Reference(f"E{n}", item.record_id, item.kind.replace("_", " "), item.text, "record")
        for n, item in enumerate(evidence, start=1)
    ]
    return sources + records


def format_references(references: list[Reference]) -> str:
    blocks = []
    for ref in references:
        tag = "record" if ref.kind == "record" else "source"
        opening = f'<{tag} id="{ref.ref_id}" cite="{ref.label}" title="{ref.title}">'
        blocks.append(f"{opening}\n{ref.text}\n</{tag}>")
    return "\n\n".join(blocks)


async def draft_answer(
    model: BaseChatModel, question: str, references: list[Reference]
) -> DraftAnswer:
    writer = model.with_structured_output(DraftAnswer, method="json_schema")
    prompt = f"<question>\n{question}\n</question>\n\n{format_references(references)}"
    draft = await writer.ainvoke([SystemMessage(ANSWER_PROMPT), HumanMessage(prompt)])
    return DraftAnswer.model_validate(draft)


def verify(draft: DraftAnswer, references: list[Reference]) -> Verification:
    """Keep only what the cited sources support. Every check is deterministic."""
    by_id = {ref.ref_id: ref for ref in references}
    dropped: list[str] = []

    claims = []
    for claim in draft.claims:
        problem = _claim_problem(claim, by_id)
        if problem:
            dropped.append(f"claim '{claim.text[:60]}': {problem}")
        else:
            claims.append(claim)

    steps = [step for step in draft.next_steps if _all_known(step.source_ids, by_id)]
    dropped += [
        f"next step '{s.text[:60]}': unknown source" for s in draft.next_steps if s not in steps
    ]

    conflicts = [c for c in draft.conflicts if _distinct_documents(c.source_ids, by_id) >= 2]
    dropped += [
        f"conflict '{c.description[:60]}': needs two documents"
        for c in draft.conflicts
        if c not in conflicts
    ]

    summary = draft.summary if _numbers_supported(draft.summary, claims) else ""
    if draft.summary and not summary:
        dropped.append("summary: contains numbers not found in any kept claim")

    return Verification(
        tuple(claims), tuple(steps), tuple(conflicts), summary, tuple(dropped), tuple(draft.gaps)
    )


def _claim_problem(claim: Claim, by_id: dict[str, Reference]) -> str | None:
    if not claim.source_ids:
        return "no citation"
    if not _all_known(claim.source_ids, by_id):
        return "cites a source that was not provided"
    if not quote_found(claim.quote, by_id[claim.source_ids[0]].text):
        return "quote not found in the cited source"
    return None


def quote_found(quote: str, source_text: str) -> bool:
    """True when every fragment of the quote (split at ellipses) appears in the source, in order,
    exactly or near-exactly; and every number in the quote appears in the source."""
    fragments = [f for f in ELLIPSIS.split(_normalise(quote)) if f]
    if not fragments or any(len(f) < MIN_QUOTE_FRAGMENT for f in fragments):
        return False
    haystack = _normalise(source_text)
    if not set(NUMBER.findall(quote)) <= set(NUMBER.findall(source_text)):
        return False
    position = 0
    for fragment in fragments:
        position = _find_near(fragment, haystack, position)
        if position < 0:
            return False
    return True


def _find_near(fragment: str, haystack: str, start: int) -> int:
    """End of the fragment's match at or after start, or -1. Long fragments may differ slightly
    (PDF hyphenation, punctuation) as long as most of them is one unbroken match."""
    exact = haystack.find(fragment, start)
    if exact >= 0:
        return exact + len(fragment)
    if len(fragment) < NEAR_MATCH_MIN_LENGTH:
        return -1
    matcher = SequenceMatcher(None, fragment, haystack, autojunk=False)
    block = matcher.find_longest_match(0, len(fragment), start, len(haystack))
    if block.size / len(fragment) < NEAR_MATCH_SHARE:
        return -1
    return block.b + block.size


def _normalise(text: str) -> str:
    # Typographic quotes, hyphens, dashes and spaces, which models and documents use
    # interchangeably: "ESS\u2011BRK" with a non-breaking hyphen must match "ESS-BRK".
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u202f": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.lower().split()).strip(" .\"'")


def _all_known(ids: list[str], by_id: dict[str, Reference]) -> bool:
    return bool(ids) and all(ref_id in by_id for ref_id in ids)


def _distinct_documents(ids: list[str], by_id: dict[str, Reference]) -> int:
    if not _all_known(ids, by_id):
        return 0
    return len({by_id[ref_id].doc_id or ref_id for ref_id in ids})


def _numbers_supported(summary: str, claims: list[Claim]) -> bool:
    """A summary may only repeat figures that appear in a kept claim or its quote."""
    supported = " ".join(f"{c.text} {c.quote}" for c in claims)
    return all(number in supported for number in NUMBER.findall(summary))
