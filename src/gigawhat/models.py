"""Model choices per profile. Everything that depends on which model runs reads from here."""

from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from gigawhat.config import Profile, RerankerKind, Settings
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
    Profile.CLOUD: EmbeddingModel("text-embedding-3-small", 1536),
    Profile.OFFLINE: EmbeddingModel("qwen3-embedding:0.6b", 1024),
}
# The same open model on both profiles: Groq hosts the weights Ollama runs locally, so prompts
# and thresholds tuned on one carry over to the other.
GROQ_CHAT_MODEL = "openai/gpt-oss-20b"
OLLAMA_CHAT_MODEL = "gpt-oss:20b"
FAST_MAX_TOKENS = 2048
ANSWER_MAX_TOKENS = 16000

RERANK_MODELS = {
    RerankerKind.COHERE: "rerank-v3.5",
    RerankerKind.LOCAL: "BAAI/bge-reranker-v2-m3",
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
    return OpenAIEmbeddings(model=model.name, openai_api_key=settings.openai_api_key)


def create_reranker(settings: Settings) -> Reranker:
    kind = settings.active_reranker
    if kind is RerankerKind.LOCAL:
        return LocalReranker(RERANK_MODELS[kind])
    return CohereReranker(RERANK_MODELS[kind], settings.cohere_api_key)


def create_fast_model(settings: Settings) -> BaseChatModel:
    """For short judgements: safety tier and input checks."""
    if settings.profile is Profile.OFFLINE:
        return ChatOllama(
            model=OLLAMA_CHAT_MODEL, base_url=settings.ollama_url, reasoning="low", temperature=0
        )
    return _groq(settings, reasoning="low", max_tokens=FAST_MAX_TOKENS)


def create_answer_model(settings: Settings) -> BaseChatModel:
    """For gathering evidence and writing cited answers."""
    if settings.profile is Profile.OFFLINE:
        return ChatOllama(
            model=OLLAMA_CHAT_MODEL, base_url=settings.ollama_url, reasoning="medium", temperature=0
        )
    return _groq(settings, reasoning="medium", max_tokens=ANSWER_MAX_TOKENS)


def chat_model_name(settings: Settings) -> str:
    return OLLAMA_CHAT_MODEL if settings.profile is Profile.OFFLINE else GROQ_CHAT_MODEL


def _groq(settings: Settings, *, reasoning: str, max_tokens: int) -> ChatGroq:
    # Reasoning tokens count towards max_tokens on Groq.
    return ChatGroq(
        model_name=GROQ_CHAT_MODEL,
        groq_api_key=settings.groq_api_key,
        reasoning_effort=reasoning,
        temperature=0,
        max_tokens=max_tokens,
    )
