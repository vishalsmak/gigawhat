from collections.abc import Iterator
from datetime import date

import pytest
from rich.console import Console
from typer.testing import CliRunner

from gigawhat.cli import app, versions_table
from gigawhat.config import get_settings
from gigawhat.corpus.catalogue import StoredVersion

runner = CliRunner()
TODAY = date(2026, 10, 9)


def render(stored: StoredVersion) -> str:
    console = Console(width=200, record=True)
    console.print(versions_table([stored], TODAY))
    return console.export_text()


def stored(status: str, review_due: date) -> StoredVersion:
    return StoredVersion(
        doc_id="PR-ELEC-052",
        title="Routine Substation Inspection",
        business_unit="electricity",
        version=4,
        status=status,
        effective_from=date(2024, 3, 4),
        review_due=review_due,
        safety_critical=False,
        chunk_count=9,
    )


@pytest.fixture
def test_database_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GIGAWHAT_DATABASE_NAME", "gigawhat_test")
    monkeypatch.setenv("GIGAWHAT_PROFILE", "cloud")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_approved_version_past_review_is_flagged_overdue() -> None:
    assert "overdue" in render(stored("approved", date(2026, 6, 30)))


def test_superseded_version_is_never_flagged_overdue() -> None:
    assert "overdue" not in render(stored("superseded", date(2026, 2, 1)))


def test_ingest_rejects_a_document_not_in_the_register() -> None:
    result = runner.invoke(app, ["data", "ingest", "--only", "PR-GAS-999"])

    assert result.exit_code == 2


@pytest.mark.integration
@pytest.mark.usefixtures("database", "test_database_settings")
def test_doctor_fails_when_cloud_keys_are_missing() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1


@pytest.mark.integration
@pytest.mark.usefixtures("database", "test_database_settings")
def test_doctor_names_the_missing_keys() -> None:
    result = runner.invoke(app, ["doctor"])

    assert "ANTHROPIC_API_KEY, COHERE_API_KEY" in result.output
