"""Short-TTL response cache for GraphQL (Redis when available, else in-process)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Coroutine, TypeVar

from starlette.requests import Request

T = TypeVar("T")

_mem: dict[str, tuple[float, str]] = {}
_lock = asyncio.Lock()


def _monotonic_expiry(ttl_seconds: float) -> float:
    return time.monotonic() + max(0.1, ttl_seconds)


async def _redis(request: Request):
    return getattr(request.app.state, "redis", None)


async def cache_get_json(request: Request, key: str) -> Any | None:
    """Return deserialized JSON or None."""
    r = await _redis(request)
    if r is not None:
        try:
            raw = await r.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception:
            return None

    async with _lock:
        hit = _mem.get(key)
        if not hit:
            return None
        exp, blob = hit
        if time.monotonic() > exp:
            _mem.pop(key, None)
            return None
        try:
            return json.loads(blob)
        except Exception:
            _mem.pop(key, None)
            return None


async def cache_set_json(
    request: Request, key: str, value: Any, ttl_seconds: float
) -> None:
    try:
        blob = json.dumps(value, default=str)
    except (TypeError, ValueError):
        return

    r = await _redis(request)
    if r is not None:
        try:
            await r.set(key, blob, ex=int(max(1, ttl_seconds)))
        except Exception:
            pass
        return

    async with _lock:
        _mem[key] = (_monotonic_expiry(ttl_seconds), blob)


async def cache_delete(request: Request, key: str) -> None:
    r = await _redis(request)
    if r is not None:
        try:
            await r.delete(key)
        except Exception:
            pass
        return
    async with _lock:
        _mem.pop(key, None)


async def cache_invalidate_prefix(request: Request, prefix: str) -> None:
    r = await _redis(request)
    if r is not None:
        try:
            async for key in r.scan_iter(match=f"{prefix}*"):
                await r.delete(key)
        except Exception:
            pass
        return
    async with _lock:
        for k in list(_mem.keys()):
            if k.startswith(prefix):
                _mem.pop(k, None)


async def cached_json_response(
    request: Request,
    key: str,
    ttl_seconds: float,
    factory: Callable[[], Coroutine[Any, Any, Any]],
) -> Any:
    hit = await cache_get_json(request, key)
    if hit is not None:
        return hit
    data = await factory()
    await cache_set_json(request, key, data, ttl_seconds)
    return data
