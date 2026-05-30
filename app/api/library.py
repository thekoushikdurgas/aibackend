"""
AuraBook Library REST API: ISBN lookup, grounded chat, statistics.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.core.auth import get_current_user
from app.database import AsyncSessionLocal
from app.models.library import LibraryBookModel
from app.services.library_service import (
    _iso_now,
    book_row_to_dict,
    compute_statistics,
    seed_library_for_owner,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["Library"])


class LibraryChatRequest(BaseModel):
    query: str
    active_book_ids: List[str] = Field(default_factory=list, alias="activeBookIds")
    chat_history: List[Dict[str, Any]] = Field(
        default_factory=list, alias="chatHistory"
    )

    model_config = {"populate_by_name": True}


class LibraryCitation(BaseModel):
    id: str
    book_id: str = Field(alias="bookId")
    book_title: str = Field(alias="bookTitle")
    quote: Optional[str] = None
    page: Optional[int] = None

    model_config = {"populate_by_name": True}


class LibraryChatResponse(BaseModel):
    id: str
    sender: str = "gemma"
    text: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str

    model_config = {"populate_by_name": True}


async def _fetch_book_lookup(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Google Books + Open Library lookup (ported from AuraBook server.ts)."""
    book_info: Optional[Dict[str, Any]] = None

    if isbn:
        sanitized = isbn.replace("-", "").replace(" ", "")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                gres = await client.get(
                    f"https://www.googleapis.com/books/v1/volumes?q=isbn:{sanitized}"
                )
                if gres.is_success:
                    gdata = gres.json()
                    items = gdata.get("items") or []
                    if items:
                        vol = items[0].get("volumeInfo") or {}
                        book_info = {
                            "title": vol.get("title") or "",
                            "author": ", ".join(vol.get("authors") or [])
                            or "Unknown Author",
                            "description": vol.get("description") or "",
                            "coverUrl": (
                                (vol.get("imageLinks") or {}).get("thumbnail")
                                or (vol.get("imageLinks") or {}).get("smallThumbnail")
                                or ""
                            ),
                            "category": (vol.get("categories") or ["General"])[0],
                            "pagesTotal": int(vol.get("pageCount") or 200),
                            "publishedDate": vol.get("publishedDate") or "",
                            "isbn": sanitized,
                            "source": "Google Books",
                        }
        except Exception as e:
            logger.warning("Google Books ISBN lookup failed: %s", e)

        if not book_info:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    olres = await client.get(
                        "https://openlibrary.org/api/books",
                        params={
                            "bibkeys": f"ISBN:{sanitized}",
                            "format": "json",
                            "jscmd": "data",
                        },
                    )
                    if olres.is_success:
                        ol_data = olres.json()
                        ol_book = ol_data.get(f"ISBN:{sanitized}")
                        if ol_book:
                            book_info = {
                                "title": ol_book.get("title") or "",
                                "author": ", ".join(
                                    a.get("name", "")
                                    for a in (ol_book.get("authors") or [])
                                )
                                or "Unknown Author",
                                "description": ol_book.get("notes")
                                or " ".join(
                                    e.get("text", "")
                                    for e in (ol_book.get("excerpts") or [])
                                )
                                or "",
                                "coverUrl": (
                                    (ol_book.get("cover") or {}).get("large")
                                    or (ol_book.get("cover") or {}).get("medium")
                                    or (ol_book.get("cover") or {}).get("small")
                                    or ""
                                ),
                                "category": (
                                    (ol_book.get("subjects") or [{}])[0].get("name")
                                    if ol_book.get("subjects")
                                    else "General"
                                ),
                                "pagesTotal": int(
                                    ol_book.get("number_of_pages") or 200
                                ),
                                "publishedDate": ol_book.get("publish_date") or "",
                                "isbn": sanitized,
                                "source": "Open Library",
                            }
            except Exception as e:
                logger.warning("Open Library ISBN lookup failed: %s", e)

    if not book_info and (title or author):
        query_parts = []
        if title:
            query_parts.append(f"intitle:{title}")
        if author:
            query_parts.append(f"inauthor:{author}")
        query = "+".join(query_parts)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                gres = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": query, "maxResults": 1},
                )
                if gres.is_success:
                    gdata = gres.json()
                    items = gdata.get("items") or []
                    if items:
                        vol = items[0].get("volumeInfo") or {}
                        ids = vol.get("industryIdentifiers") or []
                        found_isbn = ""
                        for ident in ids:
                            if ident.get("type") == "ISBN_13":
                                found_isbn = ident.get("identifier") or ""
                                break
                        if not found_isbn:
                            for ident in ids:
                                if ident.get("type") == "ISBN_10":
                                    found_isbn = ident.get("identifier") or ""
                                    break
                        book_info = {
                            "title": vol.get("title") or title or "",
                            "author": ", ".join(vol.get("authors") or [])
                            or (author or "Unknown Author"),
                            "description": vol.get("description") or "",
                            "coverUrl": (
                                (vol.get("imageLinks") or {}).get("thumbnail")
                                or (vol.get("imageLinks") or {}).get("smallThumbnail")
                                or ""
                            ),
                            "category": (vol.get("categories") or ["General"])[0],
                            "pagesTotal": int(vol.get("pageCount") or 200),
                            "publishedDate": vol.get("publishedDate") or "",
                            "isbn": found_isbn or isbn or "",
                            "source": "Google Books Search",
                        }
        except Exception as e:
            logger.warning("Google Books title/author search failed: %s", e)

    if (
        book_info
        and book_info.get("author")
        and book_info["author"] != "Unknown Author"
    ):
        try:
            first_author = book_info["author"].split(",")[0].strip()
            async with httpx.AsyncClient(timeout=15.0) as client:
                asres = await client.get(
                    "https://openlibrary.org/search/authors.json",
                    params={"q": first_author},
                )
                if asres.is_success:
                    docs = asres.json().get("docs") or []
                    if docs:
                        author_key = docs[0].get("key", "").lstrip("/authors/")
                        if author_key:
                            adet = await client.get(
                                f"https://openlibrary.org/authors/{author_key}.json"
                            )
                            if adet.is_success:
                                bio = adet.json().get("bio") or ""
                                if isinstance(bio, dict):
                                    bio = bio.get("value") or ""
                                if bio:
                                    book_info["authorInfo"] = str(bio)
        except Exception as e:
            logger.warning("Author bio lookup failed: %s", e)

    return book_info


@router.get("/books/lookup")
async def library_books_lookup(
    isbn: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    _ = user
    book_info = await _fetch_book_lookup(isbn=isbn, title=title, author=author)
    if not book_info:
        raise HTTPException(
            status_code=404,
            detail="Book details could not be found under any register.",
        )
    return book_info


@router.get("/statistics")
async def library_statistics(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    owner = str(user.get("sub") or user.get("id") or "")
    if not owner:
        raise HTTPException(status_code=401, detail="Authentication required")
    async with AsyncSessionLocal() as db:
        await seed_library_for_owner(db, owner)
        await db.commit()
        rows = (
            (
                await db.execute(
                    select(LibraryBookModel).where(LibraryBookModel.owner_id == owner)
                )
            )
            .scalars()
            .all()
        )
    return compute_statistics(list(rows))


@router.post("/chat")
async def library_chat(
    body: LibraryChatRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    owner = str(user.get("sub") or user.get("id") or "")
    if not owner:
        raise HTTPException(status_code=401, detail="Authentication required")
    query = (body.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    async with AsyncSessionLocal() as db:
        await seed_library_for_owner(db, owner)
        await db.commit()
        stmt = select(LibraryBookModel).where(LibraryBookModel.owner_id == owner)
        if body.active_book_ids:
            stmt = stmt.where(LibraryBookModel.id.in_(body.active_book_ids))
        books = (await db.execute(stmt)).scalars().all()

    if not books:
        books_list: List[LibraryBookModel] = []
    else:
        books_list = list(books)

    book_context_parts: List[str] = []
    for idx, b in enumerate(books_list):
        d = book_row_to_dict(b)
        if d["borrowingStatus"] == "borrowed":
            borrow_line = (
                f"(Borrowed by {d.get('borrower')}, due {d.get('returnDueDate')})"
            )
        else:
            borrow_line = "(Available)"
        book_context_parts.append(
            f"[Source ID: {b.id}] [Book Reference {idx + 1}]\n"
            f"Title: {d['title']}\n"
            f"Author: {d['author']}\n"
            f"Category: {d['category']}\n"
            f"Summary & Content: {d.get('pdfContent') or d.get('description')}\n"
            f"Borrowing Status: {d['borrowingStatus']} {borrow_line}\n"
            f"Pages Progress: Read {d['pagesRead']} out of {d['pagesTotal']} pages\n"
            f"ISBN: {d['isbn']}"
        )
    book_context = "\n\n---\n\n".join(book_context_parts)

    system_instruction = (
        'You are "Gemma 4", a research assistant in the AuraBook NotebookLM workspace. '
        "Synthesize the user's library to answer with citations to book titles and authors. "
        "Use Markdown with clear structure."
    )

    api_key = settings.gemini_api_key
    text_output: Optional[str] = None

    if (
        api_key
        and "placeholder" not in api_key.lower()
        and "your-api-key" not in api_key.lower()
    ):
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"The user selected these references:\n\n{book_context}\n\n"
                            f"User query:\n\n{query}"
                        )
                    }
                ],
            }
        ]
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"temperature": 0.3},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                res_data = response.json()
                candidates = res_data.get("candidates") or []
                if candidates:
                    parts = (candidates[0].get("content") or {}).get("parts") or []
                    if parts:
                        text_output = parts[0].get("text") or ""
        except Exception as e:
            logger.error("Library Gemini chat error: %s", e)

    if not text_output:
        text_output = _offline_chat_response(query, books_list)

    citations: List[Dict[str, Any]] = []
    lower_out = text_output.lower()
    for b in books_list:
        d = book_row_to_dict(b)
        title_l = d["title"].lower()
        author_l = d["author"].lower()
        if title_l in lower_out or author_l in lower_out or title_l in query.lower():
            snippet = d.get("pdfContent") or d.get("description") or ""
            citations.append(
                {
                    "id": f"cit-{b.id}-{int(time.time() * 1000)}",
                    "bookId": b.id,
                    "bookTitle": d["title"],
                    "quote": (snippet[:150] + "...") if len(snippet) > 150 else snippet,
                    "page": max(1, int(d["pagesRead"] or 0) // 2),
                }
            )

    return LibraryChatResponse(
        id=f"msg-{uuid.uuid4().hex[:12]}",
        sender="gemma",
        text=text_output,
        citations=citations,
        timestamp=_iso_now(),
    ).model_dump(by_alias=True)


def _offline_chat_response(query: str, books: List[LibraryBookModel]) -> str:
    lower_query = query.lower()
    matched = [
        b
        for b in books
        if lower_query in (b.title or "").lower()
        or lower_query in (b.author or "").lower()
        or lower_query in (b.category or "").lower()
    ]
    answer = "### Gemma 4 Research Summary\n\n*(Offline emulation mode)*\n\n"
    if matched:
        for b in matched:
            d = book_row_to_dict(b)
            answer += f"#### *{d['title']}* by {d['author']}\n"
            answer += f"- **Status**: {d['borrowingStatus']}\n"
            answer += f"- **Overview**: {d['description'][:300]}...\n\n"
    else:
        answer += (
            f'No direct match for "{query}" in {len(books)} selected references. '
            "Select books in the sidebar to ground responses.\n"
        )
    return answer
