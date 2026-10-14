from langchain_core.embeddings import Embeddings

# Qwen3 embeddings expect queries, but not documents, to carry a task instruction.
QUERY_INSTRUCTION = (
    "Given a question from a gas or electricity network engineer, retrieve the procedure or "
    "guidance passages that answer it"
)


class InstructedQueryEmbeddings(Embeddings):
    """Adds a task instruction to queries only, as instruction-tuned embedding models expect."""

    def __init__(self, inner: Embeddings, instruction: str) -> None:
        self._inner = inner
        self._instruction = instruction

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(self._instructed(text))

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._inner.aembed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await self._inner.aembed_query(self._instructed(text))

    def _instructed(self, text: str) -> str:
        return f"Instruct: {self._instruction}\nQuery: {text}"
