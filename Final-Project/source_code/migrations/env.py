"""Alembic environment for UV Guard (day 17).

URL priority: a connection passed in ``config.attributes["connection"]`` (tests), then
``sqlalchemy.url`` set on the config, then ``src.db.database_url()`` (``DATABASE_URL`` in
``.env``, SQLite fallback with a warning).
"""

from logging.config import fileConfig

from alembic import context
from src.db import Base, database_url, make_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    """Database URL for this run."""
    return config.get_main_option("sqlalchemy.url") or database_url()[0]


def run_migrations_offline() -> None:
    """Emit SQL to stdout (``alembic upgrade head --sql``) without a database."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_url().startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    """Run migrations on an open connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = make_engine(_url())
    with engine.connect() as conn:
        _run(conn)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
