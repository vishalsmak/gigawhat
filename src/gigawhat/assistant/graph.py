"""The assistant's workflow as a LangGraph graph.

The safety gate is part of the graph's shape: every path from a question to an answer goes
through it, and procedure text for safety-critical work is only released after an Authorised
Person decides, through LangGraph's interrupt(). Questions arrive already masked of personal
data, because graph state is saved to Postgres.
"""

import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer, interrupt
from sqlalchemy.ext.asyncio import AsyncEngine

from gigawhat.assistant import responses
from gigawhat.assistant.answer import (
    Claim,
    Conflict,
    NextStep,
    Reference,
    Verification,
    build_references,
    draft_answer,
    verify,
)
from gigawhat.assistant.evidence import (
    EvidenceCollector,
    EvidenceItem,
    gather_evidence,
    wants_records,
)
from gigawhat.assistant.oversight import ApprovalRequest, AuditEvent, Decision, Oversight
from gigawhat.assistant.prompts import PROMPT_VERSION
from gigawhat.assistant.rails import RailsVerdict
from gigawhat.assistant.responses import Response, ResponseKind, SourceView
from gigawhat.assistant.tiers import (
    RuleVerdict,
    Tier,
    TierDecision,
    classify_with_model,
    stricter,
    tier_rules,
)
from gigawhat.personas import Persona, profile_of
from gigawhat.retrieval.query import QueryAnalysis
from gigawhat.retrieval.search import Passage, RetrievalResult


class AssistantState(TypedDict, total=False):
    thread_id: str
    visitor_id: str
    persona: Persona
    question: str
    pii_entities: list[str]
    started_at: float
    rule_tier: RuleVerdict
    rails: RailsVerdict
    model_tier: TierDecision
    tier: Tier
    retrieval: RetrievalResult
    evidence: list[EvidenceItem]
    references: list[Reference]
    verification: Verification
    response: Response
    decision: dict[str, str]


class PassageRetriever(Protocol):
    async def retrieve(self, question: str, persona: Persona) -> RetrievalResult: ...

    def engine(self, persona: Persona) -> AsyncEngine: ...

    async def aclose(self) -> None: ...


class InputChecker(Protocol):
    async def check(self, question: str) -> RailsVerdict: ...


# Types stored in graph state; the checkpointer only restores types on this list.
STATE_TYPES = [
    (cls.__module__, cls.__name__)
    for cls in (
        RailsVerdict,
        RuleVerdict,
        TierDecision,
        Tier,
        Persona,
        Response,
        ResponseKind,
        SourceView,
        QueryAnalysis,
        Passage,
        RetrievalResult,
        EvidenceItem,
        Reference,
        Verification,
        Claim,
        NextStep,
        Conflict,
    )
]


@dataclass(frozen=True)
class Components:
    rails: InputChecker
    fast_model: BaseChatModel
    answer_model: BaseChatModel
    retriever: PassageRetriever
    oversight: Oversight
    model_names: dict[str, str]


def build_graph(components: Components, checkpointer: Checkpointer) -> CompiledStateGraph[Any]:
    nodes = _Nodes(components)
    graph = StateGraph(AssistantState)
    graph.add_node("screen", nodes.screen)
    graph.add_node("check_input", nodes.check_input)
    graph.add_node("classify", nodes.classify)
    graph.add_node("decide_tier", nodes.decide_tier)
    graph.add_node("emergency", nodes.emergency)
    graph.add_node("refuse", nodes.refuse)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("gather_evidence", nodes.gather_evidence)
    graph.add_node("write_answer", nodes.write_answer)
    graph.add_node("abstain", nodes.abstain)
    graph.add_node("prepare_release", nodes.prepare_release)
    graph.add_node("await_decision", nodes.await_decision)
    graph.add_node("apply_decision", nodes.apply_decision)
    graph.add_node("audit", nodes.audit)

    graph.add_edge(START, "screen")
    graph.add_conditional_edges("screen", _after_screen, ["emergency", "check_input", "classify"])
    graph.add_edge(["check_input", "classify"], "decide_tier")
    graph.add_conditional_edges("decide_tier", _after_tier, ["emergency", "refuse", "retrieve"])
    graph.add_conditional_edges(
        "retrieve", _after_retrieve, ["prepare_release", "gather_evidence", "abstain"]
    )
    graph.add_edge("gather_evidence", "write_answer")
    graph.add_conditional_edges("prepare_release", _after_release, ["await_decision", "audit"])
    graph.add_edge("await_decision", "apply_decision")
    for last in ("emergency", "refuse", "abstain", "write_answer", "apply_decision"):
        graph.add_edge(last, "audit")
    graph.add_edge("audit", END)
    return graph.compile(checkpointer=checkpointer)


def _after_screen(state: AssistantState) -> str | list[str]:
    if state["rule_tier"].tier == Tier.EMERGENCY:
        return "emergency"
    return ["check_input", "classify"]


def _after_tier(state: AssistantState) -> str:
    if state["tier"] == Tier.EMERGENCY:
        return "emergency"
    if not state["rails"].allowed:
        return "refuse"
    return "retrieve"


def _after_retrieve(state: AssistantState) -> str:
    if not state["retrieval"].sufficient:
        return "abstain"
    if state["tier"] == Tier.SAFETY_CRITICAL:
        return "prepare_release"
    return "gather_evidence"


def _after_release(state: AssistantState) -> str:
    return "await_decision" if state["response"].kind == ResponseKind.PENDING else "audit"


# Enums read back from saved state may arrive as plain strings, so graph code compares with ==
# and converts with str() rather than relying on .value or identity.
class _Nodes:
    def __init__(self, components: Components) -> None:
        self._c = components

    def screen(self, state: AssistantState) -> AssistantState:
        """Fixed rules first: an emergency doesn't wait for any model."""
        return {"rule_tier": tier_rules().classify(state["question"])}

    async def check_input(self, state: AssistantState) -> AssistantState:
        return {"rails": await self._c.rails.check(state["question"])}

    async def classify(self, state: AssistantState) -> AssistantState:
        return {"model_tier": await classify_with_model(self._c.fast_model, state["question"])}

    def decide_tier(self, state: AssistantState) -> AssistantState:
        return {"tier": stricter(state["rule_tier"].tier, state["model_tier"].tier)}

    def emergency(self, state: AssistantState) -> AssistantState:
        return {"tier": Tier.EMERGENCY, "response": responses.emergency()}

    def refuse(self, state: AssistantState) -> AssistantState:
        return {"response": responses.refusal()}

    def abstain(self, state: AssistantState) -> AssistantState:
        return {"response": responses.abstain()}

    async def retrieve(self, state: AssistantState) -> AssistantState:
        result = await self._c.retriever.retrieve(state["question"], state["persona"])
        return {"retrieval": result}

    async def gather_evidence(self, state: AssistantState) -> AssistantState:
        retrieval = state["retrieval"]
        if not wants_records(state["question"], retrieval.analysis.asset_ids):
            return {"evidence": []}
        collector = EvidenceCollector(self._c.retriever.engine(state["persona"]))
        items = await gather_evidence(self._c.answer_model, collector, state["question"])
        return {"evidence": items}

    async def write_answer(self, state: AssistantState) -> AssistantState:
        references = build_references(state["retrieval"].passages, state.get("evidence", []))
        draft = await draft_answer(self._c.answer_model, state["question"], references)
        verification = verify(draft, references)
        if not verification.has_content:
            response = responses.abstain()
        else:
            response = responses.render_answer(verification, references, date.today())
            if state["tier"] == Tier.SAFETY_RELEVANT:
                response = responses.with_safety_note(response)
        return {"references": references, "verification": verification, "response": response}

    async def prepare_release(self, state: AssistantState) -> AssistantState:
        extracts = responses.strict_extracts(state["retrieval"].passages)
        if not extracts:
            return {"response": responses.abstain()}
        response = responses.render_strict(extracts, date.today())
        approval_id = await self._c.oversight.request_approval(
            ApprovalRequest(
                thread_id=state["thread_id"],
                requester_visitor=state["visitor_id"],
                requester_persona=state["persona"],
                question=state["question"],
                citations=tuple(extract.citation for extract in extracts),
                extract=response.text,
            )
        )
        response = response.model_copy(update={"approval_id": approval_id})
        await self._c.oversight.record(self._event(state, "approval_requested", response))
        return {"response": response}

    def await_decision(self, state: AssistantState) -> AssistantState:
        decision: dict[str, str] = interrupt({"approval_id": state["response"].approval_id})
        return {"decision": decision}

    def apply_decision(self, state: AssistantState) -> AssistantState:
        decision = state["decision"]
        decider = profile_of(Persona(decision["decider_persona"])).title
        note = decision.get("note") or "No note given."
        pending = state["response"]
        if decision["decision"] == Decision.RELEASED:
            text = f"**Released by {decider}.** {note}\n\n{pending.text}"
            kind = ResponseKind.RELEASED
        else:
            text = (
                f"**Declined by {decider}.** {note}\n\nDo not start this work. "
                "Speak to your Authorised Person before going any further."
            )
            kind = ResponseKind.DECLINED
        return {"response": pending.model_copy(update={"kind": kind, "text": text})}

    async def audit(self, state: AssistantState) -> AssistantState:
        response = state["response"]
        await self._c.oversight.record(self._event(state, str(response.kind), response))
        return {}

    def _event(self, state: AssistantState, event_type: str, response: Response) -> AuditEvent:
        retrieval = state.get("retrieval")
        rails = state.get("rails")
        model_tier = state.get("model_tier")
        verification = state.get("verification")
        return AuditEvent(
            thread_id=state["thread_id"],
            visitor_id=state["visitor_id"],
            persona=str(state["persona"]),
            event_type=event_type,
            prompt_version=PROMPT_VERSION,
            tier=str(state.get("tier", state["rule_tier"].tier)),
            question=state["question"],
            pii_entities=tuple(state.get("pii_entities", [])),
            guardrails={
                "rules": list(state["rule_tier"].matched),
                "input_rails": "allowed" if rails is None or rails.allowed else "blocked",
                "model_tier": model_tier.model_dump() if model_tier else None,
                "decision": state.get("decision"),
            },
            sources=[
                {"citation": p.citation, "relevance": round(p.relevance, 3)}
                for p in (retrieval.passages if retrieval else ())
            ]
            + [{"record": item.record_id} for item in state.get("evidence", [])],
            response_kind=str(response.kind),
            response=response.text,
            verification={"dropped": list(verification.dropped)} if verification else {},
            models=self._c.model_names,
            latency_ms=int((time.time() - state["started_at"]) * 1000),
        )
