"""DurgasOS desktop: workflows and widget layout persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String

from app.models.metrics import Base


class WorkflowDefinitionModel(Base):
    __tablename__ = "workflow_definitions"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    spec = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), nullable=False, index=True)
    owner_id = Column(String(255), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending")
    events = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WidgetLayoutModel(Base):
    __tablename__ = "widget_layouts"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(255), nullable=False, unique=True, index=True)
    layout_json = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
