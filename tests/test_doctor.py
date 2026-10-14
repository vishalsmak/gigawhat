from collections.abc import Callable

import httpx
import pytest

from gigawhat.config import Profile, RerankerKind, Settings
from gigawhat.doctor import ModelChecks, Status, check_database, check_tracing
from gigawhat.providers.registry import ChatRole

UNUSED_PORT = 1
GEMINI_KEY = "gemini-test"
CLOUD_KEYS = {"google_api_key": GEMINI_KEY, "openai_api_key": "sk-test"}
Handler = Callable[[httpx.Request], httpx.Response]


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def checks(handler: Handler, **overrides: object) -> ModelChecks:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return ModelChecks(make_settings(**overrides), http)


def known_model(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"name": request.url.path.rsplit("/", 1)[-1]})


def unknown_model(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404, json={"error": "not found"})


def refused_key(request: httpx.Request) -> httpx.Response:
    return httpx.Response(400, json={"error": "API key not valid"})


def ollama_with(*names: str) -> Handler:
    return lambda request: httpx.Response(200, json={"models": [{"name": n} for n in names]})


def refuse_connection(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


def test_cloud_role_shows_its_declared_limits() -> None:
    check = checks(known_model, **CLOUD_KEYS).chat(ChatRole.FAST)

    assert check.status is Status.OK
    assert "gemini:gemini-3.1-flash-lite · 15 requests/min" in check.detail


def test_cloud_role_fails_without_its_key() -> None:
    check = checks(known_model).chat(ChatRole.ANSWER)

    assert check.status is Status.FAIL
    assert "GOOGLE_API_KEY isn't set" in check.detail


def test_cloud_role_fails_when_the_provider_has_no_such_model() -> None:
    check = checks(unknown_model, **CLOUD_KEYS, fast_model="gemini:gemini-9").chat(ChatRole.FAST)

    assert check.status is Status.FAIL
    assert "no model called gemini-9" in check.detail


def test_cloud_role_fails_when_the_key_is_refused() -> None:
    check = checks(refused_key, **CLOUD_KEYS).chat(ChatRole.FAST)

    assert check.status is Status.FAIL
    assert "HTTP 400" in check.detail


def test_gemini_key_is_sent_in_a_header_not_the_url() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return known_model(request)

    checks(record, **CLOUD_KEYS).chat(ChatRole.FAST)

    assert seen[0].headers["x-goog-api-key"] == GEMINI_KEY
    assert GEMINI_KEY not in str(seen[0].url)


def test_cloud_model_without_declared_limits_is_a_warning() -> None:
    check = checks(known_model, **CLOUD_KEYS, fast_model="gemini:gemini-3.5-flash").chat(
        ChatRole.FAST
    )

    assert check.status is Status.WARN


def test_local_role_passes_when_ollama_has_the_model() -> None:
    check = checks(ollama_with("gpt-oss:20b"), profile=Profile.OFFLINE).chat(ChatRole.FAST)

    assert check.status is Status.OK


def test_untagged_ollama_model_counts_as_latest() -> None:
    choice = "ollama:qwen3"
    handler = ollama_with("qwen3:latest")

    check = checks(handler, profile=Profile.OFFLINE, fast_model=choice).chat(ChatRole.FAST)

    assert check.status is Status.OK


def test_local_role_fails_with_a_pull_hint_when_the_model_is_missing() -> None:
    check = checks(ollama_with("llama3:8b"), profile=Profile.OFFLINE).chat(ChatRole.FAST)

    assert check.status is Status.FAIL
    assert "ollama pull gpt-oss:20b" in check.detail


def test_local_role_fails_when_ollama_is_down() -> None:
    check = checks(refuse_connection, profile=Profile.OFFLINE).chat(ChatRole.FAST)

    assert check.status is Status.FAIL


def test_embeddings_fail_without_the_openai_key() -> None:
    check = checks(known_model, google_api_key=GEMINI_KEY).embeddings()

    assert "OPENAI_API_KEY isn't set" in check.detail


def test_cohere_reranker_fails_without_its_key() -> None:
    check = checks(known_model, reranker=RerankerKind.COHERE).reranker()

    assert check.status is Status.FAIL


def test_local_reranker_does_not_need_a_cohere_key() -> None:
    check = checks(known_model, reranker=RerankerKind.LOCAL).reranker()

    assert check.status is Status.OK


def test_gemini_free_tier_fits_an_evidence_request() -> None:
    assert checks(known_model).evidence_budget().status is Status.OK


def test_groq_free_plan_cannot_fit_an_evidence_request() -> None:
    check = checks(known_model, answer_model="groq:openai/gpt-oss-20b").evidence_budget()

    assert check.status is Status.FAIL
    assert "allows 8,000 a minute" in check.detail


def test_local_answer_model_has_no_budget_to_fit() -> None:
    check = checks(known_model, profile=Profile.OFFLINE).evidence_budget()

    assert check.status is Status.OK


@pytest.mark.parametrize("profile", list(Profile))
def test_every_role_is_checked(profile: Profile) -> None:
    names = [check.name for check in checks(known_model, profile=profile).run()]

    assert names == ["fast", "answer", "embeddings", "reranker", "budget"]


def test_tracing_off_is_a_warning_not_a_failure() -> None:
    http = httpx.Client(transport=httpx.MockTransport(known_model))

    assert check_tracing(make_settings(), http).status is Status.WARN


def test_tracing_key_refused_by_the_endpoint_is_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    forbidden = httpx.MockTransport(lambda request: httpx.Response(403))

    check = check_tracing(make_settings(), httpx.Client(transport=forbidden))

    assert check.status is Status.WARN
    assert "key's region" in check.detail


def test_tracing_key_accepted_by_the_endpoint_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    accepted = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))

    assert check_tracing(make_settings(), httpx.Client(transport=accepted)).status is Status.OK


def test_database_check_fails_cleanly_when_unreachable() -> None:
    check = check_database(make_settings(database_port=UNUSED_PORT))

    assert check.status is Status.FAIL
    assert "docker compose up -d db" in check.detail


def test_offline_tracing_check_sends_nothing_even_with_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    sent: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200)

    check_tracing(
        make_settings(profile=Profile.OFFLINE), httpx.Client(transport=httpx.MockTransport(record))
    )

    assert sent == []
