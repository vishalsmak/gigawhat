import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from gigawhat.config import Profile, Settings
from gigawhat.db import create_db_engine, upgrade_to_head

# Chainlit loads ./.env into the process environment when imported, which would hand a
# developer's profile and API keys to every test that follows. Point it at a file that isn't there.
os.environ["CHAINLIT_ENV_FILE"] = "no-such-file.env"

TEST_DATABASE = "gigawhat_test"
KEY_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


@pytest.fixture(autouse=True)
def clean_key_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's exported API keys from leaking into tests."""
    for name in KEY_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Pinned to the cloud profile, whose 1536-dimension schema the test database uses."""
    return Settings(_env_file=None, database_name=TEST_DATABASE, profile=Profile.CLOUD)


@pytest.fixture(scope="session")
def database(test_settings: Settings) -> Iterator[Engine]:
    engine = create_db_engine(test_settings)
    try:
        with engine.connect():
            pass
    except OperationalError:
        engine.dispose()
        if os.environ.get("GIGAWHAT_REQUIRE_DB"):
            raise
        pytest.skip("Postgres isn't running. Start it with: docker compose up -d db")
    upgrade_to_head(test_settings)
    yield engine
    engine.dispose()


RECORD_FILES = {
    "sites.csv": (
        "site_id,name,business_unit,kind,rating\n"
        "GPR-MLN,Mill Lane District Governor,gas,district_governor,MP to LP 75 mbar\n"
    ),
    "assets.csv": (
        "asset_id,site_id,asset_class,description,installed_year,criticality\n"
        "G-112,GPR-MLN,district_governor,MP to LP district governor,2006,high\n"
        "SSV-112,GPR-MLN,slam_shut_valve,Governor slam-shut valve,,high\n"
    ),
    "work_orders.csv": (
        "wo_id,asset_id,work_type,title,status,priority,raised_on,due_on,completed_on,notes\n"
        "WO-1,G-112,planned,Annual maintenance,completed,3,2026-01-05,2026-01-30,2026-01-12,\n"
        "WO-2,G-112,reactive,Investigate outlet creep,open,2,2026-08-20,2026-09-03,,Recurring\n"
    ),
    "inspections.csv": (
        "inspection_id,asset_id,inspected_on,inspection_type,inspector_role,outcome,findings,readings\n"
        "INS-1,G-112,2026-08-14,monthly,Competent Person (Pressure Systems),defects_found,"
        'Outlet creep,"{""outlet_lockup_mbar"": 43.5}"\n'
    ),
    "alarms.csv": (
        "alarm_id,asset_id,raised_at,cleared_at,priority,code,message,value,unit\n"
        "1,G-112,2026-08-14T02:10:00+01:00,2026-08-14T05:40:00+01:00,2,OUTLET_HIGH,"
        "Outlet pressure high,44.0,mbar\n"
    ),
    "incidents.yaml": """
incidents:
  - incident_id: INC-2026-027
    occurred_at: 2026-08-14T02:10:00+01:00
    business_unit: gas
    site_id: GPR-MLN
    asset_id: G-112
    category: equipment_failure
    severity: medium
    riddor_reportable: false
    summary: G-112 outlet pressure creep recurred.
    description: Overnight lock-up pressure rose above the set point.
    immediate_actions: Increased monitoring.
    root_cause: null
    status: open
    linked_procedures: [PR-GAS-010]
""",
}


@pytest.fixture
def records_dir(tmp_path: Path) -> Path:
    for name, content in RECORD_FILES.items():
        (tmp_path / name).write_text(content)
    return tmp_path
