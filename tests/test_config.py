import pytest
from pydantic import ValidationError

from gigawhat.config import ModelChoice, Profile, Provider, RerankerKind, Settings


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


def test_reads_the_gemini_key_from_its_standard_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "gemini-test")

    key = make_settings().api_key(Provider.GEMINI)

    assert key is not None
    assert key.get_secret_value() == "gemini-test"


def test_ollama_needs_no_key() -> None:
    assert make_settings().api_key(Provider.OLLAMA) is None


def test_chat_role_can_be_switched_in_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIGAWHAT_ANSWER_MODEL", "gemini:gemini-2.5-flash-lite")

    assert make_settings().answer_model == ModelChoice(Provider.GEMINI, "gemini-2.5-flash-lite")


def test_model_name_may_contain_colons() -> None:
    assert ModelChoice.parse("ollama:gpt-oss:20b").name == "gpt-oss:20b"


def test_model_choice_without_a_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="provider:model"):
        ModelChoice.parse("gemini-3.5-flash-lite")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="mistral"):
        ModelChoice.parse("mistral:small")


def test_chat_role_rejects_a_provider_without_chat_models() -> None:
    with pytest.raises(ValidationError, match="isn't a chat model"):
        make_settings(fast_model="openai:text-embedding-3-small")


def test_offline_profile_rejects_a_cloud_chat_model() -> None:
    with pytest.raises(ValidationError, match="sends nothing off this machine"):
        make_settings(profile=Profile.OFFLINE, answer_model="gemini:gemini-3.5-flash-lite")


def test_offline_profile_accepts_another_local_chat_model() -> None:
    settings = make_settings(profile=Profile.OFFLINE, fast_model="ollama:qwen3:8b")

    assert settings.fast_model == ModelChoice(Provider.OLLAMA, "qwen3:8b")
