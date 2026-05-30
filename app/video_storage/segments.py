"""Segmented video table manifests for high-throughput appends.

The current storage engine rewrites a whole table video for row mutations. This
module defines the append-friendly manifest used by future high-speed storage:
each append batch becomes an immutable segment and the manifest maps row ranges
to segment files.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SEGMENT_MANIFEST_VERSION = 1


@dataclass(frozen=True)
class SegmentInfo:
    """One immutable video segment covering a contiguous row range."""

    id: str
    path: str
    row_start: int
    row_count: int
    frame_count: int
    payload_sha256: str = ""
    video_size_bytes: int = 0

    @property
    def row_end_exclusive(self) -> int:
        return self.row_start + self.row_count


@dataclass
class SegmentManifest:
    """A table's segmented storage map."""

    version: int
    table_name: str
    segments: list[SegmentInfo]

    @property
    def total_rows(self) -> int:
        return sum(seg.row_count for seg in self.segments)

    def find_segment_for_rowid(self, rowid: int) -> SegmentInfo | None:
        """Return the segment containing one-based SQL-style ``rowid``."""

        zero_based = rowid - 1
        for segment in self.segments:
            if segment.row_start <= zero_based < segment.row_end_exclusive:
                return segment
        return None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "table_name": self.table_name,
            "total_rows": self.total_rows,
            "segments": [asdict(seg) for seg in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SegmentManifest":
        return cls(
            version=int(data.get("version", SEGMENT_MANIFEST_VERSION)),
            table_name=str(data.get("table_name") or "data"),
            segments=[SegmentInfo(**item) for item in data.get("segments", [])],
        )


class SegmentStore:
    """Read/write segment manifests below a table directory."""

    def __init__(self, table_dir: Path | str, table_name: str):
        self.table_dir = Path(table_dir)
        self.table_name = table_name
        self.segment_dir = self.table_dir / "segments"
        self.manifest_path = self.table_dir / "segments.json"

    def load(self) -> SegmentManifest:
        if not self.manifest_path.is_file():
            return SegmentManifest(
                version=SEGMENT_MANIFEST_VERSION,
                table_name=self.table_name,
                segments=[],
            )
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return SegmentManifest.from_dict(data)

    def save(self, manifest: SegmentManifest) -> None:
        self.table_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        os.replace(tmp, self.manifest_path)

    def add_existing_video_segment(
        self,
        source_video: Path | str,
        *,
        row_count: int,
        frame_count: int,
        payload_sha256: str = "",
    ) -> SegmentInfo:
        """Copy an encoded batch video into the next immutable segment slot."""

        source = Path(source_video)
        if row_count < 0:
            raise ValueError("row_count must be non-negative")
        manifest = self.load()
        segment_id = f"segment_{len(manifest.segments) + 1:06d}"
        self.segment_dir.mkdir(parents=True, exist_ok=True)
        dest = self.segment_dir / f"{segment_id}{source.suffix or '.mkv'}"
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        shutil.copy2(source, tmp)
        os.replace(tmp, dest)
        segment = SegmentInfo(
            id=segment_id,
            path=str(dest.relative_to(self.table_dir)),
            row_start=manifest.total_rows,
            row_count=row_count,
            frame_count=frame_count,
            payload_sha256=payload_sha256,
            video_size_bytes=dest.stat().st_size,
        )
        manifest.segments.append(segment)
        self.save(manifest)
        return segment

    def iter_segment_paths(self) -> Iterable[Path]:
        manifest = self.load()
        for segment in manifest.segments:
            yield self.table_dir / segment.path
