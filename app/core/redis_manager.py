"""Redis manager — hot-state layer for DurgasOS.

Kernel analogy: RAM / L2 cache manager.
Provides: caching, pub/sub, job progress tracking, distributed locks, rate limits.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Key prefixes (namespacing like filesystem paths)
KEY_CACHE = "cache:"
KEY_JOB = "job:"
KEY_LOCK = "lock:"
KEY_RATE = "rate:"
KEY_SESSION = "session:"
KEY_OS_FEED = "os:feed:"

# Pub/sub channel names
CHAN_OS_NOTIFICATIONS = "os.notifications"
CHAN_WORKFLOW_EVENTS = "workflow.events"
CHAN_SYSTEM_HEALTH = "system.health"

_redis_client = None


async def get_redis():
    """Get or create the shared async Redis client."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.use_redis:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        await client.ping()
        _redis_client = client
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — running without hot-state layer", exc)
        _redis_client = None
    return _redis_client


async def close_redis() -> None:
    """Close the shared Redis connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception as exc:
            logger.warning("Redis close error: %s", exc)
        finally:
            _redis_client = None


# ── Cache layer ──────────────────────────────────────────────────────────────


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Store a JSON-serializable value with a TTL (seconds)."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.setex(KEY_CACHE + key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("cache_set error key=%s: %s", key, exc)


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve a cached value (None if missing or Redis unavailable)."""
    r = await get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(KEY_CACHE + key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("cache_get error key=%s: %s", key, exc)
        return None


async def cache_delete(key: str) -> None:
    """Invalidate a cache entry."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(KEY_CACHE + key)
    except Exception as exc:
        logger.debug("cache_delete error key=%s: %s", key, exc)


# ── Job progress tracking ────────────────────────────────────────────────────


async def job_set_progress(
    job_id: str,
    status: str,
    progress: int = 0,
    meta: Optional[Dict] = None,
    ttl: int = 3600,
) -> None:
    """Persist live job state to Redis (visible to polling frontend)."""
    r = await get_redis()
    if r is None:
        return
    data = {"status": status, "progress": progress, "meta": meta or {}}
    try:
        await r.setex(KEY_JOB + job_id, ttl, json.dumps(data))
        # Also publish to pub/sub so subscribed clients get instant push
        await r.publish(CHAN_WORKFLOW_EVENTS, json.dumps({"job_id": job_id, **data}))
    except Exception as exc:
        logger.debug("job_set_progress error job=%s: %s", job_id, exc)


async def job_get_progress(job_id: str) -> Optional[Dict]:
    """Fetch current job state from Redis."""
    r = await get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(KEY_JOB + job_id)
        return json.loads(raw) if raw is not None else None
    except Exception:
        return None


# ── Distributed lock ─────────────────────────────────────────────────────────


class RedisLock:
    """Simple SET NX + TTL distributed mutex."""

    def __init__(self, key: str, ttl: int = 30):
        self.key = KEY_LOCK + key
        self.ttl = ttl
        self._redis = None

    async def __aenter__(self):
        self._redis = await get_redis()
        if self._redis is None:
            return self
        acquired = await self._redis.set(self.key, "1", nx=True, ex=self.ttl)
        if not acquired:
            raise RuntimeError(f"Could not acquire lock: {self.key}")
        return self

    async def __aexit__(self, *args):
        if self._redis is not None:
            try:
                await self._redis.delete(self.key)
            except Exception:
                pass


# ── Pub/Sub helpers ──────────────────────────────────────────────────────────


async def publish(channel: str, message: Any) -> None:
    """Publish a message to a Redis pub/sub channel."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.publish(channel, json.dumps(message, default=str))
    except Exception as exc:
        logger.debug("redis_publish error channel=%s: %s", channel, exc)


async def subscribe(channel: str) -> AsyncIterator[Any]:
    """Subscribe to a Redis pub/sub channel and yield decoded messages."""
    r = await get_redis()
    if r is None:
        return
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    yield message["data"]
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


# ── Sliding-window rate limiter ───────────────────────────────────────────────


async def rate_check(identifier: str, limit: int, window_seconds: int = 60) -> bool:
    """Returns True if the request is allowed, False if rate limited."""
    r = await get_redis()
    if r is None:
        return True  # fail open when Redis is down
    key = KEY_RATE + identifier
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = results[0]
        return count <= limit
    except Exception:
        return True  # fail open
