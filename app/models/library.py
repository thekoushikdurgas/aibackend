"""AuraBook / Library app persistence (per-owner catalog, notes, devices, notifications)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.metrics import Base
from app.utils.helpers import utc_now


class LibraryBookModel(Base):
    __tablename__ = "library_books"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(
        String(200), nullable=False, default="Unknown Author"
    )
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    borrowing_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="available"
    )
    borrower: Mapped[str | None] = mapped_column(String(200), nullable=True)
    borrow_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    return_due_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pdf_attached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    pdf_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages_total: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    pages_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    published_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class LibraryNoteModel(Base):
    __tablename__ = "library_notes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_book_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    last_saved: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class LibraryDeviceModel(Base):
    __tablename__ = "library_devices"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    last_sync: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class LibraryNotificationModel(Base):
    __tablename__ = "library_notifications"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
