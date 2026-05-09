"""
SQLAlchemy database connection and session management
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.metrics import Base

# Import conversation models to register them with Base
from app.models import conversation  # noqa: F401
from app.models import claude_code_session  # noqa: F401
from app.core.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)

# Create async engine
database_url = settings.effective_database_url
engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
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


async def init_db():
    """Initialize database tables and Supabase"""
    # Initialize SQLAlchemy tables for the active database URL.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Supabase if configured
    if is_supabase_configured():
        try:
            supabase = get_supabase_client()
            if supabase:
                logger.info("Supabase client initialized for database operations")
        except Exception as e:
            logger.warning(f"Supabase initialization skipped: {e}")


async def close_db():
    """Close database connections"""
    await engine.dispose()
