"""Shared helpers for Google OAuth-backed REST proxies (ws_methods)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


def coerce_int_param(value: object, default: int) -> int:
    """Coerce a JSON/WebSocket param to ``int``.

    ``bool`` maps to ``default`` so ``true``/``false`` do not become ``1``/``0``.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return int(s, 10)
        except ValueError:
            return default
    if isinstance(value, float):
        if value != value:  # NaN
            return default
        try:
            return int(value)
        except (ValueError, OverflowError):
            return default
    return default


def require_access_token(params: Dict[str, Any]) -> str:
    t = params.get("access_token")
    if not t or not isinstance(t, str) or not t.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "access_token is required",
        )
    return t.strip()


async def google_http_get_json(
    url: str,
    *,
    access_token: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers, params=params)
    except httpx.RequestError as e:
        logger.error("Google API GET failed: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google API request failed: {e}",
        ) from e
    if r.status_code != 200:
        detail = r.text[:500] if r.text else r.reason_phrase
        err_msg = _parse_google_error_message(r)
        logger.warning("Google API error status=%s body=%s", r.status_code, detail)
        raise JSONRPCError(
            JSONRPCErrorCode.PROVIDER_ERROR,
            f"Google API error ({r.status_code}): {(err_msg or detail)[:240]}",
        )
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google API",
        )
    return data


def _google_error_response(r: httpx.Response) -> None:
    detail = r.text[:500] if r.text else r.reason_phrase
    err_msg = _parse_google_error_message(r)
    logger.warning("Google API error status=%s body=%s", r.status_code, detail)
    raise JSONRPCError(
        JSONRPCErrorCode.PROVIDER_ERROR,
        f"Google API error ({r.status_code}): {(err_msg or detail)[:240]}",
    )


async def google_http_post_json(
    url: str,
    *,
    access_token: str,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """POST JSON to a Google REST endpoint; response body must be a JSON object."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                headers=headers,
                params=params,
                json=json_body if json_body is not None else {},
            )
    except httpx.RequestError as e:
        logger.error("Google API POST failed: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google API request failed: {e}",
        ) from e
    if r.status_code not in (200, 201):
        _google_error_response(r)
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google API",
        )
    return data


async def google_http_put_json(
    url: str,
    *,
    access_token: str,
    json_body: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """PUT JSON to a Google REST endpoint; response body must be a JSON object."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.put(
                url,
                headers=headers,
                params=params,
                json=json_body,
            )
    except httpx.RequestError as e:
        logger.error("Google API PUT failed: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google API request failed: {e}",
        ) from e
    if r.status_code != 200:
        _google_error_response(r)
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google API",
        )
    return data


async def google_http_delete(
    url: str,
    *,
    access_token: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> None:
    """DELETE on a Google REST endpoint (204 No Content)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.delete(url, headers=headers, params=params)
    except httpx.RequestError as e:
        logger.error("Google API DELETE failed: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google API request failed: {e}",
        ) from e
    if r.status_code not in (200, 204):
        _google_error_response(r)


def _parse_google_error_message(r: httpx.Response) -> str:
    try:
        payload = r.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict) and isinstance(err.get("message"), str):
                return err["message"]
            if isinstance(err, str):
                return err
    except Exception:
        pass
    return ""
