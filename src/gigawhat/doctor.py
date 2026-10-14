"""Readiness checks behind `gigawhat doctor`."""

from dataclasses import dataclass
from enum import StrEnum
from importlib.util import find_spec

import httpx
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from gigawhat.config import ModelChoice, Profile, Provider, RerankerKind, Settings
from gigawhat.providers.registry import ROLE_SETTINGS, ChatRole, ModelRegistry
from gigawhat.records.evidence import REQUEST_TOKEN_BUDGET
from gigawhat.storage.db import create_db_engine, current_revision, head_revision, pgvector_version

# Looking a model up is free: it uses no tokens and no quota.
MODEL_URLS = {
    Provider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/models/{name}",
    Provider.GROQ: "https://api.groq.com/openai/v1/models/{name}",
    Provider.OPENAI: "https://api.openai.com/v1/models/{name}",
}
KEY_VARIABLES = {
    Provider.GEMINI: "GOOGLE_API_KEY",
    Provider.GROQ: "GROQ_API_KEY",
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.COHERE: "COHERE_API_KEY",
}


class Status(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


def run_checks(settings: Settings, http: httpx.Client) -> list[Check]:
    return [
        check_database(settings),
        *ModelChecks(settings, http).run(),
        check_tracing(settings, http),
    ]


def check_database(settings: Settings) -> Check:
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            revision = current_revision(connection)
            vector = pgvector_version(connection)
    except OperationalError:
        address = f"{settings.database_host}:{settings.database_port}/{settings.database}"
        return Check(
            "database", Status.FAIL, f"Can't reach {address}. Run: docker compose up -d db"
        )
    finally:
        engine.dispose()

    head = head_revision(settings)
    if revision != head:
        return Check(
            "database",
            Status.FAIL,
            f"Schema is at {revision or 'nothing'}, latest is {head}. Run: gigawhat db upgrade",
        )
    return Check("database", Status.OK, f"{settings.database} · pgvector {vector} · schema {head}")


class ModelChecks:
    """A check for each model role, and one that the answer model can take an evidence request.

    Rate limits come from the registry's declarations: no provider reports them through its API.
    """

    def __init__(self, settings: Settings, http: httpx.Client) -> None:
        self._settings = settings
        self._http = http
        self._models = ModelRegistry(settings)

    def run(self) -> list[Check]:
        chat = [self.chat(role) for role in ChatRole]
        return [*chat, self.embeddings(), self.reranker(), self.evidence_budget()]

    def chat(self, role: ChatRole) -> Check:
        choice = self._models.chat_choice(role)
        if problem := self._find(choice):
            return Check(role, Status.FAIL, f"{choice} · {problem}")
        if choice.provider.runs_locally:
            return Check(role, Status.OK, f"{choice} · runs on this machine")
        limits = self._models.limits(role)
        if limits is None:
            return Check(role, Status.WARN, f"{choice} · no declared limits, so calls aren't paced")
        return Check(role, Status.OK, f"{choice} · {limits}")

    def embeddings(self) -> Check:
        choice = self._models.embedding_model().choice
        if problem := self._find(choice):
            return Check("embeddings", Status.FAIL, f"{choice} · {problem}")
        return Check("embeddings", Status.OK, f"{choice}")

    def reranker(self) -> Check:
        kind = self._settings.active_reranker
        name = f"{kind}:{self._models.reranker_name()}"
        if kind is RerankerKind.LOCAL and find_spec("sentence_transformers") is None:
            return Check("reranker", Status.FAIL, f"{name} · needs PyTorch: uv sync --all-extras")
        if kind is RerankerKind.COHERE and self._settings.cohere_api_key is None:
            return Check("reranker", Status.FAIL, f"{name} · {_missing_key(Provider.COHERE)}")
        return Check("reranker", Status.OK, name)

    def evidence_budget(self) -> Check:
        """The answer model gathers records; its requests may use the budget in full, and some
        providers count the tokens reserved for the reply against the limit too."""
        choice = self._models.chat_choice(ChatRole.ANSWER)
        limits = self._models.limits(ChatRole.ANSWER)
        reserved = ROLE_SETTINGS[ChatRole.ANSWER].max_output_tokens
        largest = REQUEST_TOKEN_BUDGET + reserved
        if limits is None:
            return Check("budget", Status.OK, f"{choice} has no tokens-a-minute limit to fit")
        detail = (
            f"an evidence request can need {largest:,} tokens ({REQUEST_TOKEN_BUDGET:,} sent, "
            f"{reserved:,} reserved for the reply); {choice} allows {limits.tokens_per_minute:,} "
            "a minute"
        )
        status = Status.FAIL if largest > limits.tokens_per_minute else Status.OK
        return Check("budget", status, detail)

    def _find(self, choice: ModelChoice) -> str | None:
        """What stops the provider serving the model, or None if nothing does."""
        if choice.provider is Provider.OLLAMA:
            return self._find_in_ollama(choice.name)
        key = self._settings.api_key(choice.provider)
        if key is None:
            return _missing_key(choice.provider)
        url = MODEL_URLS[choice.provider].format(name=choice.name)
        try:
            response = self._http.get(url, headers=_auth_headers(choice.provider, key))
        except httpx.HTTPError:
            return f"can't reach {choice.provider}"
        if response.status_code == httpx.codes.NOT_FOUND:
            return f"{choice.provider} has no model called {choice.name}"
        if response.is_error:
            return f"{choice.provider} refused the request (HTTP {response.status_code})"
        return None

    def _find_in_ollama(self, name: str) -> str | None:
        url = self._settings.ollama_url
        try:
            response = self._http.get(f"{url}/api/tags")
            response.raise_for_status()
        except httpx.HTTPError:
            return f"Ollama isn't answering at {url}. Install and start it: ollama.com"
        installed = {model["name"] for model in response.json().get("models", [])}
        if not installed & {name, f"{name}:latest"}:
            return f"not installed. Run: ollama pull {name}"
        return None


def check_tracing(settings: Settings, http: httpx.Client) -> Check:
    """A key works only in the region it was created in; elsewhere traces are silently lost.
    On the offline profile nothing is checked or sent: tracing never runs there."""
    if settings.profile is Profile.OFFLINE:
        return Check(
            "tracing", Status.OK, "off: the offline profile sends nothing off this machine"
        )
    if settings.langsmith_api_key is None:
        return Check("tracing", Status.WARN, "LANGSMITH_API_KEY not set, so tracing is off")
    endpoint = settings.langsmith_endpoint
    headers = {"x-api-key": settings.langsmith_api_key.get_secret_value()}
    try:
        response = http.get(f"{endpoint}/api/v1/sessions", params={"limit": 1}, headers=headers)
    except httpx.HTTPError:
        return Check("tracing", Status.WARN, f"can't reach LangSmith at {endpoint}")
    if response.is_error:
        return Check(
            "tracing",
            Status.WARN,
            f"{endpoint} refused the key (HTTP {response.status_code}). Is LANGSMITH_ENDPOINT "
            "the key's region?",
        )
    return Check("tracing", Status.OK, f"LangSmith at {endpoint}")


def _missing_key(provider: Provider) -> str:
    return f"{KEY_VARIABLES[provider]} isn't set in .env"


def _auth_headers(provider: Provider, key: SecretStr) -> dict[str, str]:
    if provider is Provider.GEMINI:
        return {"x-goog-api-key": key.get_secret_value()}
    return {"Authorization": f"Bearer {key.get_secret_value()}"}
