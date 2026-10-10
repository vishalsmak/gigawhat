from collections.abc import AsyncIterator, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from sqlalchemy import Engine, text

from gigawhat.config import Settings
from gigawhat.corpus.chunking import SectionChunk
from gigawhat.corpus.ingest import Ingestor
from gigawhat.corpus.register import DocumentEntry
from gigawhat.models import embedding_model
from gigawhat.personas import Persona
from gigawhat.retrieval.search import MIN_RELEVANCE, Retriever

pytestmark = pytest.mark.integration

VENT_V1 = "6.2 Vent stack\nFit the vent stack at least 2 m above ground with a 3 m exclusion zone."
VENT_V2 = (
    "6.2 Vent stack\nFit the vent stack at least 2.5 m above ground with a 5 m exclusion zone."
)
EARTHING = (
    "6.3 Earthing\nApply circuit main earths to the 11 kV feeder FDR-ASH-07 at every isolation."
)
DRAFT = "6.1 Live working\nLive working on low voltage equipment is permitted with insulated tools."
FUTURE = "6.1 Odorant\nCheck the odorant level at the station outlet every week with an analyser."
SHARED = "6.1 Check-in\nLone workers check in with the controller every hour during the shift."


class HeadingChunker:
    """First line of each paragraph is its heading, so every paragraph is its own section."""

    def split(self, path: Path) -> list[SectionChunk]:
        sections = []
        for paragraph in path.read_text().split("\n\n"):
            heading, body = paragraph.split("\n", 1)
            sections.append(SectionChunk(("6 Procedure", heading), body))
        return sections


class WordOverlapReranker:
    """Fraction of the question's longer words found in the passage: crude but deterministic."""

    def score(self, question: str, documents: Sequence[Document]) -> list[float]:
        words = {word.strip("?.,").lower() for word in question.split() if len(word) > 3}
        return [
            sum(word in document.page_content.lower() for word in words) / max(len(words), 1)
            for document in documents
        ]


def entry(doc_id: str, unit: str, versions: list[dict[str, Any]]) -> DocumentEntry:
    return DocumentEntry.model_validate(
        {
            "doc_id": doc_id,
            "title": f"Test {doc_id}",
            "business_unit": unit,
            "doc_type": "procedure",
            "owner": "Head of Operations",
            "versions": versions,
        }
    )


def version(doc_id: str, number: int, status: str, effective: date) -> dict[str, Any]:
    return {
        "version": number,
        "status": status,
        "effective_from": effective,
        "review_due": effective + timedelta(days=1000),
        "approver": "Safety Manager",
        "safety_critical": True,
        "sites": [],
        "asset_classes": [],
        "file": f"{doc_id}_v{number}.md",
    }


CORPUS = [
    (
        entry(
            "PR-GAS-099",
            "gas",
            [
                version("PR-GAS-099", 1, "superseded", date(2022, 1, 1)),
                version("PR-GAS-099", 2, "approved", date(2026, 1, 1)),
            ],
        ),
        {1: VENT_V1, 2: VENT_V2},
    ),
    (
        entry(
            "PR-ELEC-099", "electricity", [version("PR-ELEC-099", 1, "approved", date(2025, 1, 1))]
        ),
        {1: EARTHING},
    ),
    (
        entry("PR-ELEC-098", "electricity", [version("PR-ELEC-098", 1, "draft", date(2026, 1, 1))]),
        {1: DRAFT},
    ),
    (
        entry(
            "PR-GAS-098",
            "gas",
            [version("PR-GAS-098", 1, "approved", date.today() + timedelta(days=30))],
        ),
        {1: FUTURE},
    ),
    (
        entry("PR-CORP-099", "shared", [version("PR-CORP-099", 1, "approved", date(2024, 1, 1))]),
        {1: SHARED},
    ),
]


@pytest.fixture(scope="module")
def corpus(
    database: Engine, test_settings: Settings, tmp_path_factory: pytest.TempPathFactory
) -> None:
    corpus_dir = tmp_path_factory.mktemp("corpus")
    with database.begin() as connection:
        connection.execute(text("TRUNCATE documents CASCADE"))
    ingestor = Ingestor(
        engine=database,
        chunker=HeadingChunker(),
        embeddings=DeterministicFakeEmbedding(size=embedding_model(test_settings).dimensions),
        embedding_model="fake",
        corpus_dir=corpus_dir,
    )
    for document, texts in CORPUS:
        for number, content in texts.items():
            (corpus_dir / f"{document.doc_id}_v{number}.md").write_text(content)
        ingestor.ingest_document(document)


@pytest.fixture
async def retriever(corpus: None, test_settings: Settings) -> AsyncIterator[Retriever]:
    size = embedding_model(test_settings).dimensions
    retriever = Retriever(
        test_settings, DeterministicFakeEmbedding(size=size), WordOverlapReranker()
    )
    yield retriever
    await retriever.aclose()


async def doc_ids_for(retriever: Retriever, question: str, persona: Persona) -> set[str]:
    result = await retriever.retrieve(question, persona)
    return {passage.doc_id for passage in result.passages}


async def test_gas_persona_never_sees_electricity_documents(retriever: Retriever) -> None:
    found = await doc_ids_for(
        retriever, "earths on the 11 kV feeder FDR-ASH-07", Persona.GAS_FIELD_ENGINEER
    )

    assert "PR-ELEC-099" not in found


async def test_electricity_persona_finds_its_own_documents(retriever: Retriever) -> None:
    found = await doc_ids_for(
        retriever, "earths on the 11 kV feeder FDR-ASH-07", Persona.ELECTRICITY_CONTROL_ROOM
    )

    assert "PR-ELEC-099" in found


async def test_shared_documents_are_visible_to_every_unit(retriever: Retriever) -> None:
    found = await doc_ids_for(retriever, "lone workers check in", Persona.ELECTRICITY_CONTROL_ROOM)

    assert "PR-CORP-099" in found


async def test_superseded_version_is_never_returned(retriever: Retriever) -> None:
    result = await retriever.retrieve("vent stack height", Persona.GAS_FIELD_ENGINEER)

    assert {(p.doc_id, p.version) for p in result.passages if p.doc_id == "PR-GAS-099"} == {
        ("PR-GAS-099", 2)
    }


async def test_draft_is_never_returned_even_to_the_document_controller(
    retriever: Retriever,
) -> None:
    found = await doc_ids_for(
        retriever, "live working insulated tools", Persona.DOCUMENT_CONTROLLER
    )

    assert "PR-ELEC-098" not in found


async def test_version_not_yet_in_effect_is_not_returned(retriever: Retriever) -> None:
    found = await doc_ids_for(retriever, "odorant level analyser", Persona.GAS_FIELD_ENGINEER)

    assert "PR-GAS-098" not in found


async def test_naming_a_document_restricts_results_to_it(retriever: Retriever) -> None:
    found = await doc_ids_for(
        retriever, "What does PR-CORP-099 say about check-ins?", Persona.GAS_FIELD_ENGINEER
    )

    assert found == {"PR-CORP-099"}


async def test_unrelated_question_is_not_enough_evidence(retriever: Retriever) -> None:
    result = await retriever.retrieve("recipe for chocolate brownies", Persona.GAS_FIELD_ENGINEER)

    assert not result.sufficient


async def test_relevant_question_is_enough_evidence(retriever: Retriever) -> None:
    result = await retriever.retrieve("vent stack exclusion zone", Persona.GAS_FIELD_ENGINEER)

    assert result.passages[0].relevance >= MIN_RELEVANCE


async def test_passage_cites_document_version_and_section(retriever: Retriever) -> None:
    result = await retriever.retrieve("vent stack exclusion zone", Persona.GAS_FIELD_ENGINEER)

    assert result.passages[0].citation == "PR-GAS-099 v2 §6.2"
