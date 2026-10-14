import pytest

from gigawhat.config import Profile, Settings
from gigawhat.observability.tracing import create_tracer, langsmith_client


def test_offline_profile_never_traces_even_with_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")

    assert create_tracer(Settings(_env_file=None, profile=Profile.OFFLINE)) is None


def test_cloud_profile_without_a_key_does_not_trace() -> None:
    assert create_tracer(Settings(_env_file=None, profile=Profile.CLOUD)) is None


def test_cloud_profile_traces_to_the_configured_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")

    tracer = create_tracer(Settings(_env_file=None, profile=Profile.CLOUD))

    assert tracer is not None
    assert tracer.project_name == "gigawhat"
    assert tracer.client.api_url == "https://eu.api.smith.langchain.com"


def test_offline_profile_never_gets_a_langsmith_client_even_with_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evaluation runs as a LangSmith experiment only when this returns a client."""
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")

    assert langsmith_client(Settings(_env_file=None, profile=Profile.OFFLINE)) is None


def test_cloud_profile_with_a_key_gets_a_client_for_its_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    client = langsmith_client(Settings(_env_file=None, profile=Profile.CLOUD))

    assert client is not None
    assert client.api_url == "https://api.smith.langchain.com"
