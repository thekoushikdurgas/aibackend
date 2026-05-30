"""
SQLAlchemy database connection and session management
"""

import errno
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.metrics import Base

# Import conversation + app user models to register tables on Base.metadata
from app.models import conversation  # noqa: F401
from app.models import claude_code_session  # noqa: F401
from app.models import user as app_user_models  # noqa: F401
from app.models import durgasos_desktop  # noqa: F401
from app.models import roadrash  # noqa: F401
from app.models import sudoku  # noqa: F401
from app.models import library  # noqa: F401
from app.models import pokemon  # noqa: F401

logger = logging.getLogger(__name__)

# Create async engine
database_url = settings.effective_database_url
_connect_args: dict = {}
if "sqlite" in database_url.lower():
    _connect_args = {"check_same_thread": False}
elif "+asyncpg" in database_url or (
    "postgresql" in database_url.lower() and "async" in database_url
):
    _connect_args = {"timeout": 45}

_engine_args: dict[str, Any] = {
    "echo": False,
    "future": True,
    "connect_args": _connect_args,
}

if "sqlite" not in database_url.lower():
    _engine_args.update(
        {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(database_url, **_engine_args)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _root_cause_is_unreachable_postgres(exc: BaseException) -> bool:
    """True when the failure chain ends in refused, timeout, or unreachable host."""
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, ConnectionRefusedError):
            return True
        if isinstance(cur, OSError):
            # Windows: WinError 121 (semaphore timeout) during TCP connect — unreachable or blocked host.
            if getattr(cur, "winerror", None) == 121:
                return True
            code = getattr(cur, "errno", None)
            if code in (
                errno.ECONNREFUSED,
                errno.ENETUNREACH,
                errno.ETIMEDOUT,
                10061,  # WSAECONNREFUSED (Windows)
                10060,  # WSAETIMEDOUT (Windows)
            ):
                return True
        cur = cur.__cause__
    return False


async def init_db():
    """Initialize database tables (SQLAlchemy / SQLite or Postgres)."""
    # Initialize SQLAlchemy tables for the active database URL.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        if _root_cause_is_unreachable_postgres(e):
            raise RuntimeError(
                "Cannot reach PostgreSQL at DATABASE_URL (refused, timeout, or "
                "unreachable). Open firewall/security groups for the host and port, "
                "start local Postgres (e.g. Compose with POSTGRES_EXTERNAL_PORT), "
                "or set DATABASE_URL=sqlite+aiosqlite:///./data/durgasai.db in .env."
            ) from e
        raise


async def close_db():
    """Close database connections"""
    await engine.dispose()
