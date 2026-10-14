"""Wires the ingestion pipeline for the current profile."""

from gigawhat.config import Settings
from gigawhat.corpus.chunking import CHUNK_MAX_TOKENS, CHUNK_TOKENIZER, DoclingChunker
from gigawhat.corpus.ingest import Ingestor
from gigawhat.db import create_db_engine
from gigawhat.providers.registry import ModelRegistry


def build_ingestor(settings: Settings) -> Ingestor:
    models = ModelRegistry(settings)
    return Ingestor(
        engine=create_db_engine(settings),
        chunker=DoclingChunker(CHUNK_TOKENIZER, CHUNK_MAX_TOKENS),
        embeddings=models.embeddings(),
        embedding_model=models.embedding_model().choice.name,
        corpus_dir=settings.corpus_dir,
    )
