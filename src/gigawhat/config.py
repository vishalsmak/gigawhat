from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BeforeValidator, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Profile(StrEnum):
    """Where models run. Each profile keeps its own database because embeddings differ."""

    CLOUD = "cloud"
    OFFLINE = "offline"


class RerankerKind(StrEnum):
    """Which cross-encoder scores passages. Local needs the `offline` extra (PyTorch)."""

    COHERE = "cohere"
    LOCAL = "local"


class Provider(StrEnum):
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"
    OPENAI = "openai"
    COHERE = "cohere"

    @property
    def runs_locally(self) -> bool:
        return self is Provider.OLLAMA


# OpenAI and Cohere only embed and rerank here.
CHAT_PROVIDERS = frozenset({Provider.GEMINI, Provider.GROQ, Provider.OLLAMA})


@dataclass(frozen=True)
class ModelChoice:
    """A provider and one of its models, written provider:model, e.g. ollama:gpt-oss:20b."""

    provider: Provider
    name: str

    @classmethod
    def parse(cls, text: str) -> "ModelChoice":
        provider, _, name = text.partition(":")
        if not name:
            raise ValueError(f"expected provider:model, e.g. ollama:gpt-oss:20b, not {text!r}")
        return cls(Provider(provider), name)

    def __str__(self) -> str:
        return f"{self.provider}:{self.name}"


def _parse_choice(value: Any) -> Any:
    return ModelChoice.parse(value) if isinstance(value, str) else value


ConfiguredChoice = Annotated[ModelChoice, BeforeValidator(_parse_choice)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GIGAWHAT_", env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    profile: Profile = Profile.CLOUD

    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "gigawhat"
    database_password: SecretStr = SecretStr("gigawhat")
    database_name: str | None = None

    data_dir: Path = Path("data")
    # Demo mode: visitors pick personas without signing in and only see their own requests.
    demo_mode: bool = True
    questions_per_hour: int = 30
    # Operations' stop switch: when true the assistant answers nothing.
    paused: bool = False
    # The server's structured logs; the CLI logs warnings only, beside its own output.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ollama_url: str = "http://localhost:11434"
    # Unset, each chat role uses its profile's default model; see providers.registry.
    fast_model: ConfiguredChoice | None = None
    answer_model: ConfiguredChoice | None = None
    # Read only on the cloud profile; see active_reranker.
    reranker: RerankerKind = RerankerKind.COHERE

    # Standard names, so LangChain integrations can read the same variables.
    google_api_key: SecretStr | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    cohere_api_key: SecretStr | None = Field(default=None, validation_alias="COHERE_API_KEY")
    langsmith_api_key: SecretStr | None = Field(default=None, validation_alias="LANGSMITH_API_KEY")
    langsmith_endpoint: str = Field(
        default="https://eu.api.smith.langchain.com", validation_alias="LANGSMITH_ENDPOINT"
    )
    langsmith_project: str = Field(default="gigawhat", validation_alias="LANGSMITH_PROJECT")

    @field_validator("fast_model", "answer_model")
    @classmethod
    def _serves_chat(cls, choice: ModelChoice | None) -> ModelChoice | None:
        if choice and choice.provider not in CHAT_PROVIDERS:
            raise ValueError(f"{choice} isn't a chat model; use gemini, groq or ollama")
        return choice

    @model_validator(mode="after")
    def _offline_models_stay_on_this_machine(self) -> Self:
        if self.profile is Profile.OFFLINE:
            remote = [
                str(choice)
                for choice in (self.fast_model, self.answer_model)
                if choice and not choice.provider.runs_locally
            ]
            if remote:
                raise ValueError(f"the offline profile sends nothing off this machine: {remote}")
        return self

    @property
    def database(self) -> str:
        return self.database_name or f"gigawhat_{self.profile}"

    @property
    def corpus_dir(self) -> Path:
        return self.data_dir / "corpus"

    @property
    def register_path(self) -> Path:
        return self.corpus_dir / "register.yaml"

    @property
    def records_dir(self) -> Path:
        return self.data_dir / "records"

    @property
    def active_reranker(self) -> RerankerKind:
        """Offline always reranks locally, whatever is configured: nothing leaves the machine."""
        return RerankerKind.LOCAL if self.profile is Profile.OFFLINE else self.reranker

    def api_key(self, provider: Provider) -> SecretStr | None:
        """None for providers that run locally and need no key."""
        keys = {
            Provider.GEMINI: self.google_api_key,
            Provider.GROQ: self.groq_api_key,
            Provider.OPENAI: self.openai_api_key,
            Provider.COHERE: self.cohere_api_key,
        }
        return keys.get(provider)


@lru_cache
def get_settings() -> Settings:
    return Settings()
