"""RAG document metadata CRUD."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select, update, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RAGDocument
from app.utils.helpers import utc_now


class RAGDocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> RAGDocument:
        meta = data.get("metadata", data.get("extra_metadata", {}))
        rid = data.get("id") or str(uuid.uuid4())
        row = RAGDocument(
            id=rid,
            user_id=data["user_id"],
            title=data["title"],
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            mime_type=data.get("mime_type"),
            storage_path=data.get("storage_path"),
            vector_ids=data.get("vector_ids") or [],
            extra_metadata=meta if isinstance(meta, dict) else {},
            indexed=bool(data.get("indexed", False)),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, document_id: str) -> Optional[RAGDocument]:
        r = await self.session.execute(
            select(RAGDocument).where(RAGDocument.id == document_id)
        )
        return r.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[RAGDocument]:
        r = await self.session.execute(
            select(RAGDocument)
            .where(RAGDocument.user_id == user_id)
            .order_by(RAGDocument.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(r.scalars().all())

    async def update(
        self, document_id: str, updates: Dict[str, Any]
    ) -> Optional[RAGDocument]:
        row = await self.get(document_id)
        if row is None:
            return None
        vals: Dict[str, Any] = {"updated_at": utc_now()}
        for k in (
            "title",
            "file_path",
            "file_size",
            "mime_type",
            "storage_path",
            "indexed",
        ):
            if k in updates and updates[k] is not None:
                vals[k] = updates[k]
        if "vector_ids" in updates and updates["vector_ids"] is not None:
            vals["vector_ids"] = updates["vector_ids"]
        if "metadata" in updates and updates["metadata"] is not None:
            vals["extra_metadata"] = updates["metadata"]
        await self.session.execute(
            update(RAGDocument).where(RAGDocument.id == document_id).values(**vals)
        )
        await self.session.refresh(row)
        return await self.get(document_id)

    async def delete(self, document_id: str) -> bool:
        r = cast(
            CursorResult[Any],
            await self.session.execute(
                delete(RAGDocument).where(RAGDocument.id == document_id)
            ),
        )
        return (r.rowcount or 0) > 0
