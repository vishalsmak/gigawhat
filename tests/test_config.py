import pytest

from gigawhat.config import Profile, Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_profile_defaults_to_cloud() -> None:
    assert make_settings().profile is Profile.CLOUD


def test_database_name_follows_profile() -> None:
    assert make_settings(profile=Profile.OFFLINE).database == "gigawhat_offline"


def test_explicit_database_name_wins_over_profile() -> None:
    assert make_settings(database_name="gigawhat_test").database == "gigawhat_test"


def test_reads_standard_api_key_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    key = make_settings().anthropic_api_key

    assert key is not None
    assert key.get_secret_value() == "sk-ant-test"


def test_empty_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "")

    assert make_settings().cohere_api_key is None


def test_secrets_are_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    assert "sk-ant-test" not in repr(make_settings())


def test_tracing_needs_both_langfuse_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")

    assert make_settings().tracing_enabled is False


def test_tracing_enabled_with_both_langfuse_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    assert make_settings().tracing_enabled is True
