"""What people see. Emergency, refusal, abstention and safety-critical extracts are fixed text or
copied source text; only the cited answer contains model-written words."""

import re
from collections.abc import Iterable
from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel

from gigawhat.assistant.answer import Reference, Verification
from gigawhat.retrieval.search import Passage, Revision

STRICT_EXTRACTS = 2
# Extracts put in front of an Authorised Person must clearly match the question, so the bar is
# higher than for an ordinary cited answer. Set on the offline reranker from the evaluation; a
# chatty but genuine question scores its right section at about 0.35, a near miss at about 0.29.
STRICT_MIN_RELEVANCE = 0.3
# How long after a new version takes effect people are warned that older copies may be about.
REVISION_NOTICE_PERIOD = timedelta(days=365)
NOT_STEPS = re.compile(
    r"revision history|references|records|definitions|purpose|scope|responsibilities", re.I
)


class ResponseKind(StrEnum):
    ANSWER = "answer"
    PENDING = "pending"
    RELEASED = "released"
    DECLINED = "declined"
    EMERGENCY = "emergency"
    REFUSAL = "refusal"
    ABSTAIN = "abstain"
    PAUSED = "paused"
    ERROR = "error"


class SourceView(BaseModel):
    label: str
    title: str
    text: str


class Response(BaseModel):
    kind: ResponseKind
    text: str
    sources: list[SourceView] = []
    notices: list[str] = []
    approval_id: str | None = None


EMERGENCY_TEXT = """\
**This sounds like an emergency. Act now; don't wait for GigaWhat.**

- **Anyone injured, a fire, or life at risk:** call **999**.
- **Smell of gas or a suspected gas escape:** call the National Gas Emergency Service on \
**0800 111 999**. Don't use switches or anything that could spark, put out naked flames, \
and get people out and away.
- **Damaged power lines or substation equipment:** keep everyone well clear and call **105**.
- Tell the Gas Network Controller or Control Engineer as soon as it's safe to do so.

Once everyone is safe, follow your emergency procedure (for gas escapes, PR-GAS-003)."""

REFUSAL_TEXT = """\
I can't help with that. GigaWhat answers questions about Harrowmere Energy's approved \
procedures and operational records. It can't change its instructions, act as an Authorised \
Person, operate equipment, or help get round permits, hold points or other controls."""

ABSTAIN_TEXT = """\
I couldn't find an approved Harrowmere procedure or record that answers this for your role, \
so I won't guess. Please ask your Authorised Person, or the document controller if you think a \
procedure is missing."""

STRICT_PREFACE = """\
**Safety-critical work: an Authorised Person must release this before you act.**

The extracts below are copied word for word from the approved procedure. GigaWhat has not \
written, reordered or changed any step. Work to the full procedure and your permit, not to \
these extracts alone."""

PAUSED_TEXT = """\
GigaWhat is paused by the operations team and is not answering questions at the moment. \
Use your procedures and your Authorised Person as normal."""

SERVICE_ERROR_TEXT = """\
GigaWhat couldn't finish this answer because a service it depends on failed. Nothing was \
decided. Please try again, or use your procedures and your Authorised Person as normal."""

AI_NOTE = "Written by AI from approved documents; check the cited sources."

SAFETY_NOTE = "Safety-relevant: check the cited procedure before acting on this."


def emergency() -> Response:
    return Response(kind=ResponseKind.EMERGENCY, text=EMERGENCY_TEXT)


def refusal() -> Response:
    return Response(kind=ResponseKind.REFUSAL, text=REFUSAL_TEXT)


def abstain() -> Response:
    return Response(kind=ResponseKind.ABSTAIN, text=ABSTAIN_TEXT)


def paused() -> Response:
    return Response(kind=ResponseKind.PAUSED, text=PAUSED_TEXT)


def service_error() -> Response:
    return Response(kind=ResponseKind.ERROR, text=SERVICE_ERROR_TEXT)


def strict_extracts(passages: tuple[Passage, ...]) -> list[Passage]:
    """The most relevant approved procedure steps. Guidance alone is not enough to act on, and
    revision history, references or records sections are not steps."""
    steps = [
        p
        for p in passages
        if p.doc_type == "procedure"
        and p.relevance >= STRICT_MIN_RELEVANCE
        and not NOT_STEPS.search(p.section_path.split(" › ")[-1])
    ]
    return steps[:STRICT_EXTRACTS]


def render_extracts(extracts: list[Passage], today: date) -> Response:
    """The word-for-word procedure text. Only the Authorised Person sees it before release."""
    sections = [STRICT_PREFACE]
    for passage in extracts:
        # A blank quoted line between steps keeps each step its own paragraph when rendered.
        quoted = "\n>\n".join(f"> {line}" for line in passage.text.splitlines() if line.strip())
        sections.append(f"#### {passage.citation} · {passage.title}\n\n{quoted}")
    return Response(
        kind=ResponseKind.PENDING,
        text="\n\n".join(sections),
        sources=[SourceView(label=p.citation, title=p.title, text=p.text) for p in extracts],
        notices=[
            _overdue_notice(p.citation, p.review_due) for p in extracts if p.review_overdue(today)
        ]
        + _revision_notices((p.revision for p in extracts), today),
    )


def pending_notice(extract: Response, approval_id: str) -> Response:
    """What the requester sees while waiting: which sections were found, not their text."""
    found = "\n".join(f"- {source.label} · {source.title}" for source in extract.sources)
    text = (
        f"**Waiting for an Authorised Person ({approval_id}).** This is safety-critical work, "
        f"so GigaWhat has sent these sections of the approved procedure for release:\n\n{found}"
        "\n\nThey will be shown here word for word once an Authorised Person releases them. "
        "Do not start the work until then."
    )
    sources = [source.model_copy(update={"text": ""}) for source in extract.sources]
    return Response(
        kind=ResponseKind.PENDING,
        text=text,
        sources=sources,
        notices=extract.notices,
        approval_id=approval_id,
    )


def released(extract: Response, decider: str, note: str) -> Response:
    return extract.model_copy(
        update={
            "kind": ResponseKind.RELEASED,
            "text": f"**Released by {decider}.** {note}\n\n{extract.text}",
        }
    )


def declined(decider: str, note: str) -> Response:
    return Response(
        kind=ResponseKind.DECLINED,
        text=(
            f"**Declined by {decider}.** {note}\n\nDo not start this work. "
            "Speak to your Authorised Person before going any further."
        ),
    )


def with_safety_note(response: Response) -> Response:
    return response.model_copy(update={"text": f"_{SAFETY_NOTE}_\n\n{response.text}"})


def render_answer(verification: Verification, references: list[Reference], today: date) -> Response:
    by_id = {ref.ref_id: ref for ref in references}
    cited_ids = _cited_ids(verification)
    lines: list[str] = []
    if verification.summary:
        lines += [verification.summary, ""]
    lines.append("**What the sources say**")
    lines += [f"- {c.text} {_cite(c.source_ids, by_id)}" for c in verification.claims]
    if verification.next_steps:
        lines += ["", "**Suggested next steps**"]
        for number, step in enumerate(verification.next_steps, start=1):
            approval = " _(needs an Authorised Person)_" if step.needs_authorisation else ""
            lines.append(f"{number}. {step.text} {_cite(step.source_ids, by_id)}{approval}")
    if verification.conflicts:
        lines += ["", "**The sources disagree**"]
        lines += [
            f"- {c.description} {_cite(c.source_ids, by_id)} Ask the document owners which applies."
            for c in verification.conflicts
        ]
    if verification.gaps:
        lines += ["", "**Not covered by the sources**"]
        lines += [f"- {gap}" for gap in verification.gaps]
    lines += ["", f"_{AI_NOTE}_"]
    cited = [by_id[ref_id] for ref_id in cited_ids]
    return Response(
        kind=ResponseKind.ANSWER,
        text="\n".join(lines),
        sources=[SourceView(label=r.label, title=r.title, text=r.text) for r in cited],
        notices=[
            _overdue_notice(r.label, r.review_due)
            for r in cited
            if r.review_due is not None and r.review_due < today
        ]
        + _revision_notices((r.revision for r in cited), today),
    )


def _cited_ids(verification: Verification) -> list[str]:
    ids = [i for c in verification.claims for i in c.source_ids]
    ids += [i for s in verification.next_steps for i in s.source_ids]
    ids += [i for c in verification.conflicts for i in c.source_ids]
    return list(dict.fromkeys(ids))


def _cite(ids: list[str], by_id: dict[str, Reference]) -> str:
    return "[" + "; ".join(by_id[ref_id].label for ref_id in ids) + "]"


def _overdue_notice(label: str, review_due: date | None) -> str:
    return (
        f"{label} was due for review on {review_due:%d %B %Y} and hasn't been reviewed. "
        "Check with the document owner before relying on it."
    )


def _revision_notices(revisions: Iterable[Revision | None], today: date) -> list[str]:
    """One notice per document that replaced an earlier version in the last year: someone may
    still be working from a printed or saved copy of the old one."""
    recent = [
        r for r in revisions if r is not None and today - r.effective_from <= REVISION_NOTICE_PERIOD
    ]
    return list(
        dict.fromkeys(
            f"{r.document} replaced an earlier version on {r.effective_from:%d %B %Y}. "
            "Make sure nobody is working from an older printed or saved copy."
            for r in recent
        )
    )
