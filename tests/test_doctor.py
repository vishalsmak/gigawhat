import httpx
import pytest

from gigawhat.config import Profile, Settings
from gigawhat.doctor import Status, check_database, check_models, check_tracing

UNUSED_PORT = 1


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def ollama_client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_cloud_profile_fails_without_keys() -> None:
    check = check_models(make_settings(), httpx.Client())

    assert check.status is Status.FAIL
    assert "ANTHROPIC_API_KEY, COHERE_API_KEY" in check.detail


def test_cloud_profile_passes_with_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("COHERE_API_KEY", "co-test")

    assert check_models(make_settings(), httpx.Client()).status is Status.OK


def test_offline_profile_passes_when_ollama_answers() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )

    check = check_models(make_settings(profile=Profile.OFFLINE), ollama_client(transport))

    assert check.status is Status.OK
    assert check.detail.endswith("models installed: 1")


def test_offline_profile_fails_when_ollama_is_down() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    check = check_models(
        make_settings(profile=Profile.OFFLINE), ollama_client(httpx.MockTransport(refuse))
    )

    assert check.status is Status.FAIL


def test_tracing_is_a_warning_not_a_failure() -> None:
    assert check_tracing(make_settings()).status is Status.WARN


def test_database_check_fails_cleanly_when_unreachable() -> None:
    check = check_database(make_settings(database_port=UNUSED_PORT))

    assert check.status is Status.FAIL
    assert "docker compose up -d db" in check.detail
