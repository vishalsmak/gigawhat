import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from gigawhat.config import Settings
from gigawhat.db import create_db_engine

TEST_DATABASE = "gigawhat_test"
KEY_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


@pytest.fixture(autouse=True)
def clean_key_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's exported API keys from leaking into tests."""
    for name in KEY_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(_env_file=None, database_name=TEST_DATABASE)


@pytest.fixture(scope="session")
def database(test_settings: Settings) -> Iterator[Engine]:
    engine = create_db_engine(test_settings)
    try:
        with engine.connect():
            pass
    except OperationalError:
        engine.dispose()
        if os.environ.get("GIGAWHAT_REQUIRE_DB"):
            raise
        pytest.skip("Postgres isn't running. Start it with: docker compose up -d db")
    yield engine
    engine.dispose()
