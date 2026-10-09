"""Wires the ingestion pipeline for the current profile."""

from gigawhat.config import Settings
from gigawhat.corpus.chunking import DoclingChunker
from gigawhat.corpus.ingest import Ingestor
from gigawhat.db import create_db_engine
from gigawhat.models import (
    CHUNK_MAX_TOKENS,
    CHUNK_TOKENIZER,
    create_embeddings,
    embedding_model,
)


def build_ingestor(settings: Settings) -> Ingestor:
    return Ingestor(
        engine=create_db_engine(settings),
        chunker=DoclingChunker(CHUNK_TOKENIZER, CHUNK_MAX_TOKENS),
        embeddings=create_embeddings(settings),
        embedding_model=embedding_model(settings).name,
        corpus_dir=settings.corpus_dir,
    )
