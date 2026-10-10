"""The HTTP endpoints that work without the assistant running. The client is never entered as a
context manager, so the app's lifespan (which builds the assistant) does not run."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from gigawhat.api import app
from gigawhat.config import get_settings
from gigawhat.ui.visitor import VISITOR_COOKIE


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("GIGAWHAT_PAUSED", "false")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_audit_trail_is_closed_outside_demo_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIGAWHAT_DEMO_MODE", "false")

    assert client.get("/api/audit").status_code == 403


def test_audit_trail_is_empty_for_a_browser_without_a_visitor_id(client: TestClient) -> None:
    assert client.get("/api/audit").json() == []


def test_first_visit_gets_a_visitor_cookie(client: TestClient) -> None:
    assert VISITOR_COOKIE in client.get("/health").cookies


def test_health_reports_the_pause_switch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIGAWHAT_PAUSED", "true")

    assert client.get("/health").json()["status"] == "paused"
