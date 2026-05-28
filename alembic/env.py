"""
Alembic environment configuration
"""

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import your models' Base
from app.models.metrics import Base
from app.config import settings
from app.database.sqlalchemy import _root_cause_is_unreachable_postgres

# this is the Alembic Config object
config = context.config


def _escape_url_for_ini(url: str) -> str:
    """Alembic stores sqlalchemy.url in ConfigParser; % starts interpolation."""
    return url.replace("%", "%%")


# Set the database URL from settings (passwords may contain URL-encoded %2F, %3D, etc.)
config.set_main_option(
    "sqlalchemy.url", _escape_url_for_ini(settings.effective_database_url)
)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def _connect_args_for_url(url: str) -> dict:
    """Driver-specific connect args (timeouts, SQLite thread check)."""
    if "sqlite" in url.lower():
        return {"check_same_thread": False}
    if "+asyncpg" in url or (
        "postgresql" in url.lower() and "async" in url.lower()
    ):
        # Avoid indefinite hangs on Windows (e.g. WinError 121) when host is unreachable.
        return {"timeout": 45}
    return {}


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = settings.effective_database_url
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=_connect_args_for_url(url),
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    except Exception as e:
        if _root_cause_is_unreachable_postgres(e):
            raise RuntimeError(
                "Alembic cannot connect to PostgreSQL (timeout, refused, or unreachable). "
                "Check VPN/firewall/security groups for the host:port in DATABASE_URL, "
                "or use sqlite+aiosqlite:///./data/durgasai.db for local migrations."
            ) from e
        raise
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
