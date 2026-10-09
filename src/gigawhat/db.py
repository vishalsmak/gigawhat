from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Connection, Engine, create_engine, text

from gigawhat.config import Settings

MIGRATIONS_LOCATION = "gigawhat:migrations"


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
