"""Compress data bytes and build/parse vSQL byte stream.

Compression support matrix:
  VSQL  (0x56 53 51 4C) — raw (uncompressed)
  VSQC  (0x56 53 51 43) — zlib deflate (legacy, still decoded for compat)
  VSQZ  (0x56 53 51 5A) — zstd (default for new writes; 3-5x faster than zlib)
"""

import hashlib
import struct
import zlib
from typing import Tuple

from .compression import zstd_compress, zstd_decompress
from .format_constants import (
    HEADER_SIZE,
    MAGIC_VSQL_COMPRESSED,
    MAGIC_VSQL_RAW,
    payload_frame_count_for_stream_length,
)

# New magic for zstd-compressed streams.
MAGIC_VSQL_ZSTD = b"VSQZ"

# All known magics accepted on decode.
_KNOWN_MAGICS = {MAGIC_VSQL_RAW, MAGIC_VSQL_COMPRESSED, MAGIC_VSQL_ZSTD}


def encode_data_to_stream(
    data_bytes: bytes,
    compress: bool = True,
    compression_algorithm: str = "zstd",
) -> Tuple[bytes, int, int]:
    """Build full stream: header (44) + payload.

    Args:
        data_bytes: Raw data to store.
        compress: Whether to compress the payload.
        compression_algorithm: "zstd" (default, fast) or "zlib" (legacy).

    Returns:
        (stream_bytes, compressed_length, payload_frame_count)
    """
    if compress:
        if compression_algorithm == "zlib":
            payload = zlib.compress(data_bytes, level=9)
            magic = MAGIC_VSQL_COMPRESSED
        else:
            payload = zstd_compress(data_bytes)
            magic = MAGIC_VSQL_ZSTD
    else:
        payload = data_bytes
        magic = MAGIC_VSQL_RAW

    compressed_length = len(payload)
    digest = hashlib.sha256(payload).digest()
    if len(digest) != 32:
        raise RuntimeError("SHA-256 must be 32 bytes")

    total_stream_len = HEADER_SIZE + compressed_length
    payload_frames = payload_frame_count_for_stream_length(total_stream_len)

    header = bytearray(HEADER_SIZE)
    header[0:4] = magic
    struct.pack_into(">I", header, 4, payload_frames)
    struct.pack_into(">I", header, 8, compressed_length)
    header[12:44] = digest

    return bytes(header) + payload, compressed_length, payload_frames


def decode_stream_to_data(stream: bytes) -> bytes:
    """Parse header + payload, verify hash, decompress if needed.

    Supports VSQL (raw), VSQC (zlib), and VSQZ (zstd) streams.
    """
    if len(stream) < HEADER_SIZE:
        raise ValueError("Stream too short for vSQL header")

    magic = stream[0:4]
    _ = struct.unpack_from(">I", stream, 4)[0]
    compressed_length = struct.unpack_from(">I", stream, 8)[0]
    expected_hash = stream[12:44]

    if magic not in _KNOWN_MAGICS:
        raise ValueError(f"Invalid vSQL magic: {magic!r}")

    if compressed_length < 0 or HEADER_SIZE + compressed_length > len(stream):
        raise ValueError("Invalid compressed_length / truncated stream")

    payload = stream[HEADER_SIZE : HEADER_SIZE + compressed_length]
    got = hashlib.sha256(payload).digest()
    if got != expected_hash:
        raise ValueError("Data integrity check failed (SHA-256 mismatch)")

    if magic == MAGIC_VSQL_COMPRESSED:
        return zlib.decompress(payload)
    if magic == MAGIC_VSQL_ZSTD:
        return zstd_decompress(payload)
    return payload
