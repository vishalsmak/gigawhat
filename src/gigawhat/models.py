"""Model choices per profile. Everything that depends on which model runs reads from here."""

from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_cohere import CohereEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

from gigawhat.config import Profile, Settings
from gigawhat.retrieval.rerank import CohereReranker, LocalReranker, Reranker

# Chunk boundaries come from one tokenizer so both profiles split documents identically.
CHUNK_TOKENIZER = "Qwen/Qwen3-Embedding-0.6B"
CHUNK_MAX_TOKENS = 512

# Qwen3 embeddings expect queries, but not documents, to carry a task instruction.
QUERY_INSTRUCTION = (
    "Given a question from a gas or electricity network engineer, retrieve the procedure or "
    "guidance passages that answer it"
)


@dataclass(frozen=True)
class EmbeddingModel:
    name: str
    dimensions: int


EMBEDDING_MODELS = {
    Profile.CLOUD: EmbeddingModel("embed-v4.0", 1536),
    Profile.OFFLINE: EmbeddingModel("qwen3-embedding:0.6b", 1024),
}
CLAUDE_MODEL = "claude-opus-5-5"
OLLAMA_CHAT_MODEL = "gpt-oss:20b"
# Refused requests are retried server-side on a model chosen by refusal category.
CLAUDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"
FAST_MAX_TOKENS = 2048
ANSWER_MAX_TOKENS = 16000

RERANK_MODELS = {
    Profile.CLOUD: "rerank-v3.5",
    Profile.OFFLINE: "BAAI/bge-reranker-v2-m3",
}


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


def embedding_model(settings: Settings) -> EmbeddingModel:
    return EMBEDDING_MODELS[settings.profile]


def create_embeddings(settings: Settings) -> Embeddings:
    model = embedding_model(settings)
    if settings.profile is Profile.OFFLINE:
        ollama = OllamaEmbeddings(model=model.name, base_url=settings.ollama_url)
        return InstructedQueryEmbeddings(ollama, QUERY_INSTRUCTION)
    # client and async_client are built by CohereEmbeddings' own validator.
    return CohereEmbeddings(  # type: ignore[call-arg]
        model=model.name, cohere_api_key=settings.cohere_api_key
    )


def create_reranker(settings: Settings) -> Reranker:
    name = RERANK_MODELS[settings.profile]
    if settings.profile is Profile.OFFLINE:
        return LocalReranker(name)
    return CohereReranker(name, settings.cohere_api_key)


def create_fast_model(settings: Settings) -> BaseChatModel:
    """For short judgements: safety tier and input checks."""
    if settings.profile is Profile.OFFLINE:
        return ChatOllama(
            model=OLLAMA_CHAT_MODEL, base_url=settings.ollama_url, reasoning="low", temperature=0
        )
    return _claude(settings, effort="low", max_tokens=FAST_MAX_TOKENS)


def create_answer_model(settings: Settings) -> BaseChatModel:
    """For gathering evidence and writing cited answers."""
    if settings.profile is Profile.OFFLINE:
        return ChatOllama(
            model=OLLAMA_CHAT_MODEL, base_url=settings.ollama_url, reasoning="medium", temperature=0
        )
    return _claude(settings, effort="high", max_tokens=ANSWER_MAX_TOKENS)


def chat_model_name(settings: Settings) -> str:
    return OLLAMA_CHAT_MODEL if settings.profile is Profile.OFFLINE else CLAUDE_MODEL


def _claude(settings: Settings, *, effort: str, max_tokens: int) -> ChatAnthropic:
    # Opus 5.5 always thinks; effort is the only depth control.
    return ChatAnthropic(
        model=CLAUDE_MODEL,
        api_key=settings.anthropic_api_key,
        effort=effort,
        max_tokens=max_tokens,
        betas=[CLAUDE_FALLBACK_BETA],
        model_kwargs={"fallbacks": "default"},
    )
