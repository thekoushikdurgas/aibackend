"""Gmail API proxy (server-side; uses user's OAuth access token)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.api.ws_methods.google_ws_util import (
    coerce_int_param,
    google_http_get_json,
    require_access_token,
)
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth

GMAIL_MESSAGES = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_THREADS = "https://gmail.googleapis.com/gmail/v1/users/me/threads"


async def handle_gmail_list_messages(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List message ids (Gmail users.messages.list).

    Params:
      - access_token (str, required)
      - max_results / maxResults (int, optional, default 25)
      - page_token / pageToken (str, optional)
      - q (str, optional): Gmail search query
    """
    await require_auth(user, "gmail.list_messages")
    access_token = require_access_token(params)
    max_results = coerce_int_param(
        params.get("max_results", params.get("maxResults", 25)),
        25,
    )
    max_results = max(1, min(100, max_results))
    page_token = params.get("page_token") or params.get("pageToken")
    q = params.get("q")
    query: Dict[str, Any] = {"maxResults": max_results}
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token
    if q and isinstance(q, str) and q.strip():
        query["q"] = q.strip()
    data = await google_http_get_json(
        GMAIL_MESSAGES, access_token=access_token, params=query
    )
    return {
        "success": True,
        "messages": data.get("messages") or [],
        "nextPageToken": data.get("nextPageToken"),
        "resultSizeEstimate": data.get("resultSizeEstimate"),
    }


async def handle_gmail_get_message(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Fetch a single message (Gmail users.messages.get).

    Params:
      - access_token (str, required)
      - message_id / messageId / id (str, required)
      - format (str, optional): metadata | minimal | full | raw (default metadata)
    """
    await require_auth(user, "gmail.get_message")
    access_token = require_access_token(params)
    mid = params.get("message_id") or params.get("messageId") or params.get("id")
    if not mid or not isinstance(mid, str) or not mid.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "message_id is required",
        )
    fmt = params.get("format", "metadata")
    if not isinstance(fmt, str) or fmt not in (
        "minimal",
        "full",
        "raw",
        "metadata",
    ):
        fmt = "metadata"
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid.strip()}"
    data = await google_http_get_json(
        url,
        access_token=access_token,
        params={"format": fmt},
    )
    return {"success": True, "message": data}


async def handle_gmail_list_threads(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """List threads with snippets (Gmail users.threads.list).

    Params:
      - access_token (str, required)
      - max_results / maxResults (int, optional, default 25)
      - page_token / pageToken (str, optional)
      - q (str, optional): Gmail search query (e.g. ``in:inbox``)
    """
    await require_auth(user, "gmail.list_threads")
    access_token = require_access_token(params)
    max_results = coerce_int_param(
        params.get("max_results", params.get("maxResults", 25)),
        25,
    )
    max_results = max(1, min(100, max_results))
    page_token = params.get("page_token") or params.get("pageToken")
    q = params.get("q")
    query: Dict[str, Any] = {"maxResults": max_results}
    if page_token and isinstance(page_token, str):
        query["pageToken"] = page_token
    if q and isinstance(q, str) and q.strip():
        query["q"] = q.strip()
    data = await google_http_get_json(
        GMAIL_THREADS, access_token=access_token, params=query
    )
    return {
        "success": True,
        "threads": data.get("threads") or [],
        "nextPageToken": data.get("nextPageToken"),
        "resultSizeEstimate": data.get("resultSizeEstimate"),
    }


async def handle_gmail_get_thread(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Fetch a thread with message metadata (Gmail users.threads.get).

    Params:
      - access_token (str, required)
      - thread_id / threadId / id (str, required)
      - format (str, optional): metadata | minimal | full (default metadata)
    """
    await require_auth(user, "gmail.get_thread")
    access_token = require_access_token(params)
    tid = params.get("thread_id") or params.get("threadId") or params.get("id")
    if not tid or not isinstance(tid, str) or not tid.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "thread_id is required",
        )
    fmt = params.get("format", "metadata")
    if not isinstance(fmt, str) or fmt not in ("minimal", "full", "metadata"):
        fmt = "metadata"
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{tid.strip()}"
    data = await google_http_get_json(
        url,
        access_token=access_token,
        params={"format": fmt},
    )
    return {"success": True, "thread": data}


def get_methods() -> Dict[str, Any]:
    return {
        "gmail.list_messages": handle_gmail_list_messages,
        "gmail.get_message": handle_gmail_get_message,
        "gmail.list_threads": handle_gmail_list_threads,
        "gmail.get_thread": handle_gmail_get_thread,
    }
