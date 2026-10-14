from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from langchain.agents import create_agent
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import tool
from sqlalchemy import Engine, delete, insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gigawhat.config import Settings
from gigawhat.identity.personas import Persona, profile_of
from gigawhat.records.evidence import (
    FINISHED,
    REQUEST_TOKEN_BUDGET,
    EvidenceCollector,
    RequestBudget,
    wants_records,
)
from gigawhat.records.load import load_records
from gigawhat.retrieval.query import analyse_query
from gigawhat.storage.db import create_reader_engine, database_url
from gigawhat.storage.schema import document_versions, documents

TEST_DOC = "PR-GAS-097"


@pytest.mark.parametrize(
    "question",
    [
        "Anything I should know about G-112?",
        "Is PR-GAS-010 still the current version?",
        "Which procedures are overdue for review?",
        "What happened at Mill Lane last month?",
        "list of documents we have",
        "Which of our procedures are owned by the Head of Health, Safety and Environment?",
    ],
)
def test_questions_about_assets_history_or_document_control_want_records(question: str) -> None:
    assert wants_records(question, analyse_query(question))


def test_question_about_a_procedure_step_does_not_want_records() -> None:
    question = "How high must the vent stack be?"

    assert not wants_records(question, analyse_query(question))


@pytest.fixture
async def collector(test_settings: Settings) -> AsyncIterator[EvidenceCollector]:
    engine: AsyncEngine = create_async_engine(database_url(test_settings))
    yield EvidenceCollector(engine)
    await engine.dispose()


@pytest.fixture
async def electricity_collector(test_settings: Settings) -> AsyncIterator[EvidenceCollector]:
    engine = create_reader_engine(test_settings, profile_of(Persona.ELECTRICITY_CONTROL_ROOM))
    yield EvidenceCollector(engine)
    await engine.dispose()


@pytest.fixture
def loaded_records(database: Engine, records_dir: Path) -> None:
    load_records(database, records_dir)


@pytest.fixture
def overdue_document(database: Engine) -> Iterator[None]:
    with database.begin() as connection:
        connection.execute(
            insert(documents).values(
                doc_id=TEST_DOC,
                title="Test Governor Maintenance",
                doc_type="procedure",
                business_unit="gas",
                owner="Head of Gas Network Operations",
            )
        )
        connection.execute(
            insert(document_versions).values(
                doc_id=TEST_DOC,
                version=1,
                status="approved",
                effective_from=date(2023, 1, 1),
                review_due=date.today() - timedelta(days=1),
                safety_critical=False,
                sites=[],
                asset_classes=[],
                source_path="test.md",
                content_hash="test",
                embedding_model="test",
            )
        )
    yield
    with database.begin() as connection:
        connection.execute(delete(document_versions).where(document_versions.c.doc_id == TEST_DOC))
        connection.execute(delete(documents).where(documents.c.doc_id == TEST_DOC))


@pytest.mark.integration
async def test_alarm_summary_counts_alarms_by_code(
    collector: EvidenceCollector, loaded_records: None
) -> None:
    await collector.recent_alarms("g-112")

    summary = next(item for item in collector.items if item.record_id == "ALM-SUMMARY-G-112")
    assert "1 in total (OUTLET_HIGH x1)" in summary.text


@pytest.mark.integration
async def test_alarm_lookup_on_an_asset_the_persona_cannot_see_gives_no_count(
    electricity_collector: EvidenceCollector, loaded_records: None
) -> None:
    await electricity_collector.recent_alarms("G-112")

    assert electricity_collector.items == []


@pytest.mark.integration
async def test_alarm_lookup_on_a_site_id_gives_no_count(
    collector: EvidenceCollector, loaded_records: None
) -> None:
    await collector.recent_alarms("GPR-MLN")

    assert collector.items == []


@pytest.mark.integration
async def test_register_entry_names_the_document_owner(
    collector: EvidenceCollector, overdue_document: None
) -> None:
    text = await collector.document_register(TEST_DOC)

    assert "owned by Head of Gas Network Operations" in text


@pytest.mark.integration
async def test_register_flags_an_approved_version_past_its_review_date(
    collector: EvidenceCollector, overdue_document: None
) -> None:
    text = await collector.document_register(TEST_DOC.lower())

    assert text.endswith("(review overdue)")


@pytest.mark.integration
async def test_every_register_entry_can_be_cited(
    collector: EvidenceCollector, overdue_document: None
) -> None:
    await collector.document_register(TEST_DOC)

    assert [item.record_id for item in collector.items] == [f"REG-{TEST_DOC}-v1"]


class LookupOnceModel(BaseChatModel):
    """Asks for one lookup, then finishes once it has the result. Counts the requests it gets."""

    requests: int = 0

    @property
    def _llm_type(self) -> str:
        return "lookup-once"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.requests += 1
        if any(isinstance(message, ToolMessage) for message in messages):
            reply = AIMessage(FINISHED)
        else:
            reply = AIMessage("", tool_calls=[{"name": "lookup", "args": {}, "id": "call-1"}])
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[Any, Any]:
        return self


async def requests_sent(budget: int, result_words: int, system_prompt: str = "") -> int:
    @tool
    def lookup() -> str:
        """Look up a record."""
        return "reading " * result_words

    model = LookupOnceModel()
    agent = create_agent(
        model, tools=[lookup], system_prompt=system_prompt, middleware=[RequestBudget(budget)]
    )
    await agent.ainvoke({"messages": [HumanMessage("Anything on T-104?")]})
    return model.requests


async def test_requests_within_the_budget_reach_the_model() -> None:
    assert await requests_sent(REQUEST_TOKEN_BUDGET, result_words=100) == 2


async def test_request_over_the_budget_ends_the_agent_without_sending_it() -> None:
    assert await requests_sent(REQUEST_TOKEN_BUDGET, result_words=20_000) == 1


async def test_budget_counts_the_system_prompt() -> None:
    assert await requests_sent(budget=1_000, result_words=0, system_prompt="rule " * 5_000) == 0
