"""Sidecar page indexes for segmented vSQL tables."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

INDEX_VERSION = 1


@dataclass(frozen=True)
class PageIndexEntry:
    """Maps a row range to segment/page/frame coordinates."""

    segment_id: str
    page_id: int
    frame_start: int
    frame_count: int
    row_start: int
    row_count: int
    min_values: dict[str, Any] = field(default_factory=dict)
    max_values: dict[str, Any] = field(default_factory=dict)

    @property
    def row_end_exclusive(self) -> int:
        return self.row_start + self.row_count

    def contains_rowid(self, rowid: int) -> bool:
        zero = rowid - 1
        return self.row_start <= zero < self.row_end_exclusive

    def may_match_range(self, column: str, value: Any) -> bool:
        """Return False only when page stats prove the value cannot match."""

        if column not in self.min_values or column not in self.max_values:
            return True
        try:
            return self.min_values[column] <= value <= self.max_values[column]
        except TypeError:
            return True


@dataclass
class PageIndex:
    """Page-level row and predicate metadata for one table."""

    version: int
    table_name: str
    pages: list[PageIndexEntry] = field(default_factory=list)
    hash_indexes: dict[str, dict[str, list[int]]] = field(default_factory=dict)

    def find_pages_for_rowid(self, rowid: int) -> list[PageIndexEntry]:
        return [page for page in self.pages if page.contains_rowid(rowid)]

    def find_pages_for_value(self, column: str, value: Any) -> list[PageIndexEntry]:
        key = _hash_value(value)
        column_hash = self.hash_indexes.get(column)
        if column_hash is not None:
            page_ids = column_hash.get(key, [])
            wanted = set(page_ids)
            return [page for page in self.pages if page.page_id in wanted]
        return [page for page in self.pages if page.may_match_range(column, value)]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "table_name": self.table_name,
            "pages": [asdict(page) for page in self.pages],
            "hash_indexes": self.hash_indexes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PageIndex":
        return cls(
            version=int(data.get("version", INDEX_VERSION)),
            table_name=str(data.get("table_name") or "data"),
            pages=[PageIndexEntry(**item) for item in data.get("pages", [])],
            hash_indexes={
                str(col): {str(k): list(v) for k, v in values.items()}
                for col, values in data.get("hash_indexes", {}).items()
            },
        )


def _hash_value(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


class PageIndexStore:
    """Read/write page index sidecars."""

    def __init__(self, table_dir: Path | str, table_name: str):
        self.table_dir = Path(table_dir)
        self.table_name = table_name
        self.index_path = self.table_dir / "page-index.json"

    def load(self) -> PageIndex:
        if not self.index_path.is_file():
            return PageIndex(version=INDEX_VERSION, table_name=self.table_name)
        return PageIndex.from_dict(
            json.loads(self.index_path.read_text(encoding="utf-8"))
        )

    def save(self, index: PageIndex) -> None:
        self.table_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(index.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        os.replace(tmp, self.index_path)

    def add_page(
        self,
        *,
        segment_id: str,
        page_id: int,
        frame_start: int,
        frame_count: int,
        row_start: int,
        row_count: int,
        min_values: dict[str, Any] | None = None,
        max_values: dict[str, Any] | None = None,
        hash_values: dict[str, list[Any]] | None = None,
    ) -> PageIndexEntry:
        index = self.load()
        entry = PageIndexEntry(
            segment_id=segment_id,
            page_id=page_id,
            frame_start=frame_start,
            frame_count=frame_count,
            row_start=row_start,
            row_count=row_count,
            min_values=min_values or {},
            max_values=max_values or {},
        )
        index.pages.append(entry)
        for column, values in (hash_values or {}).items():
            column_index = index.hash_indexes.setdefault(column, {})
            for value in values:
                key = _hash_value(value)
                ids = column_index.setdefault(key, [])
                if page_id not in ids:
                    ids.append(page_id)
        self.save(index)
        return entry
