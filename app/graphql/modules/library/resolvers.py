"""GraphQL: Library / AuraBook (books, notes, devices, notifications)."""

from __future__ import annotations

from typing import List, Optional, cast

import strawberry
from graphql import GraphQLError
from sqlalchemy import and_, delete, select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
from app.graphql.modules.util import require_authenticated_sub
from app.models.library import (
    LibraryBookModel,
    LibraryDeviceModel,
    LibraryNoteModel,
    LibraryNotificationModel,
)
from app.services.library_service import (
    MAX_AUTHOR,
    MAX_BORROWER,
    MAX_CATEGORY,
    MAX_COVER_URL,
    MAX_DESCRIPTION,
    MAX_ISBN,
    MAX_NOTE_CONTENT,
    MAX_NOTE_TITLE,
    MAX_PDF_NAME,
    MAX_TITLE,
    _clamp_str,
    _iso_now,
    new_notification_id,
    seed_library_for_owner,
    validate_borrowing_status,
    validate_device_type,
    validate_library_id,
    validate_rating,
)
from app.utils.helpers import utc_now


@strawberry.type
class LibraryBook:
    id: strawberry.ID
    title: str
    author: str
    isbn: str
    category: str
    description: str
    cover_url: str
    borrowing_status: str
    borrower: Optional[str]
    borrow_date: Optional[str]
    return_due_date: Optional[str]
    pdf_attached: bool
    pdf_storage_path: Optional[str]
    pdf_name: Optional[str]
    pdf_content: Optional[str]
    pages_total: int
    pages_read: int
    rating: Optional[float]
    published_date: Optional[str]
    author_info: Optional[str]
    created_at: str
    updated_at: str


def _row_to_book(r: LibraryBookModel) -> LibraryBook:
    return LibraryBook(
        id=strawberry.ID(str(r.id)),
        title=str(r.title),
        author=str(r.author),
        isbn=str(r.isbn or ""),
        category=str(r.category or ""),
        description=str(r.description or ""),
        cover_url=str(r.cover_url or ""),
        borrowing_status=str(r.borrowing_status),
        borrower=r.borrower,
        borrow_date=r.borrow_date,
        return_due_date=r.return_due_date,
        pdf_attached=bool(r.pdf_attached),
        pdf_storage_path=r.pdf_storage_path,
        pdf_name=r.pdf_name,
        pdf_content=r.pdf_content,
        pages_total=int(r.pages_total or 0),
        pages_read=int(r.pages_read or 0),
        rating=float(r.rating) if r.rating is not None else None,
        published_date=r.published_date,
        author_info=r.author_info,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class LibraryNote:
    id: strawberry.ID
    title: str
    content: str
    linked_book_ids: List[str]
    last_saved: str
    created_at: str
    updated_at: str


def _row_to_note(r: LibraryNoteModel) -> LibraryNote:
    linked = r.linked_book_ids if isinstance(r.linked_book_ids, list) else []
    return LibraryNote(
        id=strawberry.ID(str(r.id)),
        title=str(r.title),
        content=str(r.content or ""),
        linked_book_ids=[str(x) for x in linked],
        last_saved=str(r.last_saved or ""),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class LibraryDevice:
    id: strawberry.ID
    name: str
    type: str
    last_sync: str
    active: bool
    created_at: str
    updated_at: str


def _row_to_device(r: LibraryDeviceModel) -> LibraryDevice:
    return LibraryDevice(
        id=strawberry.ID(str(r.id)),
        name=str(r.name),
        type=str(r.type),
        last_sync=str(r.last_sync or ""),
        active=bool(r.active),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class LibraryNotification:
    id: strawberry.ID
    message: str
    type: str
    timestamp: str


def _row_to_notification(r: LibraryNotificationModel) -> LibraryNotification:
    return LibraryNotification(
        id=strawberry.ID(str(r.id)),
        message=str(r.message),
        type=str(r.type),
        timestamp=str(r.timestamp),
    )


@strawberry.input
class LibraryBookUpsertInput:
    id: str
    title: str
    author: str
    isbn: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    borrowing_status: Optional[str] = None
    borrower: Optional[str] = None
    borrow_date: Optional[str] = None
    return_due_date: Optional[str] = None
    pdf_attached: Optional[bool] = None
    pdf_storage_path: Optional[str] = None
    pdf_name: Optional[str] = None
    pdf_content: Optional[str] = None
    pages_total: Optional[int] = None
    pages_read: Optional[int] = None
    rating: Optional[float] = None
    published_date: Optional[str] = None
    author_info: Optional[str] = None


@strawberry.input
class LibraryNoteUpsertInput:
    id: str
    title: str
    content: Optional[str] = None
    linked_book_ids: Optional[List[str]] = None


@strawberry.input
class LibraryDeviceUpsertInput:
    id: str
    name: str
    type: str
    last_sync: Optional[str] = None
    active: Optional[bool] = None


@strawberry.type
class LibraryQuery:
    @strawberry.field
    async def library_books(self, info: Info) -> List[LibraryBook]:
        owner = require_authenticated_sub(info)
        async with AsyncSessionLocal() as db:
            await seed_library_for_owner(db, owner)
            await db.commit()
            rows = (
                (
                    await db.execute(
                        select(LibraryBookModel)
                        .where(LibraryBookModel.owner_id == owner)
                        .order_by(LibraryBookModel.updated_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        return [_row_to_book(r) for r in rows]

    @strawberry.field
    async def library_notes(self, info: Info) -> List[LibraryNote]:
        owner = require_authenticated_sub(info)
        async with AsyncSessionLocal() as db:
            await seed_library_for_owner(db, owner)
            await db.commit()
            rows = (
                (
                    await db.execute(
                        select(LibraryNoteModel)
                        .where(LibraryNoteModel.owner_id == owner)
                        .order_by(LibraryNoteModel.updated_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        return [_row_to_note(r) for r in rows]

    @strawberry.field
    async def library_devices(self, info: Info) -> List[LibraryDevice]:
        owner = require_authenticated_sub(info)
        async with AsyncSessionLocal() as db:
            await seed_library_for_owner(db, owner)
            await db.commit()
            rows = (
                (
                    await db.execute(
                        select(LibraryDeviceModel).where(
                            LibraryDeviceModel.owner_id == owner
                        )
                    )
                )
                .scalars()
                .all()
            )
        return [_row_to_device(r) for r in rows]

    @strawberry.field
    async def library_notifications(self, info: Info) -> List[LibraryNotification]:
        owner = require_authenticated_sub(info)
        async with AsyncSessionLocal() as db:
            await seed_library_for_owner(db, owner)
            await db.commit()
            rows = (
                (
                    await db.execute(
                        select(LibraryNotificationModel)
                        .where(LibraryNotificationModel.owner_id == owner)
                        .order_by(LibraryNotificationModel.timestamp.desc())
                    )
                )
                .scalars()
                .all()
            )
        return [_row_to_notification(r) for r in rows]


@strawberry.type
class LibraryMutation:
    @strawberry.mutation
    async def library_book_upsert(
        self, info: Info, input: LibraryBookUpsertInput
    ) -> LibraryBook:
        owner = require_authenticated_sub(info)
        book_id = validate_library_id(input.id)
        title = _clamp_str(input.title, MAX_TITLE, required=True) or ""
        author = _clamp_str(input.author, MAX_AUTHOR, required=True) or "Unknown Author"
        status = validate_borrowing_status(input.borrowing_status)
        rating = validate_rating(input.rating)

        async with AsyncSessionLocal() as db:
            existing = (
                await db.execute(
                    select(LibraryBookModel).where(
                        and_(
                            LibraryBookModel.id == book_id,
                            LibraryBookModel.owner_id == owner,
                        )
                    )
                )
            ).scalar_one_or_none()

            prev_status = existing.borrowing_status if existing else None

            if existing:
                existing.title = title
                existing.author = author
                existing.isbn = _clamp_str(input.isbn, MAX_ISBN)
                existing.category = _clamp_str(input.category, MAX_CATEGORY)
                existing.description = _clamp_str(input.description, MAX_DESCRIPTION)
                existing.cover_url = _clamp_str(input.cover_url, MAX_COVER_URL)
                existing.borrowing_status = status
                existing.borrower = _clamp_str(input.borrower, MAX_BORROWER)
                existing.borrow_date = input.borrow_date
                existing.return_due_date = input.return_due_date
                if input.pdf_attached is not None:
                    existing.pdf_attached = bool(input.pdf_attached)
                if input.pdf_storage_path is not None:
                    existing.pdf_storage_path = _clamp_str(input.pdf_storage_path, 2000)
                if input.pdf_name is not None:
                    existing.pdf_name = _clamp_str(input.pdf_name, MAX_PDF_NAME)
                if input.pdf_content is not None:
                    existing.pdf_content = input.pdf_content
                if input.pages_total is not None:
                    existing.pages_total = max(0, int(input.pages_total))
                if input.pages_read is not None:
                    existing.pages_read = max(0, int(input.pages_read))
                existing.rating = rating
                if input.published_date is not None:
                    existing.published_date = input.published_date
                if input.author_info is not None:
                    existing.author_info = input.author_info
                existing.updated_at = utc_now()
                row = existing
            else:
                row = LibraryBookModel(
                    id=book_id,
                    owner_id=owner,
                    title=title,
                    author=author,
                    isbn=_clamp_str(input.isbn, MAX_ISBN),
                    category=_clamp_str(input.category, MAX_CATEGORY) or "General",
                    description=_clamp_str(input.description, MAX_DESCRIPTION) or "",
                    cover_url=_clamp_str(input.cover_url, MAX_COVER_URL)
                    or "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=300&q=80",
                    borrowing_status=status,
                    borrower=_clamp_str(input.borrower, MAX_BORROWER),
                    borrow_date=input.borrow_date,
                    return_due_date=input.return_due_date,
                    pdf_attached=bool(input.pdf_attached),
                    pdf_storage_path=_clamp_str(input.pdf_storage_path, 2000),
                    pdf_name=_clamp_str(input.pdf_name, MAX_PDF_NAME),
                    pdf_content=input.pdf_content,
                    pages_total=max(0, int(input.pages_total or 200)),
                    pages_read=max(0, int(input.pages_read or 0)),
                    rating=rating,
                    published_date=input.published_date,
                    author_info=input.author_info,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(row)
                db.add(
                    LibraryNotificationModel(
                        id=new_notification_id(),
                        owner_id=owner,
                        message=f'Cataloged "{title}" successfully.',
                        type="success",
                        timestamp=_iso_now(),
                        created_at=utc_now(),
                    )
                )

            if prev_status != status and existing:
                db.add(
                    LibraryNotificationModel(
                        id=new_notification_id(),
                        owner_id=owner,
                        message=(f'Book "{title}" status changed to {status}.'),
                        type="info",
                        timestamp=_iso_now(),
                        created_at=utc_now(),
                    )
                )

            await db.commit()
            await db.refresh(row)
        return _row_to_book(row)

    @strawberry.mutation
    async def library_book_delete(self, info: Info, book_id: str) -> bool:
        owner = require_authenticated_sub(info)
        bid = validate_library_id(book_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(LibraryBookModel).where(
                    and_(
                        LibraryBookModel.id == bid,
                        LibraryBookModel.owner_id == owner,
                    )
                )
            )
            await db.commit()
        return True

    @strawberry.mutation
    async def library_note_upsert(
        self, info: Info, input: LibraryNoteUpsertInput
    ) -> LibraryNote:
        owner = require_authenticated_sub(info)
        note_id = validate_library_id(input.id)
        title = _clamp_str(input.title, MAX_NOTE_TITLE, required=True) or "Untitled"
        content = input.content or ""
        if len(content) > MAX_NOTE_CONTENT:
            raise GraphQLError(
                "Note content exceeds maximum size",
                extensions={"code": "BAD_USER_INPUT"},
            )
        linked = input.linked_book_ids or []
        if len(linked) > 50:
            raise GraphQLError(
                "Too many linked books",
                extensions={"code": "BAD_USER_INPUT"},
            )

        now = _iso_now()
        async with AsyncSessionLocal() as db:
            existing = (
                await db.execute(
                    select(LibraryNoteModel).where(
                        and_(
                            LibraryNoteModel.id == note_id,
                            LibraryNoteModel.owner_id == owner,
                        )
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.title = title
                existing.content = content
                existing.linked_book_ids = [str(x) for x in linked]
                existing.last_saved = now
                existing.updated_at = utc_now()
                row = existing
            else:
                row = LibraryNoteModel(
                    id=note_id,
                    owner_id=owner,
                    title=title,
                    content=content,
                    linked_book_ids=[str(x) for x in linked],
                    last_saved=now,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(row)
            await db.commit()
            await db.refresh(row)
        return _row_to_note(row)

    @strawberry.mutation
    async def library_note_delete(self, info: Info, note_id: str) -> bool:
        owner = require_authenticated_sub(info)
        nid = validate_library_id(note_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(LibraryNoteModel).where(
                    and_(
                        LibraryNoteModel.id == nid,
                        LibraryNoteModel.owner_id == owner,
                    )
                )
            )
            await db.commit()
        return True

    @strawberry.mutation
    async def library_device_upsert(
        self, info: Info, input: LibraryDeviceUpsertInput
    ) -> LibraryDevice:
        owner = require_authenticated_sub(info)
        dev_id = validate_library_id(input.id)
        name = _clamp_str(input.name, 100, required=True) or "Device"
        dtype = validate_device_type(input.type)
        now = input.last_sync or _iso_now()

        async with AsyncSessionLocal() as db:
            existing = (
                await db.execute(
                    select(LibraryDeviceModel).where(
                        and_(
                            LibraryDeviceModel.id == dev_id,
                            LibraryDeviceModel.owner_id == owner,
                        )
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.name = name
                existing.type = dtype
                existing.last_sync = now
                if input.active is not None:
                    existing.active = bool(input.active)
                existing.updated_at = utc_now()
                row = existing
            else:
                row = LibraryDeviceModel(
                    id=dev_id,
                    owner_id=owner,
                    name=name,
                    type=dtype,
                    last_sync=now,
                    active=bool(input.active) if input.active is not None else True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(row)
            await db.commit()
            await db.refresh(row)
        return _row_to_device(row)

    @strawberry.mutation
    async def library_notification_delete(
        self, info: Info, notification_id: str
    ) -> bool:
        owner = require_authenticated_sub(info)
        nid = validate_library_id(notification_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(LibraryNotificationModel).where(
                    and_(
                        LibraryNotificationModel.id == nid,
                        LibraryNotificationModel.owner_id == owner,
                    )
                )
            )
            await db.commit()
        return True

    @strawberry.mutation
    async def library_trigger_sync(self, info: Info) -> JSON:
        owner = require_authenticated_sub(info)
        now = _iso_now()
        async with AsyncSessionLocal() as db:
            devices = (
                (
                    await db.execute(
                        select(LibraryDeviceModel).where(
                            LibraryDeviceModel.owner_id == owner
                        )
                    )
                )
                .scalars()
                .all()
            )
            for d in devices:
                d.last_sync = now
                d.updated_at = utc_now()
            db.add(
                LibraryNotificationModel(
                    id=new_notification_id(),
                    owner_id=owner,
                    message=(
                        f"Workspace synchronization initialized across "
                        f"{len(devices)} verified devices."
                    ),
                    type="success",
                    timestamp=now,
                    created_at=utc_now(),
                )
            )
            await db.commit()
        return cast(
            JSON,
            {"status": "success", "timestamp": now, "deviceCount": len(devices)},
        )
