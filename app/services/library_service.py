"""Library (AuraBook) validation, seeding, and shared helpers."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from graphql import GraphQLError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import (
    LibraryBookModel,
    LibraryDeviceModel,
    LibraryNoteModel,
    LibraryNotificationModel,
)
from app.utils.helpers import utc_now

VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
BORROWING_STATUSES = frozenset({"available", "borrowed"})
DEVICE_TYPES = frozenset({"mobile", "tablet", "desktop"})
NOTIFICATION_TYPES = frozenset({"info", "warning", "success"})

MAX_TITLE = 500
MAX_AUTHOR = 200
MAX_ISBN = 32
MAX_CATEGORY = 100
MAX_DESCRIPTION = 5000
MAX_COVER_URL = 2000
MAX_BORROWER = 200
MAX_PDF_NAME = 500
MAX_NOTE_TITLE = 300
MAX_NOTE_CONTENT = 3_000_000
MAX_MESSAGE = 1000
MAX_LINKED_BOOKS = 50


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_library_id(doc_id: str, field: str = "id") -> str:
    s = (doc_id or "").strip()
    if not s or len(s) > 128 or not VALID_ID_RE.match(s):
        raise GraphQLError(
            f"Invalid {field}: use alphanumeric, underscore, or hyphen (max 128 chars)",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def validate_rating(rating: Optional[float | int]) -> Optional[float]:
    if rating is None:
        return None
    r = float(rating)
    if r < 1 or r > 5:
        raise GraphQLError(
            "rating must be between 1 and 5",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return r


def validate_borrowing_status(status: Optional[str]) -> str:
    s = (status or "available").strip()
    if s not in BORROWING_STATUSES:
        raise GraphQLError(
            "borrowing_status must be 'available' or 'borrowed'",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def validate_device_type(device_type: str) -> str:
    s = device_type.strip()
    if s not in DEVICE_TYPES:
        raise GraphQLError(
            "device type must be mobile, tablet, or desktop",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def validate_notification_type(notif_type: str) -> str:
    s = notif_type.strip()
    if s not in NOTIFICATION_TYPES:
        raise GraphQLError(
            "notification type must be info, warning, or success",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s


def _clamp_str(
    val: Optional[str], max_len: int, required: bool = False
) -> Optional[str]:
    if val is None:
        if required:
            raise GraphQLError(
                "Required string field missing", extensions={"code": "BAD_USER_INPUT"}
            )
        return None
    s = str(val).strip()
    if required and not s:
        raise GraphQLError(
            "Required string field empty", extensions={"code": "BAD_USER_INPUT"}
        )
    if len(s) > max_len:
        raise GraphQLError(
            f"String exceeds maximum length of {max_len}",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return s or None


def book_row_to_dict(row: LibraryBookModel) -> Dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "author": row.author,
        "isbn": row.isbn or "",
        "category": row.category or "",
        "description": row.description or "",
        "coverUrl": row.cover_url or "",
        "borrowingStatus": row.borrowing_status,
        "borrower": row.borrower,
        "borrowDate": row.borrow_date,
        "returnDueDate": row.return_due_date,
        "pdfAttached": bool(row.pdf_attached),
        "pdfStoragePath": row.pdf_storage_path,
        "pdfName": row.pdf_name,
        "pdfContent": row.pdf_content,
        "pagesTotal": int(row.pages_total or 0),
        "pagesRead": int(row.pages_read or 0),
        "rating": row.rating,
        "publishedDate": row.published_date,
        "authorInfo": row.author_info,
    }


def compute_statistics(books: List[LibraryBookModel]) -> Dict[str, Any]:
    total = len(books)
    borrowed = sum(1 for b in books if b.borrowing_status == "borrowed")
    completed = sum(
        1
        for b in books
        if b.pages_total and b.pages_read and b.pages_read >= b.pages_total
    )
    pages_read = sum(int(b.pages_read or 0) for b in books)
    pages_sum = sum(int(b.pages_total or 0) for b in books) or 1
    ratings = [float(b.rating) for b in books if b.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    cats: Dict[str, int] = {}
    for b in books:
        cat = (b.category or "General").strip() or "General"
        cats[cat] = cats.get(cat, 0) + 1
    return {
        "totalBooks": total,
        "borrowedBooks": borrowed,
        "completedBooks": completed,
        "totalPagesRead": pages_read,
        "readingEfficiency": round((pages_read / pages_sum) * 100, 1),
        "averageRating": round(avg_rating, 2),
        "categoryDistribution": [
            {"name": k, "value": v}
            for k, v in sorted(cats.items(), key=lambda x: -x[1])
        ],
    }


async def count_books(db: AsyncSession, owner_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(LibraryBookModel)
        .where(LibraryBookModel.owner_id == owner_id)
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def seed_library_for_owner(db: AsyncSession, owner_id: str) -> None:
    """Seed demo catalog when owner has no books (AuraBook firebaseSeeder parity)."""
    if await count_books(db, owner_id) > 0:
        return

    now = _iso_now()
    uid_suffix = re.sub(r"[^a-zA-Z0-9_]", "_", owner_id)[:64]

    books_data: List[Dict[str, Any]] = [
        {
            "id": f"book-ddia-{uid_suffix}",
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "isbn": "9781449373320",
            "category": "Computer Science",
            "description": (
                "An in-depth guide to modern system architecture, detailing data storage "
                "engines, encoding systems, distributed algorithms, replication, partition "
                "mechanisms, and stream processing in complex large-scale platforms."
            ),
            "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=300&q=80",
            "borrowing_status": "available",
            "pdf_attached": True,
            "pdf_name": "ddia_chapter_1_storage.pdf",
            "pdf_content": (
                "Designing Data-Intensive Applications. Chapter 1: Storage and Retrieval. "
                "Martin Kleppmann explores hash indexes, LSM Trees, SSTables, and B-Trees."
            ),
            "pages_total": 610,
            "pages_read": 345,
            "rating": 5.0,
            "published_date": "2017-03-16",
            "author_info": (
                "Martin Kleppmann is a researcher in distributed systems at the University of Cambridge."
            ),
        },
        {
            "id": f"book-phm-{uid_suffix}",
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "isbn": "9780593135204",
            "category": "Science Fiction",
            "description": (
                "A thrilling cosmic survival story of Ryland Grace on a mission to save humanity."
            ),
            "cover_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=300&q=80",
            "borrowing_status": "borrowed",
            "borrower": "Alice Henderson",
            "borrow_date": "2026-05-15",
            "return_due_date": "2026-06-15",
            "pdf_attached": False,
            "pages_total": 476,
            "pages_read": 476,
            "rating": 5.0,
            "published_date": "2021-05-04",
            "author_info": "Andy Weir is an American novelist; The Martian was his debut novel.",
        },
        {
            "id": f"book-sapiens-{uid_suffix}",
            "title": "Sapiens: A Brief History of Humankind",
            "author": "Yuval Noah Harari",
            "isbn": "9780062316097",
            "category": "History",
            "description": (
                "An evolutionary epic exploring how Homo sapiens came to dominate the Earth."
            ),
            "cover_url": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=300&q=80",
            "borrowing_status": "available",
            "pdf_attached": True,
            "pdf_name": "sapiens_summary.pdf",
            "pdf_content": (
                "Sapiens explores the Cognitive, Agricultural, and Scientific revolutions."
            ),
            "pages_total": 512,
            "pages_read": 120,
            "rating": 4.0,
            "published_date": "2011-01-01",
            "author_info": "Yuval Noah Harari is an Israeli public intellectual and historian.",
        },
    ]

    for b in books_data:
        db.add(
            LibraryBookModel(
                id=b["id"],
                owner_id=owner_id,
                title=b["title"],
                author=b["author"],
                isbn=b.get("isbn"),
                category=b.get("category"),
                description=b.get("description"),
                cover_url=b.get("cover_url"),
                borrowing_status=b.get("borrowing_status", "available"),
                borrower=b.get("borrower"),
                borrow_date=b.get("borrow_date"),
                return_due_date=b.get("return_due_date"),
                pdf_attached=bool(b.get("pdf_attached")),
                pdf_name=b.get("pdf_name"),
                pdf_content=b.get("pdf_content"),
                pages_total=int(b["pages_total"]),
                pages_read=int(b["pages_read"]),
                rating=b.get("rating"),
                published_date=b.get("published_date"),
                author_info=b.get("author_info"),
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )

    note_id = f"note-1-{uid_suffix}"
    db.add(
        LibraryNoteModel(
            id=note_id,
            owner_id=owner_id,
            title="Distributed Systems & LSM Study Notes",
            content=(
                "## Notes on Kleppmann's DDIA\n\n"
                "- **LSM Trees** buffer writes in memory before flushing to SSTables.\n"
                "- **B-Trees** offer consistent read performance with in-place updates.\n"
            ),
            linked_book_ids=[f"book-ddia-{uid_suffix}"],
            last_saved=now,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )

    for dev in (
        {
            "id": f"dev-iphone-{uid_suffix}",
            "name": "iPhone 15 Pro Max",
            "type": "mobile",
        },
        {"id": f"dev-ipad-{uid_suffix}", "name": "iPad Pro 11-inch", "type": "tablet"},
    ):
        db.add(
            LibraryDeviceModel(
                id=dev["id"],
                owner_id=owner_id,
                name=dev["name"],
                type=dev["type"],
                last_sync=now,
                active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )

    db.add(
        LibraryNotificationModel(
            id=f"not-1-{uid_suffix}",
            owner_id=owner_id,
            message=(
                "Reminder: 'Project Hail Mary' is currently borrowed by Alice Henderson. "
                "Return date: June 15."
            ),
            type="warning",
            timestamp=now,
            created_at=utc_now(),
        )
    )

    await db.flush()


def new_notification_id() -> str:
    return f"not-{uuid.uuid4().hex[:12]}"
