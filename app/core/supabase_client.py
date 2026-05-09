"""
Supabase client initialization and management (sync + async for Realtime).
"""

import asyncio
import logging
from functools import lru_cache
from typing import Optional

from supabase import AsyncClient, Client, acreate_client, create_client
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

from app.config import settings

logger = logging.getLogger(__name__)

# Global Supabase client instances
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None
_async_supabase_client: Optional[AsyncClient] = None
_async_lock: Optional[asyncio.Lock] = None


def _get_async_lock() -> asyncio.Lock:
    global _async_lock
    if _async_lock is None:
        _async_lock = asyncio.Lock()
    return _async_lock


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """
    Get or create Supabase client instance (anon key)
    Returns None if Supabase is not configured
    """
    global _supabase_client

    if not settings.supabase_url or not settings.supabase_anon_key:
        logger.warning("Supabase not configured. URL and anon key required.")
        return None

    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_anon_key,
                options=SyncClientOptions(
                    auto_refresh_token=True, persist_session=False
                ),
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None

    return _supabase_client


@lru_cache()
def get_supabase_admin_client() -> Optional[Client]:
    """
    Get or create Supabase admin client instance (service role key)
    Use only in backend for admin operations
    Returns None if service role key is not configured
    """
    global _supabase_admin_client

    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning(
            "Supabase admin client not configured. Service role key required."
        )
        return None

    if _supabase_admin_client is None:
        try:
            _supabase_admin_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
                options=SyncClientOptions(
                    auto_refresh_token=False, persist_session=False
                ),
            )
            logger.info("Supabase admin client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase admin client: {e}")
            return None

    return _supabase_admin_client


async def get_async_supabase_client() -> Optional[AsyncClient]:
    """
    Async Supabase client (anon key) for Realtime and other async APIs.
    Returns None if Supabase is not configured.
    """
    global _async_supabase_client

    if not settings.supabase_url or not settings.supabase_anon_key:
        return None

    async with _get_async_lock():
        if _async_supabase_client is None:
            try:
                _async_supabase_client = await acreate_client(
                    settings.supabase_url,
                    settings.supabase_anon_key,
                    options=AsyncClientOptions(
                        auto_refresh_token=True, persist_session=False
                    ),
                )
                logger.info("Async Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize async Supabase client: {e}")
                return None

    return _async_supabase_client


async def close_async_supabase_client() -> None:
    """Close async client WebSocket (Realtime) and release singleton."""
    global _async_supabase_client

    async with _get_async_lock():
        if _async_supabase_client is None:
            return
        try:
            await _async_supabase_client.realtime.close()
            logger.info("Async Supabase Realtime disconnected")
        except Exception as e:
            logger.warning(f"Async Supabase Realtime close error: {e}")
        finally:
            _async_supabase_client = None


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured"""
    return bool(settings.supabase_url and settings.supabase_anon_key)


def reset_supabase_clients():
    """Reset Supabase sync client instances (useful for testing). Caller should await close_async_supabase_client() separately."""
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    get_supabase_client.cache_clear()
    get_supabase_admin_client.cache_clear()
