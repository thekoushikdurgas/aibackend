"""Google Photos API proxies (server-side; uses user's OAuth access token)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.api.ws_methods.google_ws_util import coerce_int_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth

logger = logging.getLogger(__name__)

PHOTOS_MEDIA_ITEMS = "https://photoslibrary.googleapis.com/v1/mediaItems"
PICKER_SESSIONS = "https://photospicker.googleapis.com/v1/sessions"
PICKER_MEDIA_ITEMS = "https://photospicker.googleapis.com/v1/mediaItems"
PHOTOS_PICKER_SCOPE = "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"
LEGACY_PHOTOS_SCOPE = "https://www.googleapis.com/auth/photoslibrary.readonly"


def _access_token(params: Dict[str, Any]) -> str:
    access_token = params.get("access_token")
    if (
        not access_token
        or not isinstance(access_token, str)
        or not access_token.strip()
    ):
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "access_token is required")
    return access_token.strip()


def _google_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    err = payload.get("error")
    if isinstance(err, dict):
        msg = err.get("message")
        if isinstance(msg, str):
            return msg
    if isinstance(err, str):
        return err
    return ""


def _raise_google_photos_error(
    *,
    response: httpx.Response,
    product: str,
    auth_hint: str,
) -> None:
    detail = response.text[:500] if response.text else response.reason_phrase
    err_msg = _google_error_message(response)
    logger.warning(
        "%s API error status=%s body=%s", product, response.status_code, detail
    )
    combined = f"{err_msg} {detail}".lower()
    if "insufficient authentication scopes" in combined:
        raise JSONRPCError(JSONRPCErrorCode.AUTHORIZATION_ERROR, auth_hint)
    raise JSONRPCError(
        JSONRPCErrorCode.PROVIDER_ERROR,
        f"{product} API error ({response.status_code}): {(err_msg or detail)[:240]}",
    )


async def _token_scopes(access_token: str) -> tuple[list[str], str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
            )
    except Exception:
        return [], ""
    if r.status_code != 200:
        return [], ""
    try:
        body = r.json()
    except ValueError:
        return [], ""
    if not isinstance(body, dict):
        return [], ""
    raw_scope = body.get("scope", "")
    scopes = raw_scope.split() if isinstance(raw_scope, str) else []
    aud = body.get("aud", "")
    return scopes, aud if isinstance(aud, str) else ""


async def handle_google_photos_list(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Legacy Google Photos Library API mediaItems.list proxy.

    Google removed full-library access for photoslibrary.readonly after March 31, 2025.
    Keep this method for compatibility, but the Gallery UI uses the Picker API methods below.
    """
    await require_auth(user, "google_photos.list")
    access_token = _access_token(params)
    page_token = params.get("page_token") or params.get("pageToken")
    page_size = coerce_int_param(
        params.get("page_size", params.get("pageSize", 100)),
        100,
    )
    page_size = max(1, min(100, page_size))

    query: Dict[str, Any] = {"pageSize": page_size}
    if isinstance(page_token, str) and page_token.strip():
        query["pageToken"] = page_token.strip()

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(PHOTOS_MEDIA_ITEMS, headers=headers, params=query)
    except httpx.RequestError as e:
        logger.error("Google Photos request error: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google Photos request failed: {e}",
        ) from e

    if r.status_code != 200:
        detail = r.text[:500] if r.text else r.reason_phrase
        err_msg = _google_error_message(r)
        combined = f"{err_msg} {detail}".lower()
        if "insufficient authentication scopes" in combined:
            scopes, token_aud = await _token_scopes(access_token)
            if any(LEGACY_PHOTOS_SCOPE in s for s in scopes):
                logger.warning(
                    "Google Photos 403 with legacy photoslibrary.readonly scope (aud=%s)",
                    token_aud or "?",
                )
                raise JSONRPCError(
                    JSONRPCErrorCode.PROVIDER_ERROR,
                    "Google Photos no longer allows full-library listing with "
                    f"`{LEGACY_PHOTOS_SCOPE}`. Use the Google Photos Picker flow and "
                    f"re-authenticate with `{PHOTOS_PICKER_SCOPE}`.",
                )
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHORIZATION_ERROR,
                "Google Photos denied this request. Re-authenticate the Google account "
                f"so Gallery can request `{PHOTOS_PICKER_SCOPE}`.",
            )
        raise JSONRPCError(
            JSONRPCErrorCode.PROVIDER_ERROR,
            f"Google Photos API error ({r.status_code}): {(err_msg or detail)[:240]}",
        )

    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google Photos API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google Photos API",
        )
    return {
        "success": True,
        "mediaItems": data.get("mediaItems") or [],
        "nextPageToken": data.get("nextPageToken"),
    }


async def handle_google_photos_picker_create(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Create a Google Photos Picker session."""
    await require_auth(user, "google_photos.picker.create")
    access_token = _access_token(params)
    max_item_count = coerce_int_param(
        params.get("max_item_count", params.get("maxItemCount", 2000)),
        2000,
    )
    max_item_count = max(1, min(2000, max_item_count))
    request_id = params.get("request_id") or params.get("requestId")
    query: Dict[str, Any] = {}
    if isinstance(request_id, str) and request_id.strip():
        query["requestId"] = request_id.strip()

    headers = {"Authorization": f"Bearer {access_token}"}
    body: Dict[str, Any] = {"pickingConfig": {"maxItemCount": str(max_item_count)}}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                PICKER_SESSIONS, headers=headers, params=query, json=body
            )
    except httpx.RequestError as e:
        logger.error("Google Photos Picker create request error: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google Photos Picker request failed: {e}",
        ) from e
    if r.status_code not in (200, 201):
        _raise_google_photos_error(
            response=r,
            product="Google Photos Picker",
            auth_hint=(
                "Google Photos Picker denied this request. Re-authenticate the Google "
                f"account so the token includes `{PHOTOS_PICKER_SCOPE}`, and make sure "
                "the Google Photos Picker API is enabled in the OAuth client project."
            ),
        )
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google Photos Picker API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google Photos Picker API",
        )
    return {"success": True, "session": data}


async def handle_google_photos_picker_get(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Get a Google Photos Picker session."""
    await require_auth(user, "google_photos.picker.get")
    access_token = _access_token(params)
    session_id = params.get("session_id") or params.get("sessionId")
    if not isinstance(session_id, str) or not session_id.strip():
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "session_id is required")

    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{PICKER_SESSIONS}/{quote(session_id.strip(), safe='')}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers=headers)
    except httpx.RequestError as e:
        logger.error("Google Photos Picker get request error: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google Photos Picker request failed: {e}",
        ) from e
    if r.status_code != 200:
        _raise_google_photos_error(
            response=r,
            product="Google Photos Picker",
            auth_hint=(
                "Google Photos Picker denied this session request. Re-authenticate "
                f"with `{PHOTOS_PICKER_SCOPE}` and create a new picker session."
            ),
        )
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google Photos Picker API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google Photos Picker API",
        )
    return {"success": True, "session": data}


async def handle_google_photos_picker_list(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List media selected in a completed Google Photos Picker session."""
    await require_auth(user, "google_photos.picker.list")
    access_token = _access_token(params)
    session_id = params.get("session_id") or params.get("sessionId")
    if not isinstance(session_id, str) or not session_id.strip():
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "session_id is required")
    page_token = params.get("page_token") or params.get("pageToken")
    page_size = coerce_int_param(
        params.get("page_size", params.get("pageSize", 100)),
        100,
    )
    page_size = max(1, min(100, page_size))

    query: Dict[str, Any] = {"sessionId": session_id.strip(), "pageSize": page_size}
    if isinstance(page_token, str) and page_token.strip():
        query["pageToken"] = page_token.strip()

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(PICKER_MEDIA_ITEMS, headers=headers, params=query)
    except httpx.RequestError as e:
        logger.error("Google Photos Picker media request error: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"Google Photos Picker request failed: {e}",
        ) from e
    if r.status_code != 200:
        _raise_google_photos_error(
            response=r,
            product="Google Photos Picker",
            auth_hint=(
                "Google Photos Picker denied selected media access. Re-authenticate "
                f"with `{PHOTOS_PICKER_SCOPE}` and create a new picker session."
            ),
        )
    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google Photos Picker API",
        ) from e
    if not isinstance(data, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Unexpected non-object JSON from Google Photos Picker API",
        )
    return {
        "success": True,
        "mediaItems": data.get("mediaItems") or [],
        "nextPageToken": data.get("nextPageToken"),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "google_photos.list": handle_google_photos_list,
        "google_photos.picker.create": handle_google_photos_picker_create,
        "google_photos.picker.get": handle_google_photos_picker_get,
        "google_photos.picker.list": handle_google_photos_picker_list,
    }
