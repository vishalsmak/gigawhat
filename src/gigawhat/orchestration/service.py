"""The assistant as the UI and API see it: ask, approve, look up outcomes and the audit trail."""

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Any

import structlog
from langchain_core.tracers import LangChainTracer
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine
from structlog.contextvars import bound_contextvars

from gigawhat.config import Settings
from gigawhat.identity.personas import Persona
from gigawhat.observability.tracing import flush
from gigawhat.orchestration import responses
from gigawhat.orchestration.graph import STATE_TYPES, AssistantState, Components, build_graph
from gigawhat.orchestration.responses import Response
from gigawhat.oversight.store import (
    Approval,
    ApprovalError,
    AuditEvent,
    DecisionRequest,
    Oversight,
)
from gigawhat.policy.pii import pii_masker
from gigawhat.policy.rails import InputRails
from gigawhat.prompts import PROMPT_VERSION
from gigawhat.providers.registry import ChatRole, ModelRegistry
from gigawhat.retrieval.search import Retriever
from gigawhat.storage.db import database_url

CHECKPOINT_POOL_SIZE = 10
logger = structlog.get_logger()
STEP_LABELS = {
    "screen": "Checked for emergencies",
    "check_input": "Checked the question against the guardrails",
    "classify": "Classified the safety tier",
    "decide_tier": "Chose the stricter safety tier",
    "retrieve": "Searched approved procedures you can see",
    "gather_evidence": "Looked up operational records",
    "write_answer": "Wrote an answer and checked every quote against its source",
    "prepare_release": "Copied the procedure text and asked an Authorised Person to release it",
    "audit": "Recorded the audit trail",
}
StepListener = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class Question:
    text: str
    persona: Persona
    visitor_id: str


@dataclass(frozen=True)
class Turn:
    thread_id: str
    response: Response
    tier: str | None


@dataclass(frozen=True)
class Runtime:
    """What the assistant needs besides the graph: its parts, the checkpoint pool, a tracer."""

    components: Components
    pool: AsyncConnectionPool
    tracer: LangChainTracer | None = None
    paused: bool = False

    @property
    def trace_metadata(self) -> dict[str, str]:
        """What every trace is labelled with, so runs can be filtered and compared."""
        models = {f"{role}_model": name for role, name in self.components.model_names.items()}
        return {"prompt_version": PROMPT_VERSION} | models


class Assistant:
    def __init__(self, graph: CompiledStateGraph[Any], runtime: Runtime) -> None:
        self._graph = graph
        self._runtime = runtime
        self._components = runtime.components

    @property
    def oversight(self) -> Oversight:
        return self._components.oversight

    @property
    def trace_metadata(self) -> dict[str, str]:
        return self._runtime.trace_metadata

    async def ask(self, question: Question, on_step: StepListener | None = None) -> Turn:
        """Personal data is masked here, before the question enters graph state, which is
        saved to Postgres."""
        if self._runtime.paused:
            return Turn(thread_id="", response=responses.paused(), tier=None)
        state = _initial_state(question)
        with bound_contextvars(thread_id=state["thread_id"], persona=str(question.persona)):
            logger.info("question.received", personal_data_found=len(state["pii_entities"]))
            return await self._answer(state, on_step)

    async def pending_approvals(self, persona: Persona, visitor_id: str | None) -> list[Approval]:
        return await self.oversight.pending_for(persona, visitor_id)

    async def decide(self, request: DecisionRequest) -> Turn:
        if self._runtime.paused:
            raise ApprovalError("GigaWhat is paused, so nothing can be released or declined")
        request = replace(request, note=pii_masker().mask(request.note).text)
        approval = await self.oversight.decide(request)
        resume = {
            "decision": request.decision.value,
            "decider_persona": request.decider_persona.value,
            "decider_visitor": request.decider_visitor,
            "note": request.note,
        }
        config = self._run_config(approval.thread_id, "decide", request.decider_persona)
        with bound_contextvars(thread_id=approval.thread_id, persona=str(request.decider_persona)):
            logger.info(
                "approval.decided", approval_id=approval.approval_id, decision=str(request.decision)
            )
            await self._graph.ainvoke(Command(resume=resume), config)
        return await self._turn(approval.thread_id)

    async def outcome(self, thread_id: str) -> Turn:
        return await self._turn(thread_id)

    async def aclose(self) -> None:
        await self._components.retriever.aclose()
        await self._runtime.pool.close()
        if self._runtime.tracer is not None:
            flush(self._runtime.tracer)

    async def _answer(self, state: AssistantState, on_step: StepListener | None) -> Turn:
        thread_id = state["thread_id"]
        config = self._run_config(thread_id, "ask", state["persona"])
        try:
            async for update in self._graph.astream(state, config, stream_mode="updates"):
                for node in update:
                    logger.info("workflow.step", node=node)
                    if on_step and node in STEP_LABELS:
                        await on_step(STEP_LABELS[node])
        except Exception as error:  # A failed model or API call must still leave an audit record.
            logger.error("question.failed", error=type(error).__name__)
            await self.oversight.record(_failure_event(state, error))
            return Turn(thread_id, responses.service_error(), None)
        turn = await self._turn(thread_id)
        logger.info(
            "question.answered",
            kind=str(turn.response.kind),
            tier=turn.tier,
            seconds=round(time.time() - state["started_at"], 2),
        )
        return turn

    def _config(self, thread_id: str) -> Any:
        return {"configurable": {"thread_id": thread_id}}

    def _run_config(self, thread_id: str, run_name: str, persona: Persona) -> Any:
        """Labels a run the same way whichever tracer receives it: the assistant's own, or an
        evaluation experiment's. LangSmith groups runs sharing a thread_id into one thread."""
        metadata = {"thread_id": thread_id, "persona": str(persona)} | self._runtime.trace_metadata
        config = self._config(thread_id) | {
            "run_name": run_name,
            "metadata": metadata,
            "tags": [str(persona)],
        }
        if self._runtime.tracer is not None:
            config["callbacks"] = [self._runtime.tracer]
        return config

    async def _turn(self, thread_id: str) -> Turn:
        snapshot = await self._graph.aget_state(self._config(thread_id))
        values: dict[str, Any] = snapshot.values
        tier = values.get("tier")
        return Turn(thread_id, values["response"], str(tier) if tier else None)


async def create_assistant(settings: Settings, tracer: LangChainTracer | None) -> Assistant:
    """Pass create_tracer(settings) to trace each question, or None when something else traces,
    such as a LangSmith evaluation."""
    models = ModelRegistry(settings)
    fast_model = models.chat(ChatRole.FAST)
    components = Components(
        rails=InputRails(fast_model),
        fast_model=fast_model,
        answer_model=models.chat(ChatRole.ANSWER),
        retriever=Retriever(settings, models.embeddings(), models.reranker()),
        oversight=Oversight(create_async_engine(database_url(settings), pool_pre_ping=True)),
        model_names=models.names(),
    )
    checkpointer, pool = await open_checkpointer(settings)
    pii_masker()  # Load spaCy now rather than on the first question.
    runtime = Runtime(components, pool, tracer, paused=settings.paused)
    return Assistant(build_graph(components, checkpointer), runtime)


async def open_checkpointer(settings: Settings) -> tuple[AsyncPostgresSaver, AsyncConnectionPool]:
    """LangGraph's Postgres checkpointer, which saves graph state between approval steps."""
    pool = AsyncConnectionPool(
        _conninfo(settings),
        max_size=CHECKPOINT_POOL_SIZE,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await pool.open()
    serde = JsonPlusSerializer(allowed_msgpack_modules=STATE_TYPES)
    checkpointer = AsyncPostgresSaver(pool, serde=serde)  # type: ignore[arg-type]
    await checkpointer.setup()
    return checkpointer, pool


def _initial_state(question: Question) -> AssistantState:
    masked = pii_masker().mask(question.text)
    return {
        "thread_id": str(uuid.uuid4()),
        "visitor_id": question.visitor_id,
        "persona": question.persona,
        "question": masked.text,
        "pii_entities": list(masked.entities),
        "started_at": time.time(),
    }


def _failure_event(state: AssistantState, error: Exception) -> AuditEvent:
    return AuditEvent(
        thread_id=state["thread_id"],
        visitor_id=state["visitor_id"],
        persona=str(state["persona"]),
        event_type="error",
        prompt_version=PROMPT_VERSION,
        question=state["question"],
        pii_entities=tuple(state["pii_entities"]),
        response_kind="error",
        response=type(error).__name__,
        latency_ms=int((time.time() - state["started_at"]) * 1000),
    )


def _conninfo(settings: Settings) -> str:
    url = database_url(settings).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)
