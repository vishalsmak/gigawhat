"""The assistant as the UI and API see it: ask, approve, look up outcomes and the audit trail."""

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine

from gigawhat.assistant import responses
from gigawhat.assistant.graph import STATE_TYPES, AssistantState, Components, build_graph
from gigawhat.assistant.oversight import Approval, DecisionRequest, Oversight
from gigawhat.assistant.pii import pii_masker
from gigawhat.assistant.rails import InputRails
from gigawhat.assistant.responses import Response
from gigawhat.config import Settings
from gigawhat.db import database_url
from gigawhat.models import (
    RERANK_MODELS,
    chat_model_name,
    create_answer_model,
    create_fast_model,
    embedding_model,
)
from gigawhat.personas import Persona
from gigawhat.retrieval.service import build_retriever
from gigawhat.tracing import create_tracer

CHECKPOINT_POOL_SIZE = 10
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
    tracer: BaseCallbackHandler | None = None
    paused: bool = False


class Assistant:
    def __init__(self, graph: CompiledStateGraph[Any], runtime: Runtime) -> None:
        self._graph = graph
        self._runtime = runtime
        self._components = runtime.components

    @property
    def oversight(self) -> Oversight:
        return self._components.oversight

    async def ask(self, question: Question, on_step: StepListener | None = None) -> Turn:
        """Personal data is masked here, before the question enters graph state, which is
        saved to Postgres."""
        if self._runtime.paused:
            return Turn(thread_id="", response=responses.paused(), tier=None)
        masked = pii_masker().mask(question.text)
        thread_id = str(uuid.uuid4())
        state: AssistantState = {
            "thread_id": thread_id,
            "visitor_id": question.visitor_id,
            "persona": question.persona,
            "question": masked.text,
            "pii_entities": list(masked.entities),
            "started_at": time.time(),
        }
        config = self._config(thread_id, question.persona)
        async for update in self._graph.astream(state, config, stream_mode="updates"):
            for node in update:
                if on_step and node in STEP_LABELS:
                    await on_step(STEP_LABELS[node])
        return await self._turn(thread_id)

    async def pending_approvals(self, persona: Persona, visitor_id: str | None) -> list[Approval]:
        return await self.oversight.pending_for(persona, visitor_id)

    async def decide(self, request: DecisionRequest) -> Turn:
        approval = await self.oversight.decide(request)
        resume = {
            "decision": request.decision.value,
            "decider_persona": request.decider_persona.value,
            "note": request.note,
        }
        config = self._config(approval.thread_id, request.decider_persona)
        await self._graph.ainvoke(Command(resume=resume), config)
        return await self._turn(approval.thread_id)

    async def outcome(self, thread_id: str) -> Turn:
        return await self._turn(thread_id)

    async def aclose(self) -> None:
        await self._components.retriever.aclose()
        await self._runtime.pool.close()

    def _config(self, thread_id: str, persona: Persona | None = None) -> Any:
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        if self._runtime.tracer is not None:
            config["callbacks"] = [self._runtime.tracer]
            config["metadata"] = {
                "langfuse_session_id": thread_id,
                "langfuse_tags": [str(persona)] if persona else [],
            }
        return config

    async def _turn(self, thread_id: str) -> Turn:
        snapshot = await self._graph.aget_state(self._config(thread_id))
        values: dict[str, Any] = snapshot.values
        tier = values.get("tier")
        return Turn(thread_id, values["response"], str(tier) if tier else None)


async def create_assistant(settings: Settings) -> Assistant:
    fast_model = create_fast_model(settings)
    components = Components(
        rails=InputRails(fast_model),
        fast_model=fast_model,
        answer_model=create_answer_model(settings),
        retriever=build_retriever(settings),
        oversight=Oversight(create_async_engine(database_url(settings), pool_pre_ping=True)),
        model_names={
            "chat": chat_model_name(settings),
            "embeddings": embedding_model(settings).name,
            "reranker": RERANK_MODELS[settings.profile],
        },
    )
    checkpointer, pool = await open_checkpointer(settings)
    pii_masker()  # Load spaCy now rather than on the first question.
    runtime = Runtime(components, pool, create_tracer(settings), paused=settings.paused)
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


def _conninfo(settings: Settings) -> str:
    url = database_url(settings).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)
