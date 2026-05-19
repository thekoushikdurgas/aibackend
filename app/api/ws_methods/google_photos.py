"""Google Photos Library API proxy (server-side; uses user's OAuth access token)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.api.ws_methods.google_ws_util import coerce_int_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth

logger = logging.getLogger(__name__)

PHOTOS_MEDIA_ITEMS = "https://photoslibrary.googleapis.com/v1/mediaItems"


async def handle_google_photos_list(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List media items via Google Photos Library API (paginated).

    Params:
      - access_token (str, required): Google OAuth access token with Photos scope.
      - page_token (str, optional): nextPageToken from a previous response.
      - page_size (int, optional): 1–100, default 100.
    """
    await require_auth(user, "google_photos.list")

    access_token = params.get("access_token")
    if not access_token or not isinstance(access_token, str):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "access_token is required",
        )

    page_token = params.get("page_token") or params.get("pageToken")
    page_size = coerce_int_param(
        params.get("page_size", params.get("pageSize", 100)),
        100,
    )
    page_size = max(1, min(100, page_size))

    query: Dict[str, Any] = {"pageSize": page_size}
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token

    headers = {"Authorization": f"Bearer {access_token.strip()}"}

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
        logger.warning(
            "Google Photos API error status=%s body=%s", r.status_code, detail
        )
        err_msg = ""
        try:
            payload = r.json()
            if isinstance(payload, dict):
                err = payload.get("error")
                if isinstance(err, dict) and isinstance(err.get("message"), str):
                    err_msg = err["message"]
        except Exception:
            err_msg = ""
        combined = f"{err_msg} {detail}".lower()
        if "insufficient authentication scopes" in combined:
            scope_list: list[str] = []
            token_aud = ""
            try:
                async with httpx.AsyncClient(timeout=10.0) as tc:
                    ti = await tc.get(
                        "https://oauth2.googleapis.com/tokeninfo",
                        params={"access_token": access_token.strip()},
                    )
                    if ti.status_code == 200:
                        body = ti.json()
                        raw_sc = body.get("scope", "")
                        if isinstance(raw_sc, str):
                            scope_list = [s for s in raw_sc.split() if s]
                        aud_v = body.get("aud")
                        if isinstance(aud_v, str):
                            token_aud = aud_v
            except Exception:
                scope_list = []
                token_aud = ""
            has_photoslibrary = any("photoslibrary.readonly" in s for s in scope_list)
            if has_photoslibrary:
                logger.warning(
                    "Google Photos 403 'insufficient scopes' but tokeninfo lists "
                    "photoslibrary.readonly (aud=%s); enable Photos Library API for that client project.",
                    token_aud or "?",
                )
                raise JSONRPCError(
                    JSONRPCErrorCode.PROVIDER_ERROR,
                    "Google Photos refused access even though this token includes "
                    "`photoslibrary.readonly` (verified with Google tokeninfo). "
                    "In Google Cloud Console, open the project for OAuth **client id** "
                    f"`{token_aud or 'your Web client'}` and enable **Photos Library API** "
                    "(APIs & Services → Library → search “Photos Library API” → Enable), wait a minute, then retry.",
                )
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHORIZATION_ERROR,
                "Google Photos denied this request: the access token is missing the "
                "Photos Library OAuth scope. Remove the Google account under Settings → Accounts "
                "and add it again (Gallery can re-authenticate), and ensure "
                "`https://www.googleapis.com/auth/photoslibrary.readonly` is listed on your "
                "Google Cloud OAuth consent screen for this client.",
            )
        raise JSONRPCError(
            JSONRPCErrorCode.PROVIDER_ERROR,
            f"Google Photos API error ({r.status_code}): {(err_msg or detail)[:200]}",
        )

    try:
        data = r.json()
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            "Invalid JSON from Google Photos API",
        ) from e

    return {
        "success": True,
        "mediaItems": data.get("mediaItems") or [],
        "nextPageToken": data.get("nextPageToken"),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "google_photos.list": handle_google_photos_list,
    }
