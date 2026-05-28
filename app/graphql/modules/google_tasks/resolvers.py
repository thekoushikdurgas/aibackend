"""Google Tasks API via WebSocket handlers (GraphQL JSON)."""

from __future__ import annotations

from typing import cast

import strawberry
from graphql import GraphQLError
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_tasks as google_tasks_handlers
from app.database import AsyncSessionLocal
from app.graphql.modules.util import (
    graphql_params,
    require_authenticated_sub,
    run_ws,
)
from app.models.durgasos_desktop import TodoWorkspaceModel
from app.utils.helpers import utc_now


async def _update_todo_workspace_list_ids(
    workspace_id: str,
    owner_id: str,
    backlog_list_id: str,
    todo_list_id: str,
    doing_list_id: str,
    done_list_id: str,
) -> None:
    now = utc_now()
    async with AsyncSessionLocal() as db:
        stmt = select(TodoWorkspaceModel).where(
            TodoWorkspaceModel.id == workspace_id,
            TodoWorkspaceModel.owner_id == owner_id,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            return
        setattr(row, "backlog_list_id", backlog_list_id)
        setattr(row, "todo_list_id", todo_list_id)
        setattr(row, "doing_list_id", doing_list_id)
        setattr(row, "done_list_id", done_list_id)
        setattr(row, "updated_at", now)
        await db.commit()


@strawberry.type
class GoogleTasksQuery:
    @strawberry.field
    async def google_tasks_list_tasklists(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """GET users/@me/lists. Params: access_token, max_results?, page_token?."""
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_list_tasklists, p, info
        )

    @strawberry.field
    async def google_tasks_ensure_kanban_lists(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """Ensure four Kanban lists for a workspace; persists list ids on that row.

        Params: access_token, workspace_id (str).
        """
        owner = require_authenticated_sub(info)
        p = graphql_params(params)
        ws_id = p.get("workspace_id") or p.get("workspaceId")
        if not isinstance(ws_id, str) or not ws_id.strip():
            raise GraphQLError(
                "workspace_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        ws_id = ws_id.strip()
        async with AsyncSessionLocal() as db:
            stmt = select(TodoWorkspaceModel).where(
                TodoWorkspaceModel.id == ws_id,
                TodoWorkspaceModel.owner_id == owner,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise GraphQLError(
                "Workspace not found",
                extensions={"code": "NOT_FOUND"},
            )
        st = str(getattr(row, "storage", None) or "google")
        if st != "google":
            raise GraphQLError(
                "This workspace is not linked to Google Tasks",
                extensions={"code": "BAD_USER_INPUT"},
            )
        merged = {
            **p,
            "workspace_name": row.name,
        }
        result = await run_ws(
            google_tasks_handlers.handle_google_tasks_ensure_kanban_lists,
            merged,
            info,
        )
        if not isinstance(result, dict):
            return cast(JSON, {})
        bid = result.get("backlogListId")
        tid = result.get("todoListId")
        did = result.get("doingListId")
        dnid = result.get("doneListId")
        if not all(isinstance(x, str) and x.strip() for x in (bid, tid, did, dnid)):
            return cast(JSON, result)
        await _update_todo_workspace_list_ids(
            ws_id,
            owner,
            str(bid).strip(),
            str(tid).strip(),
            str(did).strip(),
            str(dnid).strip(),
        )
        return cast(JSON, result)

    @strawberry.field
    async def google_tasks_list_tasks(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """GET lists/{tasklist}/tasks. Params: access_token, tasklist_id, ..."""
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_list_tasks, p, info
        )


@strawberry.type
class GoogleTasksMutation:
    @strawberry.mutation
    async def google_tasks_insert_task(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_insert_task, p, info
        )

    @strawberry.mutation
    async def google_tasks_update_task(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_update_task, p, info
        )

    @strawberry.mutation
    async def google_tasks_delete_task(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_delete_task, p, info
        )

    @strawberry.mutation
    async def google_tasks_move_task(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        p = graphql_params(params)
        return await run_ws(
            google_tasks_handlers.handle_google_tasks_move_task, p, info
        )
