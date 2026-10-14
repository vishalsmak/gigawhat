import pytest

from gigawhat.config import Profile, RerankerKind, Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_profile_defaults_to_cloud() -> None:
    assert make_settings().profile is Profile.CLOUD


def test_database_name_follows_profile() -> None:
    assert make_settings(profile=Profile.OFFLINE).database == "gigawhat_offline"


def test_explicit_database_name_wins_over_profile() -> None:
    assert make_settings(database_name="gigawhat_test").database == "gigawhat_test"


def test_reads_standard_api_key_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")

    key = make_settings().groq_api_key

    assert key is not None
    assert key.get_secret_value() == "gsk-test"


def test_empty_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "")

    assert make_settings().cohere_api_key is None


def test_secrets_are_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    assert "sk-test" not in repr(make_settings())


def test_tracing_off_without_a_langsmith_key() -> None:
    assert make_settings().tracing_enabled is False


def test_tracing_enabled_with_a_langsmith_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")

    assert make_settings().tracing_enabled is True


def test_traces_go_to_the_eu_region_by_default() -> None:
    assert make_settings().langsmith_endpoint == "https://eu.api.smith.langchain.com"


def test_cloud_reranks_with_cohere_by_default() -> None:
    assert make_settings().active_reranker is RerankerKind.COHERE


def test_cloud_can_rerank_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIGAWHAT_RERANKER", "local")

    assert make_settings().active_reranker is RerankerKind.LOCAL


def test_offline_reranks_locally_even_when_cohere_is_configured() -> None:
    settings = make_settings(profile=Profile.OFFLINE, reranker=RerankerKind.COHERE)

    assert settings.active_reranker is RerankerKind.LOCAL
