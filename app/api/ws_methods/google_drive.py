"""Google Drive API v3 proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.api.ws_methods.google_ws_util import (
    coerce_int_param,
    google_http_get_json,
    require_access_token,
)
from app.core.ws_auth import require_auth

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"


async def handle_google_drive_list_files(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List files in Drive (files.list).

    Params:
      - access_token (str, required)
      - page_size / pageSize (int, optional, default 50)
      - page_token / pageToken (str, optional)
      - q (str, optional): Drive search query
      - fields (str, optional): partial response field mask
    """
    await require_auth(user, "google_drive.list_files")
    access_token = require_access_token(params)
    page_size = coerce_int_param(
        params.get("page_size", params.get("pageSize", 50)),
        50,
    )
    page_size = max(1, min(100, page_size))
    page_token = params.get("page_token") or params.get("pageToken")
    q = params.get("q")
    fields = params.get("fields")
    if not isinstance(fields, str) or not fields.strip():
        fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents)"
    query: Dict[str, Any] = {
        "pageSize": page_size,
        "fields": fields.strip(),
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token
    if q and isinstance(q, str) and q.strip():
        query["q"] = q.strip()

    data = await google_http_get_json(
        DRIVE_FILES, access_token=access_token, params=query
    )
    return {
        "success": True,
        "files": data.get("files") or [],
        "nextPageToken": data.get("nextPageToken"),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "google_drive.list_files": handle_google_drive_list_files,
    }
