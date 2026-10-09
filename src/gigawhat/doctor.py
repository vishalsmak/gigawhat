"""Readiness checks behind `gigawhat doctor`."""

from dataclasses import dataclass
from enum import StrEnum

import httpx
from sqlalchemy.exc import OperationalError

from gigawhat.config import Profile, Settings
from gigawhat.db import create_db_engine, current_revision, head_revision, pgvector_version


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
    return [check_database(settings), check_models(settings, http), check_tracing(settings)]


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


def check_models(settings: Settings, http: httpx.Client) -> Check:
    if settings.profile is Profile.OFFLINE:
        return check_ollama(settings, http)
    return check_cloud_keys(settings)


def check_cloud_keys(settings: Settings) -> Check:
    keys = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "COHERE_API_KEY": settings.cohere_api_key,
    }
    missing = [name for name, value in keys.items() if value is None]
    if missing:
        return Check("models", Status.FAIL, f"Cloud profile needs {', '.join(missing)} in .env")
    return Check("models", Status.OK, "Anthropic and Cohere keys set")


def check_ollama(settings: Settings, http: httpx.Client) -> Check:
    try:
        response = http.get(f"{settings.ollama_url}/api/tags")
        response.raise_for_status()
    except httpx.HTTPError:
        return Check(
            "models",
            Status.FAIL,
            f"Ollama isn't answering at {settings.ollama_url}. Install and start it: ollama.com",
        )
    installed = len(response.json().get("models", []))
    return Check("models", Status.OK, f"Ollama running · models installed: {installed}")


def check_tracing(settings: Settings) -> Check:
    if settings.tracing_enabled:
        return Check("tracing", Status.OK, "Langfuse keys set")
    return Check("tracing", Status.WARN, "Langfuse keys not set, so tracing is off")
