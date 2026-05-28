"""Google People API (contacts) proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.api.ws_methods.google_ws_util import (
    coerce_int_param,
    google_http_get_json,
    require_access_token,
)
from app.core.ws_auth import require_auth

PEOPLE_CONNECTIONS = "https://people.googleapis.com/v1/people/me/connections"


async def handle_google_people_list_contacts(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List connections (contacts) for the authenticated user.

    Params:
      - access_token (str, required)
      - page_size / pageSize (int, optional, default 100)
      - page_token / pageToken (str, optional)
      - person_fields / personFields (str, optional): People API field mask
    """
    await require_auth(user, "google_people.list_contacts")
    access_token = require_access_token(params)
    page_size = coerce_int_param(
        params.get("page_size", params.get("pageSize", 100)),
        100,
    )
    page_size = max(1, min(1000, page_size))
    page_token = params.get("page_token") or params.get("pageToken")
    person_fields = (
        params.get("person_fields")
        or params.get("personFields")
        or "names,emailAddresses,photos,metadata"
    )
    if not isinstance(person_fields, str):
        person_fields = "names,emailAddresses,photos,metadata"
    query: Dict[str, Any] = {
        "pageSize": page_size,
        "personFields": person_fields.strip() or "names,emailAddresses,photos,metadata",
    }
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token

    data = await google_http_get_json(
        PEOPLE_CONNECTIONS, access_token=access_token, params=query
    )
    return {
        "success": True,
        "connections": data.get("connections") or [],
        "nextPageToken": data.get("nextPageToken"),
        "totalPeople": data.get("totalPeople"),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "google_people.list_contacts": handle_google_people_list_contacts,
    }
