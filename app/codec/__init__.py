"""vSQL codec: Data bytes <-> RGBA frames <-> video."""

from .format_constants import (
    FRAME_WIDTH,
    FRAME_HEIGHT,
    PIXELS_PER_FRAME,
    FRAME_CAPACITY,
    HEADER_SIZE,
    MAX_PAYLOAD_FRAME_0,
    LOGICAL_TOTAL_FRAMES_DEFAULT,
    MAGIC_VSQL_COMPRESSED,
    MAGIC_VSQL_RAW,
)
from .payload import encode_data_to_stream, decode_stream_to_data
from .frames import stream_to_frames, frames_to_stream, frames_pad_to_count

__all__ = [
    "FRAME_WIDTH",
    "FRAME_HEIGHT",
    "PIXELS_PER_FRAME",
    "FRAME_CAPACITY",
    "HEADER_SIZE",
    "MAX_PAYLOAD_FRAME_0",
    "LOGICAL_TOTAL_FRAMES_DEFAULT",
    "MAGIC_VSQL_COMPRESSED",
    "MAGIC_VSQL_RAW",
    "encode_data_to_stream",
    "decode_stream_to_data",
    "stream_to_frames",
    "frames_to_stream",
    "frames_pad_to_count",
]
