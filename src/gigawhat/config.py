from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Profile(StrEnum):
    """Where models run. Each profile keeps its own database because embeddings differ."""

    CLOUD = "cloud"
    OFFLINE = "offline"


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

    ollama_url: str = "http://localhost:11434"

    # Standard names, so LangChain integrations can read the same variables.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    cohere_api_key: SecretStr | None = Field(default=None, validation_alias="COHERE_API_KEY")
    langfuse_public_key: str | None = Field(default=None, validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: SecretStr | None = Field(
        default=None, validation_alias="LANGFUSE_SECRET_KEY"
    )

    @property
    def database(self) -> str:
        return self.database_name or f"gigawhat_{self.profile}"

    @property
    def tracing_enabled(self) -> bool:
        return self.langfuse_public_key is not None and self.langfuse_secret_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
