"""DurgasOS desktop: workflows and widget layout persistence."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)

from app.models.metrics import Base
from app.utils.helpers import utc_now


class WorkflowDefinitionModel(Base):
    __tablename__ = "workflow_definitions"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    spec = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), nullable=False, index=True)
    owner_id = Column(String(255), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending")
    events = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class WidgetLayoutModel(Base):
    __tablename__ = "widget_layouts"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, unique=True, index=True)
    layout_json = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class LinkedGoogleAccountModel(Base):
    """Linked Google accounts (OAuth access token) per OS user (JWT sub)."""

    __tablename__ = "linked_google_accounts"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "google_user_id", name="uq_linked_google_owner_uid"
        ),
    )

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, index=True)
    google_user_id = Column(String(255), nullable=False, index=True)
    email = Column(String(512), nullable=True)
    display_name = Column(String(512), nullable=True)
    photo_url = Column(String(2048), nullable=True)
    access_token = Column(Text, nullable=False)
    token_expires_at = Column(Float, nullable=True)
    scopes_granted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class LinkedGithubAccountModel(Base):
    """Linked GitHub accounts (OAuth user-to-server token) per OS user (JWT sub)."""

    __tablename__ = "linked_github_accounts"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "github_user_id", name="uq_linked_github_owner_uid"
        ),
    )

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, index=True)
    github_user_id = Column(String(255), nullable=False, index=True)
    login = Column(String(255), nullable=True)
    email = Column(String(512), nullable=True)
    display_name = Column(String(512), nullable=True)
    photo_url = Column(String(2048), nullable=True)
    access_token = Column(Text, nullable=False)
    token_expires_at = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class DurgasOSInstalledAppsModel(Base):
    """Per-user list of installed DurgasOS app ids (see durgasos lib/apps)."""

    __tablename__ = "durgasos_installed_apps"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, unique=True, index=True)
    app_ids = Column(JSON, nullable=False, default=list)
    file_associations = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class TodoWorkspaceModel(Base):
    """Todo Kanban workspace: Google-backed (four Task lists) or local (DB tasks only)."""

    __tablename__ = "todo_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "storage",
            "google_user_id",
            "name",
            name="uq_todo_workspaces_owner_storage_google_name",
        ),
    )

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, index=True)
    storage = Column(
        String(16), nullable=False, default="google", server_default="google"
    )
    google_user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    backlog_list_id = Column(String(255), nullable=True)
    todo_list_id = Column(String(255), nullable=True)
    doing_list_id = Column(String(255), nullable=True)
    done_list_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class TodoTaskModel(Base):
    """Kanban card for a local (storage=local) Todo workspace."""

    __tablename__ = "todo_tasks"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(
        String(36),
        ForeignKey("todo_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id = Column(String(255), nullable=False, index=True)
    board_column = Column("board_column", String(32), nullable=False)
    title = Column(String(512), nullable=False)
    sort_order = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
