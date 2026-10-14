"""Models by role. Everything that depends on which model runs asks the registry.

Each chat role uses its profile's default unless .env names another, for example
GIGAWHAT_ANSWER_MODEL=gemini:gemini-2.5-flash-lite once a model's daily quota is used up.
Embeddings follow the profile alone: changing them needs another database and a full re-index.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from gigawhat.config import ModelChoice, Profile, Provider, RerankerKind, Settings
from gigawhat.providers.embeddings import QUERY_INSTRUCTION, InstructedQueryEmbeddings
from gigawhat.providers.limits import DECLARED_LIMITS, RateLimits, shared_limiter
from gigawhat.retrieval.rerank import CohereReranker, LocalReranker, Reranker


class ChatRole(StrEnum):
    FAST = "fast"  # Short judgements: input check, safety tier, search rewrites.
    ANSWER = "answer"  # Gathering records and writing cited answers.


@dataclass(frozen=True)
class RoleSettings:
    effort: Literal["low", "medium"]
    # Reasoning tokens count towards this on every provider here.
    max_output_tokens: int
    # Per attempt, for cloud providers: a stalled request is cut off and retried rather than
    # holding the question up (one Gemini call once took 210 seconds). Local models get none,
    # because on a laptop they can take minutes.
    timeout_seconds: float


@dataclass(frozen=True)
class EmbeddingModel:
    choice: ModelChoice
    dimensions: int


ROLE_SETTINGS = {
    ChatRole.FAST: RoleSettings("low", 2048, timeout_seconds=30),
    ChatRole.ANSWER: RoleSettings("medium", 16_000, timeout_seconds=90),
}
OLLAMA_CHAT = ModelChoice(Provider.OLLAMA, "gpt-oss:20b")
DEFAULT_CHAT = {
    # Two models because free-tier quotas are per model, so each role has its own daily quota.
    Profile.CLOUD: {
        ChatRole.FAST: ModelChoice(Provider.GEMINI, "gemini-3.1-flash-lite"),
        ChatRole.ANSWER: ModelChoice(Provider.GEMINI, "gemini-3.5-flash-lite"),
    },
    Profile.OFFLINE: {ChatRole.FAST: OLLAMA_CHAT, ChatRole.ANSWER: OLLAMA_CHAT},
}
EMBEDDING_MODELS = {
    Profile.CLOUD: EmbeddingModel(ModelChoice(Provider.OPENAI, "text-embedding-3-small"), 1536),
    Profile.OFFLINE: EmbeddingModel(ModelChoice(Provider.OLLAMA, "qwen3-embedding:0.6b"), 1024),
}
RERANK_MODELS = {
    RerankerKind.COHERE: "rerank-v3.5",
    RerankerKind.LOCAL: "BAAI/bge-reranker-v2-m3",
}


class ModelRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def chat_choice(self, role: ChatRole) -> ModelChoice:
        configured = {
            ChatRole.FAST: self._settings.fast_model,
            ChatRole.ANSWER: self._settings.answer_model,
        }[role]
        return configured or DEFAULT_CHAT[self._settings.profile][role]

    def chat(self, role: ChatRole) -> BaseChatModel:
        choice = self.chat_choice(role)
        adapters: dict[Provider, Callable[[ModelChoice, RoleSettings], BaseChatModel]] = {
            Provider.GEMINI: self._gemini,
            Provider.GROQ: self._groq,
            Provider.OLLAMA: self._ollama,
        }
        return adapters[choice.provider](choice, ROLE_SETTINGS[role])

    def limits(self, role: ChatRole) -> RateLimits | None:
        return DECLARED_LIMITS.get(self.chat_choice(role))

    def embedding_model(self) -> EmbeddingModel:
        return EMBEDDING_MODELS[self._settings.profile]

    def embeddings(self) -> Embeddings:
        name = self.embedding_model().choice.name
        if self._settings.profile is Profile.OFFLINE:
            ollama = OllamaEmbeddings(model=name, base_url=self._settings.ollama_url)
            return InstructedQueryEmbeddings(ollama, QUERY_INSTRUCTION)
        return OpenAIEmbeddings(model=name, openai_api_key=self._settings.openai_api_key)

    def reranker_name(self) -> str:
        return RERANK_MODELS[self._settings.active_reranker]

    def reranker(self) -> Reranker:
        if self._settings.active_reranker is RerankerKind.LOCAL:
            return LocalReranker(self.reranker_name())
        return CohereReranker(self.reranker_name(), self._settings.cohere_api_key)

    def names(self) -> dict[str, str]:
        """The models behind every answer, as the audit trail records them."""
        chat = {str(role): str(self.chat_choice(role)) for role in ChatRole}
        return chat | {
            "embeddings": str(self.embedding_model().choice),
            "reranker": f"{self._settings.active_reranker}:{self.reranker_name()}",
        }

    def _gemini(self, choice: ModelChoice, role: RoleSettings) -> BaseChatModel:
        # Temperature stays at Gemini 3's default: Google warns that lower values can make it loop.
        return ChatGoogleGenerativeAI(
            model=choice.name,
            google_api_key=self._settings.google_api_key,
            reasoning_effort=role.effort,
            max_output_tokens=role.max_output_tokens,
            timeout=role.timeout_seconds,
            rate_limiter=shared_limiter(choice),
        )

    def _groq(self, choice: ModelChoice, role: RoleSettings) -> BaseChatModel:
        return ChatGroq(
            model_name=choice.name,
            groq_api_key=self._settings.groq_api_key,
            reasoning_effort=role.effort,
            temperature=0,
            max_tokens=role.max_output_tokens,
            request_timeout=role.timeout_seconds,
            rate_limiter=shared_limiter(choice),
        )

    def _ollama(self, choice: ModelChoice, role: RoleSettings) -> BaseChatModel:
        return ChatOllama(
            model=choice.name,
            base_url=self._settings.ollama_url,
            reasoning=role.effort,
            temperature=0,
        )
