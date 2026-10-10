"""Builds the retriever for the current profile."""

from gigawhat.config import Settings
from gigawhat.models import create_embeddings, create_reranker
from gigawhat.retrieval.search import Retriever


def build_retriever(settings: Settings) -> Retriever:
    return Retriever(settings, create_embeddings(settings), create_reranker(settings))
