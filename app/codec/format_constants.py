"""Binary layout constants (aligned with docs/vsql/lib/vsql.ts)."""

import math

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
PIXELS_PER_FRAME = FRAME_WIDTH * FRAME_HEIGHT
BYTES_PER_PIXEL = 3
FRAME_CAPACITY = PIXELS_PER_FRAME * BYTES_PER_PIXEL
HEADER_SIZE = 44
MAX_PAYLOAD_FRAME_0 = FRAME_CAPACITY - HEADER_SIZE

# 1 hour @ 30fps — black tail frames after payload
LOGICAL_TOTAL_FRAMES_DEFAULT = 60 * 60 * 30  # 108000

MAGIC_VSQL_COMPRESSED = b"VSQC"  # zlib (legacy)
MAGIC_VSQL_RAW = b"VSQL"  # uncompressed
MAGIC_VSQL_ZSTD = b"VSQZ"  # zstd (preferred)


def payload_frame_count_for_stream_length(total_stream_bytes: int) -> int:
    """Number of frames needed to store header+payload stream."""
    if total_stream_bytes <= 0:
        return 0
    if total_stream_bytes <= FRAME_CAPACITY:
        return 1
    rest = total_stream_bytes - FRAME_CAPACITY
    return 1 + math.ceil(rest / FRAME_CAPACITY)
