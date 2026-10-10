from collections.abc import AsyncIterator, Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, delete, insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gigawhat.assistant.evidence import EvidenceCollector, wants_records
from gigawhat.config import Settings
from gigawhat.db import database_url
from gigawhat.records.load import load_records
from gigawhat.retrieval.query import analyse_query
from gigawhat.schema import document_versions, documents

TEST_DOC = "PR-GAS-097"


@pytest.mark.parametrize(
    "question",
    [
        "Anything I should know about G-112?",
        "Is PR-GAS-010 still the current version?",
        "Which procedures are overdue for review?",
        "What happened at Mill Lane last month?",
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
