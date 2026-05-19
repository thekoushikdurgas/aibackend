"""Google Tasks API proxy (server-side; uses user's OAuth access token)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

from app.api.ws_methods.google_ws_util import (
    coerce_int_param,
    google_http_delete,
    google_http_get_json,
    google_http_post_json,
    google_http_put_json,
    require_access_token,
)
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth

TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"
TASKLISTS_URL = f"{TASKS_BASE}/users/@me/lists"

_DEBUG_LOG_PATH = r"e:\durgas_ai\debug-2cdf97.log"


def _agent_debug_log(
    location: str,
    message: str,
    data: Dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "2cdf97",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except OSError:
        pass
    # endregion


def sanitize_workspace_name_for_titles(raw: object) -> str:
    """Normalize workspace name for Google Task list titles (middle segment)."""
    if not isinstance(raw, str):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "workspace_name is required",
        )
    s = " ".join(raw.strip().split())
    if not s:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "workspace_name must be non-empty",
        )
    if len(s) > 50:
        s = s[:50].rstrip()
    return s


def kanban_list_titles_for_workspace(
    workspace_name: str,
) -> Tuple[Tuple[str, str], ...]:
    """Four (resultKey, Google list title) pairs for one workspace Kanban."""
    w = sanitize_workspace_name_for_titles(workspace_name)
    # Legacy single-board lists (pre multi-workspace migration) used em-dash titles.
    if w == "Default":
        return (
            ("backlogListId", "DurgasOS — Backlog"),
            ("todoListId", "DurgasOS — TODO"),
            ("doingListId", "DurgasOS — In progress"),
            ("doneListId", "DurgasOS — Done"),
        )
    prefix = f"DurgasOS · {w} · "
    return (
        ("backlogListId", prefix + "Backlog"),
        ("todoListId", prefix + "TODO"),
        ("doingListId", prefix + "In progress"),
        ("doneListId", prefix + "Done"),
    )


def _tasklist_id_param(params: Dict[str, Any]) -> str:
    tid = params.get("tasklist_id") or params.get("tasklistId")
    if not tid or not isinstance(tid, str) or not tid.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "tasklist_id is required",
        )
    return tid.strip()


def _task_id_param(params: Dict[str, Any]) -> str:
    tid = params.get("task_id") or params.get("taskId") or params.get("id")
    if not tid or not isinstance(tid, str) or not tid.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "task_id is required",
        )
    return tid.strip()


def _move_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    parent = params.get("parent")
    if isinstance(parent, str) and parent.strip():
        out["parent"] = parent.strip()
    previous = params.get("previous")
    if isinstance(previous, str) and previous.strip():
        out["previous"] = previous.strip()
    dest = params.get("destination_tasklist") or params.get("destinationTasklist")
    if isinstance(dest, str) and dest.strip():
        out["destinationTasklist"] = dest.strip()
    return out


async def handle_google_tasks_list_tasklists(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """GET users/@me/lists."""
    await require_auth(user, "google_tasks.list_tasklists")
    access_token = require_access_token(params)
    max_results = coerce_int_param(
        params.get("max_results", params.get("maxResults", 100)),
        100,
    )
    max_results = max(1, min(100, max_results))
    page_token = params.get("page_token") or params.get("pageToken")
    q: Dict[str, Any] = {"maxResults": max_results}
    if page_token and isinstance(page_token, str) and page_token.strip():
        q["pageToken"] = page_token.strip()
    data = await google_http_get_json(
        TASKLISTS_URL, access_token=access_token, params=q
    )
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    return {
        "success": True,
        "items": items,
        "nextPageToken": data.get("nextPageToken"),
    }


async def _ensure_single_list(
    access_token: str,
    title: str,
    by_title: Dict[str, str],
) -> str:
    existing = by_title.get(title)
    if existing:
        return existing
    created = await google_http_post_json(
        TASKLISTS_URL,
        access_token=access_token,
        json_body={"title": title},
    )
    lid = created.get("id")
    if not isinstance(lid, str) or not lid.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.PROVIDER_ERROR,
            "Google Tasks did not return a task list id",
        )
    by_title[title] = lid.strip()
    return lid.strip()


async def handle_google_tasks_ensure_kanban_lists(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """Ensure the four Kanban task lists exist for a workspace; create any missing ones.

    Params:
      - access_token (str, required)
      - workspace_name / workspaceName (str, required)
    """
    await require_auth(user, "google_tasks.ensure_kanban_lists")
    access_token = require_access_token(params)
    wn_raw = params.get("workspace_name") or params.get("workspaceName")
    wn = sanitize_workspace_name_for_titles(wn_raw)
    titles = kanban_list_titles_for_workspace(wn)

    by_title: Dict[str, str] = {}
    page_token: Optional[str] = None
    while True:
        q: Dict[str, Any] = {"maxResults": 100}
        if page_token:
            q["pageToken"] = page_token
        data = await google_http_get_json(
            TASKLISTS_URL, access_token=access_token, params=q
        )
        items = data.get("items")
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                t = it.get("title")
                i = it.get("id")
                if isinstance(t, str) and isinstance(i, str) and t and i:
                    by_title[t] = i
        page_token = data.get("nextPageToken")
        if not page_token or not isinstance(page_token, str):
            break

    result: Dict[str, Any] = {"success": True}
    for key, title in titles:
        result[key] = await _ensure_single_list(access_token, title, by_title)
    return result


async def handle_google_tasks_list_tasks(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """GET lists/{tasklist}/tasks.

    Params:
      - access_token (str, required)
      - tasklist_id / tasklistId (str, required)
      - max_results / maxResults (int, optional, default 100)
      - page_token / pageToken (str, optional)
      - show_completed / showCompleted (bool, optional, default True)
      - show_deleted / showDeleted (bool, optional, default False)
      - show_hidden / showHidden (bool, optional, default False)
    """
    await require_auth(user, "google_tasks.list_tasks")
    access_token = require_access_token(params)
    tasklist_id = _tasklist_id_param(params)
    max_results = coerce_int_param(
        params.get("max_results", params.get("maxResults", 100)),
        100,
    )
    max_results = max(1, min(100, max_results))
    page_token = params.get("page_token") or params.get("pageToken")
    sc = params.get("show_completed", params.get("showCompleted", True))
    show_completed = (
        sc if isinstance(sc, bool) else str(sc).lower() in ("1", "true", "yes")
    )
    sd = params.get("show_deleted", params.get("showDeleted", False))
    show_deleted = (
        sd if isinstance(sd, bool) else str(sd).lower() in ("1", "true", "yes")
    )
    sh = params.get("show_hidden", params.get("showHidden", False))
    show_hidden = (
        sh if isinstance(sh, bool) else str(sh).lower() in ("1", "true", "yes")
    )

    query: Dict[str, Any] = {
        "maxResults": max_results,
        "showCompleted": str(show_completed).lower(),
        "showDeleted": str(show_deleted).lower(),
        "showHidden": str(show_hidden).lower(),
    }
    if page_token and isinstance(page_token, str) and page_token.strip():
        query["pageToken"] = page_token.strip()

    url = f"{TASKS_BASE}/lists/{tasklist_id}/tasks"
    data = await google_http_get_json(url, access_token=access_token, params=query)
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    return {
        "success": True,
        "items": items,
        "nextPageToken": data.get("nextPageToken"),
    }


async def handle_google_tasks_insert_task(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """POST lists/{tasklist}/tasks.

    Params:
      - access_token (str, required)
      - tasklist_id / tasklistId (str, required)
      - title (str, required)
      - notes (str, optional)
      - status (str, optional): needsAction | completed
    """
    await require_auth(user, "google_tasks.insert_task")
    access_token = require_access_token(params)
    tasklist_id = _tasklist_id_param(params)
    title = params.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "title is required",
        )
    body: Dict[str, Any] = {"title": title.strip()}
    notes = params.get("notes")
    if isinstance(notes, str) and notes.strip():
        body["notes"] = notes.strip()
    st = params.get("status")
    if isinstance(st, str) and st.strip() in ("needsAction", "completed"):
        body["status"] = st.strip()

    url = f"{TASKS_BASE}/lists/{tasklist_id}/tasks"
    task = await google_http_post_json(url, access_token=access_token, json_body=body)
    return {"success": True, "task": task}


async def handle_google_tasks_update_task(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """PUT lists/{tasklist}/tasks/{task}.

    Params:
      - access_token (str, required)
      - tasklist_id / tasklistId (str, required)
      - task_id / taskId (str, required)
      - task (object, required): full or partial Task resource (merged server-side
        by replacing with provided keys over a minimal fetch is heavy; client
        should send full task object from list_tasks + edits). For simplicity we
        require ``task`` to be a dict with at least id and title as needed by API.
    """
    await require_auth(user, "google_tasks.update_task")
    access_token = require_access_token(params)
    tasklist_id = _tasklist_id_param(params)
    task_id = _task_id_param(params)
    task = params.get("task")
    if not isinstance(task, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "task object is required",
        )
    body = dict(task)
    body["id"] = task_id

    url = f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    updated = await google_http_put_json(url, access_token=access_token, json_body=body)
    return {"success": True, "task": updated}


async def handle_google_tasks_delete_task(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """DELETE lists/{tasklist}/tasks/{task}."""
    await require_auth(user, "google_tasks.delete_task")
    access_token = require_access_token(params)
    tasklist_id = _tasklist_id_param(params)
    task_id = _task_id_param(params)
    url = f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    await google_http_delete(url, access_token=access_token)
    return {"success": True}


async def handle_google_tasks_move_task(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """POST lists/{tasklist}/tasks/{task}/move.

    Params:
      - access_token (str, required)
      - tasklist_id / tasklistId (str, required): source list
      - task_id / taskId (str, required)
      - parent (str, optional)
      - previous (str, optional): task id of previous sibling
      - destination_tasklist / destinationTasklist (str, optional)
    """
    await require_auth(user, "google_tasks.move_task")
    access_token = require_access_token(params)
    tasklist_id = _tasklist_id_param(params)
    task_id = _task_id_param(params)
    move_params = _move_query_params(params)
    url = f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}/move"
    _agent_debug_log(
        "google_tasks.py:handle_google_tasks_move_task",
        "move_request",
        {
            "tasklist_id": tasklist_id,
            "task_id": task_id,
            "move_params": move_params,
        },
        "A",
    )
    try:
        task = await google_http_post_json(
            url, access_token=access_token, json_body={}, params=move_params or None
        )
    except JSONRPCError as exc:
        msg = str(exc)
        if move_params.get("previous") and "Previous task id" in msg:
            reduced = {k: v for k, v in move_params.items() if k != "previous"}
            _agent_debug_log(
                "google_tasks.py:handle_google_tasks_move_task",
                "move_retry_without_previous",
                {"reduced": reduced, "error": msg[:200]},
                "B",
            )
            task = await google_http_post_json(
                url,
                access_token=access_token,
                json_body={},
                params=reduced or None,
            )
        else:
            _agent_debug_log(
                "google_tasks.py:handle_google_tasks_move_task",
                "move_failed",
                {"error": msg[:240], "move_params": move_params},
                "C",
            )
            raise
    _agent_debug_log(
        "google_tasks.py:handle_google_tasks_move_task",
        "move_ok",
        {"task_id": task.get("id") if isinstance(task, dict) else None},
        "A",
    )
    return {"success": True, "task": task}


def get_methods() -> Dict[str, Any]:
    return {
        "google_tasks.list_tasklists": handle_google_tasks_list_tasklists,
        "google_tasks.ensure_kanban_lists": handle_google_tasks_ensure_kanban_lists,
        "google_tasks.list_tasks": handle_google_tasks_list_tasks,
        "google_tasks.insert_task": handle_google_tasks_insert_task,
        "google_tasks.update_task": handle_google_tasks_update_task,
        "google_tasks.delete_task": handle_google_tasks_delete_task,
        "google_tasks.move_task": handle_google_tasks_move_task,
    }
