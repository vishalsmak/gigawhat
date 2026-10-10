"""Hybrid search over current documents, scoped by the persona's row-level security, then reranked.

Search runs against the current_chunks view, so drafts, withdrawn and superseded versions and
documents not yet in effect can never be returned, whatever the question says.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import date

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGEngine, PGVectorStore
from langchain_postgres.v2.hybrid_search_config import HybridSearchConfig, reciprocal_rank_fusion
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from gigawhat.config import Settings
from gigawhat.db import create_reader_engine
from gigawhat.personas import Persona, profile_of
from gigawhat.retrieval.query import QueryAnalysis, analyse_query
from gigawhat.retrieval.rerank import Reranker

SEARCH_VIEW = "current_chunks"
CANDIDATES_PER_SEARCH = 20
CANDIDATES = 24
PASSAGES = 6
# Cross-encoder relevance below which the best passage does not answer the question.
MIN_RELEVANCE = 0.2
METADATA_COLUMNS = [
    "doc_id",
    "version",
    "version_id",
    "title",
    "section_path",
    "doc_type",
    "business_unit",
    "safety_critical",
    "review_due",
    "owner",
    "effective_from",
]
SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\s")
SECTION_TEXT = text(
    "SELECT body FROM current_chunks "
    "WHERE version_id = :version_id AND section_path = :section_path ORDER BY ordinal"
)


@dataclass(frozen=True)
class Revision:
    """A document version that replaced an earlier one."""

    document: str
    effective_from: date


@dataclass(frozen=True)
class Passage:
    doc_id: str
    version: int
    title: str
    section_path: str
    text: str
    relevance: float
    doc_type: str
    business_unit: str
    safety_critical: bool
    review_due: date | None
    owner: str
    effective_from: date | None = None

    @property
    def revision(self) -> Revision | None:
        if self.version == 1 or self.effective_from is None:
            return None
        return Revision(f"{self.doc_id} v{self.version}", self.effective_from)

    @property
    def citation(self) -> str:
        """Human-readable reference, e.g. 'PR-GAS-031 v3 §6.2'."""
        heading = self.section_path.split(" › ")[-1]
        number = SECTION_NUMBER.match(heading)
        where = f"§{number.group(1)}" if number else f"› {heading}"
        return f"{self.doc_id} v{self.version} {where}"

    def review_overdue(self, today: date) -> bool:
        return self.review_due is not None and self.review_due < today


@dataclass(frozen=True)
class RetrievalResult:
    analysis: QueryAnalysis
    passages: tuple[Passage, ...]

    @property
    def sufficient(self) -> bool:
        return bool(self.relevant_passages)

    @property
    def relevant_passages(self) -> tuple[Passage, ...]:
        return tuple(p for p in self.passages if p.relevance >= MIN_RELEVANCE)


def hybrid_config(analysis: QueryAnalysis) -> HybridSearchConfig | None:
    """A fresh config per query. langchain-postgres writes the first query's keywords into a
    store's default config and reuses them, so the store is never given one."""
    if not analysis.keyword_query:
        return None
    return HybridSearchConfig(
        tsv_column="content_tsv",
        tsv_lang="english",
        fts_query=analysis.keyword_query,
        fusion_function=reciprocal_rank_fusion,
        primary_top_k=CANDIDATES_PER_SEARCH,
        secondary_top_k=CANDIDATES_PER_SEARCH,
    )


class Retriever:
    def __init__(self, settings: Settings, embeddings: Embeddings, reranker: Reranker) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._reranker = reranker
        self._engines: dict[Persona, AsyncEngine] = {}
        self._stores: dict[Persona, PGVectorStore] = {}

    async def retrieve(
        self, question: str, persona: Persona, rewrites: tuple[str, ...] = ()
    ) -> RetrievalResult:
        """Searches with the question and any rewrites of it, then reranks every candidate
        against the original question, so a rewrite can only add candidates."""
        analysis = analyse_query(question)
        candidates = await self._search(analysis, persona)
        for rewrite in rewrites:
            candidates += await self._search(analyse_query(rewrite), persona)
        candidates = _unique_by_id(candidates)
        scores = await asyncio.to_thread(self._reranker.score, question, candidates)
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda pair: -pair[1])
        async with self.engine(persona).connect() as connection:
            passages = [
                await _whole_section(connection, document, score)
                for document, score in _best_per_section(ranked)[:PASSAGES]
            ]
        return RetrievalResult(analysis, tuple(passages))

    def engine(self, persona: Persona) -> AsyncEngine:
        """The persona's row-level-security engine, shared with the evidence tools."""
        if persona not in self._engines:
            self._engines[persona] = create_reader_engine(self._settings, profile_of(persona))
        return self._engines[persona]

    async def aclose(self) -> None:
        for engine in self._engines.values():
            await engine.dispose()

    async def _search(self, analysis: QueryAnalysis, persona: Persona) -> list[Document]:
        named_documents = {"doc_id": {"$in": list(analysis.doc_ids)}} if analysis.doc_ids else None
        store = await self._store(persona)
        hits = await store.asimilarity_search_with_score(
            analysis.question,
            k=CANDIDATES,
            filter=named_documents,
            hybrid_search_config=hybrid_config(analysis),
        )
        return [document for document, _ in hits]

    async def _store(self, persona: Persona) -> PGVectorStore:
        if persona not in self._stores:
            self._stores[persona] = await PGVectorStore.create(
                engine=PGEngine.from_engine(self.engine(persona)),
                embedding_service=self._embeddings,
                table_name=SEARCH_VIEW,
                id_column="id",
                content_column="content",
                embedding_column="embedding",
                metadata_columns=METADATA_COLUMNS,
                metadata_json_column=None,
            )
        return self._stores[persona]


def _unique_by_id(candidates: list[Document]) -> list[Document]:
    return list({str(candidate.id): candidate for candidate in candidates}.values())


def _best_per_section(ranked: list[tuple[Document, float]]) -> list[tuple[Document, float]]:
    """Keep the highest-scoring hit from each section; the rest would repeat its text."""
    best: dict[tuple[str, str], tuple[Document, float]] = {}
    for document, score in ranked:
        key = (str(document.metadata["version_id"]), document.metadata["section_path"])
        best.setdefault(key, (document, score))
    return list(best.values())


async def _whole_section(connection: AsyncConnection, document: Document, score: float) -> Passage:
    metadata = document.metadata
    rows = await connection.execute(
        SECTION_TEXT,
        {"version_id": metadata["version_id"], "section_path": metadata["section_path"]},
    )
    return Passage(
        doc_id=metadata["doc_id"],
        version=metadata["version"],
        title=metadata["title"],
        section_path=metadata["section_path"],
        text="\n\n".join(row.body for row in rows),
        relevance=score,
        doc_type=metadata["doc_type"],
        business_unit=metadata["business_unit"],
        safety_critical=metadata["safety_critical"],
        review_due=metadata["review_due"],
        owner=metadata["owner"],
        effective_from=metadata["effective_from"],
    )
