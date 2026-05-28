"""GraphQL: Todo workspaces (Google Tasks or local DB) and local Kanban tasks."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, cast

import strawberry
from graphql import GraphQLError
from sqlalchemy import and_, delete, func, select
from sqlalchemy.engine import CursorResult
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_tasks as google_tasks_handlers
from app.database import AsyncSessionLocal
from app.graphql.modules.util import graphql_params, require_authenticated_sub
from app.models.durgasos_desktop import (
    TodoCommentModel,
    TodoTaskModel,
    TodoWorkspaceModel,
)
from app.utils.helpers import utc_now

LOCAL_GOOGLE_USER_ID = "__local__"
TODO_STORAGE_GOOGLE = "google"
TODO_STORAGE_LOCAL = "local"
TODO_KANBAN_COLUMNS = frozenset({"backlog", "todo", "doing", "done"})


def _normalize_workspace_name(name: str) -> str:
    s = " ".join(name.strip().split())
    if not s:
        raise GraphQLError(
            "Workspace name is required",
            extensions={"code": "BAD_USER_INPUT"},
        )
    if len(s) > 64:
        raise GraphQLError(
            "Workspace name must be at most 64 characters",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def _normalize_task_title(title: str) -> str:
    s = title.strip()
    if not s:
        raise GraphQLError(
            "Task title is required",
            extensions={"code": "BAD_USER_INPUT"},
        )
    if len(s) > 512:
        raise GraphQLError(
            "Task title must be at most 512 characters",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def _str_or_empty(val: object | None) -> str:
    if val is None:
        return ""
    return str(val)


@strawberry.type
class TodoWorkspace:
    id: strawberry.ID
    name: str
    storage: str
    google_user_id: str
    backlog_list_id: str
    todo_list_id: str
    doing_list_id: str
    done_list_id: str
    created_at: str
    updated_at: str


def _row_to_workspace(r: TodoWorkspaceModel) -> TodoWorkspace:
    st = str(getattr(r, "storage", None) or TODO_STORAGE_GOOGLE)
    return TodoWorkspace(
        id=strawberry.ID(str(r.id)),
        name=str(r.name),
        storage=st,
        google_user_id=str(r.google_user_id),
        backlog_list_id=_str_or_empty(getattr(r, "backlog_list_id", None)),
        todo_list_id=_str_or_empty(getattr(r, "todo_list_id", None)),
        doing_list_id=_str_or_empty(getattr(r, "doing_list_id", None)),
        done_list_id=_str_or_empty(getattr(r, "done_list_id", None)),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class TodoTask:
    id: strawberry.ID
    title: str
    column: str
    sort_order: float
    workspace_id: strawberry.ID
    created_at: str
    updated_at: str


def _row_to_task(r: TodoTaskModel) -> TodoTask:
    return TodoTask(
        id=strawberry.ID(str(r.id)),
        title=str(r.title),
        column=str(r.board_column),
        sort_order=float(cast(Any, r.sort_order)),
        workspace_id=strawberry.ID(str(r.workspace_id)),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class TodoComment:
    id: strawberry.ID
    task_id: str
    owner_id: str
    content: str
    created_at: str
    updated_at: str


def _row_to_comment(r: TodoCommentModel) -> TodoComment:
    return TodoComment(
        id=strawberry.ID(str(r.id)),
        task_id=str(r.task_id),
        owner_id=str(r.owner_id),
        content=str(r.content),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class TodosQuery:
    @strawberry.field
    async def todo_workspaces(
        self, info: Info, google_user_id: str
    ) -> List[TodoWorkspace]:
        owner = require_authenticated_sub(info)
        gid = google_user_id.strip()
        if not gid:
            raise GraphQLError(
                "google_user_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            if gid == LOCAL_GOOGLE_USER_ID:
                stmt = (
                    select(TodoWorkspaceModel)
                    .where(
                        and_(
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_LOCAL,
                        )
                    )
                    .order_by(TodoWorkspaceModel.updated_at.desc())
                )
            else:
                stmt = (
                    select(TodoWorkspaceModel)
                    .where(
                        and_(
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_GOOGLE,
                            TodoWorkspaceModel.google_user_id == gid,
                        )
                    )
                    .order_by(TodoWorkspaceModel.updated_at.desc())
                )
            rows = (await db.execute(stmt)).scalars().all()
        return [_row_to_workspace(r) for r in rows]

    @strawberry.field
    async def todo_tasks(self, info: Info, workspace_id: str) -> List[TodoTask]:
        owner = require_authenticated_sub(info)
        wid = workspace_id.strip()
        if not wid:
            raise GraphQLError(
                "workspace_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            ws = (
                await db.execute(
                    select(TodoWorkspaceModel).where(
                        and_(
                            TodoWorkspaceModel.id == wid,
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_LOCAL,
                        )
                    )
                )
            ).scalar_one_or_none()
            if not ws:
                raise GraphQLError(
                    "Workspace not found",
                    extensions={"code": "NOT_FOUND"},
                )
            stmt = (
                select(TodoTaskModel)
                .where(TodoTaskModel.workspace_id == wid)
                .order_by(
                    TodoTaskModel.board_column.asc(), TodoTaskModel.sort_order.asc()
                )
            )
            rows = (await db.execute(stmt)).scalars().all()
        return [_row_to_task(r) for r in rows]

    @strawberry.field
    async def todo_comments(self, info: Info, task_id: str) -> List[TodoComment]:
        owner = require_authenticated_sub(info)
        tid = task_id.strip()
        if not tid:
            raise GraphQLError(
                "task_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = (
                select(TodoCommentModel)
                .where(
                    and_(
                        TodoCommentModel.task_id == tid,
                        TodoCommentModel.owner_id == owner,
                    )
                )
                .order_by(TodoCommentModel.created_at.asc())
            )
            rows = (await db.execute(stmt)).scalars().all()
        return [_row_to_comment(r) for r in rows]


@strawberry.type
class TodosMutation:
    @strawberry.mutation
    async def create_todo_workspace(
        self,
        info: Info,
        google_user_id: str,
        name: str,
        params: JSON | None = None,
    ) -> TodoWorkspace:
        owner = require_authenticated_sub(info)
        gid = google_user_id.strip()
        if not gid:
            raise GraphQLError(
                "google_user_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        nm = _normalize_workspace_name(name)

        if gid == LOCAL_GOOGLE_USER_ID:
            async with AsyncSessionLocal() as db:
                dup = (
                    await db.execute(
                        select(TodoWorkspaceModel.id).where(
                            and_(
                                TodoWorkspaceModel.owner_id == owner,
                                TodoWorkspaceModel.storage == TODO_STORAGE_LOCAL,
                                TodoWorkspaceModel.name == nm,
                            )
                        )
                    )
                ).scalar_one_or_none()
                if dup:
                    raise GraphQLError(
                        "A workspace with this name already exists",
                        extensions={"code": "BAD_USER_INPUT"},
                    )
            wid = str(uuid.uuid4())
            now = utc_now()
            row = TodoWorkspaceModel(
                id=wid,
                owner_id=owner,
                storage=TODO_STORAGE_LOCAL,
                google_user_id=LOCAL_GOOGLE_USER_ID,
                name=nm,
                backlog_list_id=None,
                todo_list_id=None,
                doing_list_id=None,
                done_list_id=None,
                created_at=now,
                updated_at=now,
            )
            async with AsyncSessionLocal() as db:
                db.add(row)
                await db.commit()
                await db.refresh(row)
            return _row_to_workspace(row)

        p = graphql_params(params)
        tok = p.get("access_token")
        if not isinstance(tok, str) or not tok.strip():
            raise GraphQLError(
                "params.access_token is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            dup = (
                await db.execute(
                    select(TodoWorkspaceModel.id).where(
                        and_(
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_GOOGLE,
                            TodoWorkspaceModel.google_user_id == gid,
                            TodoWorkspaceModel.name == nm,
                        )
                    )
                )
            ).scalar_one_or_none()
            if dup:
                raise GraphQLError(
                    "A workspace with this name already exists",
                    extensions={"code": "BAD_USER_INPUT"},
                )

        ensure_params = {"access_token": tok.strip(), "workspace_name": nm}
        user: Dict[str, Any] = {
            "sub": owner,
            "id": owner,
            "email": None,
            "user_metadata": {},
            "app_metadata": {},
        }
        result = await google_tasks_handlers.handle_google_tasks_ensure_kanban_lists(
            ensure_params, user=user, connection_id=None
        )
        if not isinstance(result, dict) or not result.get("success"):
            raise GraphQLError(
                "Could not create Google Task lists for this workspace",
                extensions={"code": "PROVIDER_ERROR"},
            )
        bid = result.get("backlogListId")
        tid = result.get("todoListId")
        did = result.get("doingListId")
        dnid = result.get("doneListId")
        if not all(isinstance(x, str) and x.strip() for x in (bid, tid, did, dnid)):
            raise GraphQLError(
                "Google Tasks returned incomplete list ids",
                extensions={"code": "PROVIDER_ERROR"},
            )
        wid = str(uuid.uuid4())
        now = utc_now()
        row = TodoWorkspaceModel(
            id=wid,
            owner_id=owner,
            storage=TODO_STORAGE_GOOGLE,
            google_user_id=gid,
            name=nm,
            backlog_list_id=str(bid).strip(),
            todo_list_id=str(tid).strip(),
            doing_list_id=str(did).strip(),
            done_list_id=str(dnid).strip(),
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionLocal() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
        return _row_to_workspace(row)

    @strawberry.mutation
    async def rename_todo_workspace(
        self, info: Info, workspace_id: str, name: str
    ) -> TodoWorkspace:
        owner = require_authenticated_sub(info)
        nm = _normalize_workspace_name(name)
        wid = workspace_id.strip()
        if not wid:
            raise GraphQLError(
                "workspace_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = select(TodoWorkspaceModel).where(
                and_(
                    TodoWorkspaceModel.id == wid,
                    TodoWorkspaceModel.owner_id == owner,
                )
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                raise GraphQLError(
                    "Workspace not found",
                    extensions={"code": "NOT_FOUND"},
                )
            st = str(getattr(row, "storage", None) or TODO_STORAGE_GOOGLE)
            dup = (
                await db.execute(
                    select(TodoWorkspaceModel.id).where(
                        and_(
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == st,
                            TodoWorkspaceModel.google_user_id == row.google_user_id,
                            TodoWorkspaceModel.name == nm,
                            TodoWorkspaceModel.id != wid,
                        )
                    )
                )
            ).scalar_one_or_none()
            if dup:
                raise GraphQLError(
                    "A workspace with this name already exists",
                    extensions={"code": "BAD_USER_INPUT"},
                )
            setattr(row, "name", nm)
            setattr(row, "updated_at", utc_now())
            await db.commit()
            await db.refresh(row)
            out = _row_to_workspace(row)
        return out

    @strawberry.mutation
    async def delete_todo_workspace(self, info: Info, workspace_id: str) -> bool:
        owner = require_authenticated_sub(info)
        wid = workspace_id.strip()
        if not wid:
            raise GraphQLError(
                "workspace_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = delete(TodoWorkspaceModel).where(
                and_(
                    TodoWorkspaceModel.id == wid,
                    TodoWorkspaceModel.owner_id == owner,
                )
            )
            result = await db.execute(stmt)
            await db.commit()
        assert isinstance(result, CursorResult)
        rc = result.rowcount
        return rc is not None and rc > 0

    @strawberry.mutation
    async def create_todo_task(
        self, info: Info, workspace_id: str, column: str, title: str
    ) -> TodoTask:
        owner = require_authenticated_sub(info)
        wid = workspace_id.strip()
        col = column.strip()
        if not wid:
            raise GraphQLError(
                "workspace_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if col not in TODO_KANBAN_COLUMNS:
            raise GraphQLError(
                "Invalid column",
                extensions={"code": "BAD_USER_INPUT"},
            )
        ttl = _normalize_task_title(title)
        async with AsyncSessionLocal() as db:
            ws = (
                await db.execute(
                    select(TodoWorkspaceModel).where(
                        and_(
                            TodoWorkspaceModel.id == wid,
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_LOCAL,
                        )
                    )
                )
            ).scalar_one_or_none()
            if not ws:
                raise GraphQLError(
                    "Workspace not found",
                    extensions={"code": "NOT_FOUND"},
                )
            mx = (
                await db.execute(
                    select(func.max(TodoTaskModel.sort_order)).where(
                        and_(
                            TodoTaskModel.workspace_id == wid,
                            TodoTaskModel.board_column == col,
                        )
                    )
                )
            ).scalar_one_or_none()
            base = float(mx) if mx is not None else 0.0
            tid = str(uuid.uuid4())
            now = utc_now()
            row = TodoTaskModel(
                id=tid,
                workspace_id=wid,
                owner_id=owner,
                board_column=col,
                title=ttl,
                sort_order=base + 1024.0,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
        return _row_to_task(row)

    @strawberry.mutation
    async def move_todo_task(
        self,
        info: Info,
        task_id: str,
        column: str,
        previous_task_id: Optional[str] = None,
    ) -> TodoTask:
        owner = require_authenticated_sub(info)
        tid = task_id.strip()
        col = column.strip()
        prev_raw = (previous_task_id or "").strip()
        prev_id = prev_raw or None
        if not tid:
            raise GraphQLError(
                "task_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if col not in TODO_KANBAN_COLUMNS:
            raise GraphQLError(
                "Invalid column",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = select(TodoTaskModel).where(
                and_(TodoTaskModel.id == tid, TodoTaskModel.owner_id == owner)
            )
            task = (await db.execute(stmt)).scalar_one_or_none()
            if not task:
                raise GraphQLError(
                    "Task not found",
                    extensions={"code": "NOT_FOUND"},
                )
            ws_id = str(task.workspace_id)
            ws = (
                await db.execute(
                    select(TodoWorkspaceModel).where(
                        and_(
                            TodoWorkspaceModel.id == ws_id,
                            TodoWorkspaceModel.owner_id == owner,
                            TodoWorkspaceModel.storage == TODO_STORAGE_LOCAL,
                        )
                    )
                )
            ).scalar_one_or_none()
            if not ws:
                raise GraphQLError(
                    "Workspace not found",
                    extensions={"code": "NOT_FOUND"},
                )

            others_stmt = (
                select(TodoTaskModel)
                .where(
                    and_(
                        TodoTaskModel.workspace_id == ws_id,
                        TodoTaskModel.board_column == col,
                        TodoTaskModel.id != tid,
                    )
                )
                .order_by(TodoTaskModel.sort_order.asc())
            )
            ordered_others = list((await db.execute(others_stmt)).scalars().all())

            insert_at = 0
            if prev_id:
                for i, o in enumerate(ordered_others):
                    if str(o.id) == prev_id:
                        insert_at = i + 1
                        break
            new_sequence = (
                ordered_others[:insert_at] + [task] + ordered_others[insert_at:]
            )
            now = utc_now()
            for i, t in enumerate(new_sequence):
                setattr(t, "board_column", col)
                setattr(t, "sort_order", float((i + 1) * 1024))
                setattr(t, "updated_at", now)
            await db.commit()
            await db.refresh(task)
        return _row_to_task(task)

    @strawberry.mutation
    async def delete_todo_task(self, info: Info, task_id: str) -> bool:
        owner = require_authenticated_sub(info)
        tid = task_id.strip()
        if not tid:
            raise GraphQLError(
                "task_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = delete(TodoTaskModel).where(
                and_(TodoTaskModel.id == tid, TodoTaskModel.owner_id == owner)
            )
            result = await db.execute(stmt)
            await db.commit()
        assert isinstance(result, CursorResult)
        rc = result.rowcount
        return rc is not None and rc > 0

    @strawberry.mutation
    async def create_todo_comment(
        self, info: Info, task_id: str, content: str
    ) -> TodoComment:
        owner = require_authenticated_sub(info)
        tid = task_id.strip()
        cnt = content.strip()
        if not tid:
            raise GraphQLError(
                "task_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if not cnt:
            raise GraphQLError(
                "Comment content cannot be empty",
                extensions={"code": "BAD_USER_INPUT"},
            )
        cid = str(uuid.uuid4())
        now = utc_now()
        row = TodoCommentModel(
            id=cid,
            task_id=tid,
            owner_id=owner,
            content=cnt,
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionLocal() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
        return _row_to_comment(row)

    @strawberry.mutation
    async def delete_todo_comment(self, info: Info, comment_id: str) -> bool:
        owner = require_authenticated_sub(info)
        cid = comment_id.strip()
        if not cid:
            raise GraphQLError(
                "comment_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = delete(TodoCommentModel).where(
                and_(TodoCommentModel.id == cid, TodoCommentModel.owner_id == owner)
            )
            result = await db.execute(stmt)
            await db.commit()
        assert isinstance(result, CursorResult)
        rc = result.rowcount
        return rc is not None and rc > 0
