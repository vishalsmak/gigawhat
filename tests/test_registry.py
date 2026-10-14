import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from gigawhat.config import CHAT_PROVIDERS, ModelChoice, Profile, Provider, Settings
from gigawhat.providers.registry import ROLE_SETTINGS, ChatRole, ModelRegistry

EXAMPLE_CHAT_MODELS = {
    Provider.GEMINI: ("gemini-3.5-flash-lite", ChatGoogleGenerativeAI),
    Provider.GROQ: ("openai/gpt-oss-20b", ChatGroq),
    Provider.OLLAMA: ("gpt-oss:20b", ChatOllama),
}


def registry(**overrides: object) -> ModelRegistry:
    settings = Settings(
        _env_file=None,
        google_api_key="gemini-test",
        groq_api_key="gsk-test",
        **overrides,  # type: ignore[arg-type]
    )
    return ModelRegistry(settings)


def test_cloud_fast_role_defaults_to_gemini_flash_lite() -> None:
    assert registry().chat_choice(ChatRole.FAST) == ModelChoice(
        Provider.GEMINI, "gemini-3.1-flash-lite"
    )


def test_cloud_roles_use_different_models_so_each_has_its_own_quota() -> None:
    models = registry()

    assert models.chat_choice(ChatRole.FAST) != models.chat_choice(ChatRole.ANSWER)


def test_offline_roles_run_on_ollama() -> None:
    models = registry(profile=Profile.OFFLINE)

    assert {models.chat_choice(role).provider for role in ChatRole} == {Provider.OLLAMA}


def test_configured_model_replaces_the_default() -> None:
    models = registry(answer_model="groq:openai/gpt-oss-20b")

    assert models.chat_choice(ChatRole.ANSWER) == ModelChoice(Provider.GROQ, "openai/gpt-oss-20b")


@pytest.mark.parametrize("provider", sorted(CHAT_PROVIDERS))
def test_every_chat_provider_has_an_adapter(provider: Provider) -> None:
    name, chat_class = EXAMPLE_CHAT_MODELS[provider]

    model = registry(fast_model=f"{provider}:{name}").chat(ChatRole.FAST)

    assert isinstance(model, chat_class)


def test_gemini_answer_model_gets_the_roles_reasoning_effort() -> None:
    model = registry().chat(ChatRole.ANSWER)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.reasoning_effort == ROLE_SETTINGS[ChatRole.ANSWER].effort == "medium"


def test_roles_on_the_same_model_share_its_rate_limiter() -> None:
    same = "gemini:gemini-3.5-flash-lite"
    models = registry(fast_model=same, answer_model=same)

    fast, answer = models.chat(ChatRole.FAST), models.chat(ChatRole.ANSWER)

    assert fast.rate_limiter is not None
    assert fast.rate_limiter is answer.rate_limiter


def test_roles_on_different_models_are_paced_separately() -> None:
    models = registry()

    assert models.chat(ChatRole.FAST).rate_limiter is not models.chat(ChatRole.ANSWER).rate_limiter


def test_local_model_is_not_paced() -> None:
    assert registry(profile=Profile.OFFLINE).chat(ChatRole.FAST).rate_limiter is None


def test_audit_names_each_role_with_its_provider() -> None:
    names = registry(profile=Profile.OFFLINE).names()

    assert names == {
        "fast": "ollama:gpt-oss:20b",
        "answer": "ollama:gpt-oss:20b",
        "embeddings": "ollama:qwen3-embedding:0.6b",
        "reranker": "local:BAAI/bge-reranker-v2-m3",
    }


@pytest.mark.parametrize(
    ("profile", "dimensions"), [(Profile.CLOUD, 1536), (Profile.OFFLINE, 1024)]
)
def test_embedding_size_follows_the_profile(profile: Profile, dimensions: int) -> None:
    assert registry(profile=profile).embedding_model().dimensions == dimensions


def test_cloud_chat_model_gives_up_on_a_stalled_request() -> None:
    model = registry().chat(ChatRole.FAST)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.timeout == ROLE_SETTINGS[ChatRole.FAST].timeout_seconds
