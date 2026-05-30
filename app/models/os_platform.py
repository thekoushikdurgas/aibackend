"""DurgasOS platform models — file metadata, audit log, OS settings.

Workflow and desktop layout models already live in durgasos_desktop.py.
This module adds file tracking, audit trail, and platform config.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.metrics import Base
from app.utils.helpers import utc_now


class FileMetadataModel(Base):
    """Tracks every file uploaded or known to DurgasOS.

    Raw bytes live in MinIO; this table holds the addressable metadata
    and links to the ChromaDB embedding_id when the file has been vectorized.
    """

    __tablename__ = "file_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), index=True, nullable=True
    )
    minio_bucket: Mapped[str] = mapped_column(String(255), default="user-uploads")
    minio_key: Mapped[str] = mapped_column(
        String(1024)
    )  # e.g. uploads/user-id/filename
    original_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )  # ChromaDB doc id
    embedded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AuditLogModel(Base):
    """Immutable audit trail for all significant OS operations.

    Analogous to the Linux kernel audit subsystem.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(128)
    )  # e.g. "file.upload", "workflow.run"
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class OsPlatformConfigModel(Base):
    """Per-user and global platform configuration key-value store."""

    __tablename__ = "os_platform_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), index=True, nullable=True
    )
    config_key: Mapped[str] = mapped_column(String(128))
    config_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
