"""Versioned binary row pages for high-throughput vSQL storage.

This module is intentionally independent from the current CSV-backed storage
path. It defines the binary layout needed for million-row/sec experiments:
compact typed cells, nullable bitmaps, variable-width values, and per-page CRC.
"""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence

from .exceptions import VideoDecodingError, VideoEncodingError
from .schema import VideoSchema

MAGIC = b"VSQLBP1\0"
VERSION = 1
HEADER_STRUCT = struct.Struct(">8sHHIIHI")
# magic, version, flags, row_count, body_len, column_count, checksum_crc32
NULL_FLAG = 1


@dataclass(frozen=True)
class BinaryPage:
    """Decoded binary page payload."""

    rows: list[dict[str, Any]]
    row_count: int
    body_bytes: int
    checksum_crc32: int


def _coerce_value(value: Any, data_type: str) -> bytes:
    if data_type == "INTEGER":
        return struct.pack(">q", int(value))
    if data_type == "REAL":
        return struct.pack(">d", float(value))
    if data_type == "BLOB":
        raw = bytes(value)
        return struct.pack(">I", len(raw)) + raw
    raw = str(value).encode("utf-8")
    return struct.pack(">I", len(raw)) + raw


def _read_value(buf: memoryview, offset: int, data_type: str) -> tuple[Any, int]:
    if data_type == "INTEGER":
        if offset + 8 > len(buf):
            raise VideoDecodingError("INTEGER cell exceeds page body")
        return struct.unpack_from(">q", buf, offset)[0], offset + 8
    if data_type == "REAL":
        if offset + 8 > len(buf):
            raise VideoDecodingError("REAL cell exceeds page body")
        return struct.unpack_from(">d", buf, offset)[0], offset + 8
    if offset + 4 > len(buf):
        raise VideoDecodingError("Variable-width cell length exceeds page body")
    size = struct.unpack_from(">I", buf, offset)[0]
    offset += 4
    if offset + size > len(buf):
        raise VideoDecodingError("Variable-width cell exceeds page body")
    raw = bytes(buf[offset : offset + size])
    offset += size
    if data_type == "BLOB":
        return raw, offset
    return raw.decode("utf-8"), offset


def encode_page(schema: VideoSchema, rows: Sequence[dict[str, Any]]) -> bytes:
    """Encode a row batch into one binary page."""

    columns = schema.columns
    if not columns:
        raise VideoEncodingError("Cannot encode binary page without columns")

    null_bytes = math.ceil(len(columns) / 8)
    body = bytearray()
    for row in rows:
        bitmap = bytearray(null_bytes)
        cells = bytearray()
        for index, col in enumerate(columns):
            value = row.get(col.name)
            if value is None:
                bitmap[index // 8] |= 1 << (index % 8)
                continue
            cells += _coerce_value(value, col.data_type)
        body += bitmap
        body += cells

    checksum = zlib.crc32(body) & 0xFFFFFFFF
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        NULL_FLAG,
        len(rows),
        len(body),
        len(columns),
        checksum,
    )
    return header + body


def decode_page(schema: VideoSchema, page: bytes) -> BinaryPage:
    """Decode and validate one binary row page."""

    if len(page) < HEADER_STRUCT.size:
        raise VideoDecodingError("Binary page is shorter than header")
    magic, version, _flags, row_count, body_len, column_count, checksum = (
        HEADER_STRUCT.unpack_from(page, 0)
    )
    if magic != MAGIC:
        raise VideoDecodingError("Invalid binary page magic")
    if version != VERSION:
        raise VideoDecodingError(f"Unsupported binary page version {version}")
    if column_count != len(schema.columns):
        raise VideoDecodingError(
            f"Binary page column count {column_count} does not match schema {len(schema.columns)}"
        )
    body_start = HEADER_STRUCT.size
    body_end = body_start + body_len
    if body_end > len(page):
        raise VideoDecodingError("Binary page body length exceeds page buffer")
    body = memoryview(page)[body_start:body_end]
    actual = zlib.crc32(body) & 0xFFFFFFFF
    if actual != checksum:
        raise VideoDecodingError("Binary page checksum mismatch")

    null_bytes = math.ceil(len(schema.columns) / 8)
    rows: list[dict[str, Any]] = []
    offset = 0
    for _ in range(row_count):
        if offset + null_bytes > len(body):
            raise VideoDecodingError("Row null bitmap exceeds page body")
        bitmap = body[offset : offset + null_bytes]
        offset += null_bytes
        row: dict[str, Any] = {}
        for index, col in enumerate(schema.columns):
            is_null = bool(bitmap[index // 8] & (1 << (index % 8)))
            if is_null:
                row[col.name] = None
                continue
            row[col.name], offset = _read_value(body, offset, col.data_type)
        rows.append(row)

    if offset != len(body):
        raise VideoDecodingError("Binary page has trailing undecoded bytes")
    return BinaryPage(
        rows=rows,
        row_count=row_count,
        body_bytes=body_len,
        checksum_crc32=checksum,
    )


def paginate_rows(
    schema: VideoSchema,
    rows: Iterable[dict[str, Any]],
    *,
    max_page_bytes: int,
) -> Iterator[bytes]:
    """Yield encoded pages no larger than ``max_page_bytes`` when possible."""

    batch: list[dict[str, Any]] = []
    for row in rows:
        candidate = batch + [row]
        encoded = encode_page(schema, candidate)
        if batch and len(encoded) > max_page_bytes:
            yield encode_page(schema, batch)
            batch = [row]
        else:
            batch = candidate
    if batch:
        yield encode_page(schema, batch)
