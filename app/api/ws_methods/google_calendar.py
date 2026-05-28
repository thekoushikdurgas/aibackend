"""Google Calendar API proxy (server-side; uses user's OAuth access token)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.api.ws_methods.google_ws_util import (
    coerce_int_param,
    google_http_get_json,
    require_access_token,
)
from app.core.ws_auth import require_auth

CAL_EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


async def handle_google_calendar_list_events(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List events on the primary calendar.

    Params:
      - access_token (str, required)
      - max_results / maxResults (int, optional, default 50)
      - page_token / pageToken (str, optional)
      - time_min / timeMin (str, optional): RFC3339
      - time_max / timeMax (str, optional): RFC3339
      - single_events / singleEvents (bool, optional, default True)
    """
    await require_auth(user, "google_calendar.list_events")
    access_token = require_access_token(params)
    max_results = coerce_int_param(
        params.get("max_results", params.get("maxResults", 50)),
        50,
    )
    max_results = max(1, min(250, max_results))
    page_token = params.get("page_token") or params.get("pageToken")
    time_min = params.get("time_min") or params.get("timeMin")
    time_max = params.get("time_max") or params.get("timeMax")
    se = params.get("single_events", params.get("singleEvents", True))
    single_events = (
        bool(se) if not isinstance(se, str) else se.lower() in ("1", "true", "yes")
    )

    query: Dict[str, Any] = {"maxResults": max_results}
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token
    has_time_min = bool(time_min and isinstance(time_min, str) and time_min.strip())
    if has_time_min:
        # startTime ordering requires timeMin + singleEvents=true per Calendar API.
        query["orderBy"] = "startTime"
        query["singleEvents"] = "true"
        query["timeMin"] = (
            time_min if isinstance(time_min, str) else str(time_min)
        ).strip()
        if time_max and isinstance(time_max, str) and time_max.strip():
            query["timeMax"] = time_max.strip()
    else:
        query["orderBy"] = "updated"
        query["singleEvents"] = str(single_events).lower()
        if time_max and isinstance(time_max, str) and time_max.strip():
            query["timeMax"] = time_max.strip()

    data = await google_http_get_json(
        CAL_EVENTS, access_token=access_token, params=query
    )
    return {
        "success": True,
        "items": data.get("items") or [],
        "nextPageToken": data.get("nextPageToken"),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "google_calendar.list_events": handle_google_calendar_list_events,
    }
