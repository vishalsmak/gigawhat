import pytest

from gigawhat.config import Profile, Settings
from gigawhat.tracing import create_tracer


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
