import pytest

from gigawhat.config import Profile, Settings
from gigawhat.tracing import create_tracer


def test_offline_profile_never_traces_even_with_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    assert create_tracer(Settings(_env_file=None, profile=Profile.OFFLINE)) is None


def test_cloud_profile_without_keys_does_not_trace() -> None:
    assert create_tracer(Settings(_env_file=None, profile=Profile.CLOUD)) is None
