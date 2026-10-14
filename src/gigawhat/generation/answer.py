"""Drafting cited answers: the schema the model fills and the sources it may cite.

Checking a draft is the validation layer's job (gigawhat.validation): the model never decides
what counts as verified."""

from dataclasses import dataclass
from datetime import date

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from gigawhat.prompts import ANSWER_PROMPT
from gigawhat.records.evidence import EvidenceItem
from gigawhat.retrieval.search import Passage, Revision


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
