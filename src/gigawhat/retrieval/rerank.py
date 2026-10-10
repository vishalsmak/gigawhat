"""Cross-encoder reranking: score each candidate passage against the question, 0 to 1."""

from collections.abc import Sequence
from typing import Protocol

from langchain_cohere import CohereRerank
from langchain_core.documents import Document
from pydantic import SecretStr


class Reranker(Protocol):
    def score(self, question: str, documents: Sequence[Document]) -> list[float]:
        """Relevance of each document to the question, in the documents' order."""
        ...


class LocalReranker:
    """An open cross-encoder run on this machine (BAAI/bge-reranker-v2-m3 by default)."""

    def __init__(self, model_name: str) -> None:
        # Imported here: it loads PyTorch, which the cloud profile and migrations don't need.
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)

    def score(self, question: str, documents: Sequence[Document]) -> list[float]:
        if not documents:
            return []
        pairs = [(question, document.page_content) for document in documents]
        return [float(score) for score in self._model.predict(pairs)]


class CohereReranker:
    def __init__(self, model_name: str, api_key: SecretStr | None) -> None:
        self._rerank = CohereRerank(model=model_name, cohere_api_key=api_key)

    def score(self, question: str, documents: Sequence[Document]) -> list[float]:
        if not documents:
            return []
        results = self._rerank.rerank(documents, question, top_n=len(documents))
        scores = [0.0] * len(documents)
        for result in results:
            scores[result["index"]] = float(result["relevance_score"])
        return scores
