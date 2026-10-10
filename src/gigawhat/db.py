from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Connection, Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gigawhat.config import Settings
from gigawhat.personas import PersonaProfile

MIGRATIONS_LOCATION = "gigawhat:migrations"
READER_ROLE = "gigawhat_reader"


def database_url(settings: Settings) -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=settings.database_user,
        password=settings.database_password.get_secret_value(),
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database,
    )


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(database_url(settings), pool_pre_ping=True)


def create_reader_engine(settings: Settings, profile: PersonaProfile) -> AsyncEngine:
    """An engine whose every connection runs as the restricted reader role, scoped to the
    persona's business units. Row-level security does the filtering; with no units, it
    returns nothing."""
    units = ",".join(unit.value for unit in profile.business_units)
    drafts = "on" if profile.sees_drafts else "off"
    options = f"-c role={READER_ROLE} -c app.business_units={units} -c app.include_drafts={drafts}"
    return create_async_engine(
        database_url(settings), pool_pre_ping=True, connect_args={"options": options}
    )


def alembic_config(settings: Settings) -> Config:
    config = Config()
    config.set_main_option("script_location", MIGRATIONS_LOCATION)
    config.attributes["settings"] = settings
    return config


def upgrade_to_head(settings: Settings) -> None:
    command.upgrade(alembic_config(settings), "head")


def head_revision(settings: Settings) -> str | None:
    return ScriptDirectory.from_config(alembic_config(settings)).get_current_head()


def current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def pgvector_version(connection: Connection) -> str | None:
    query = text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    return connection.execute(query).scalar_one_or_none()
