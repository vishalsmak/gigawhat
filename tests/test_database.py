import pytest
from sqlalchemy import Engine

from gigawhat.config import Settings
from gigawhat.db import current_revision, head_revision, pgvector_version, upgrade_to_head
from gigawhat.doctor import Status, check_database

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def migrated(database: Engine, test_settings: Settings) -> None:
    upgrade_to_head(test_settings)


def test_upgrade_reaches_latest_revision(database: Engine, test_settings: Settings) -> None:
    with database.connect() as connection:
        assert current_revision(connection) == head_revision(test_settings)


def test_upgrade_enables_pgvector(database: Engine) -> None:
    with database.connect() as connection:
        assert pgvector_version(connection) is not None


def test_doctor_reports_migrated_database_as_ready(test_settings: Settings) -> None:
    assert check_database(test_settings).status is Status.OK
