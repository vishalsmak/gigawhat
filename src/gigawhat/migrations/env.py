from alembic import context

from gigawhat.config import Settings, get_settings
from gigawhat.db import create_db_engine, database_url

settings: Settings = context.config.attributes.get("settings") or get_settings()


def run_migrations_offline() -> None:
    url = database_url(settings).render_as_string(hide_password=False)
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(settings)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
