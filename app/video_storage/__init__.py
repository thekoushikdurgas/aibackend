"""Video Storage: Pure video-based data persistence system.

Data is stored directly as RGBA pixels in MP4 video frames.
"""

from .engine import VideoDB
from .encoder import DataEncoder
from .decoder import DataDecoder
from .schema import VideoSchema
from .crud import VideoCRUD
from .query import VideoQuery
from .integrity import DataIntegrity
from .exceptions import (
    VideoStorageError,
    VideoEncodingError,
    VideoDecodingError,
    SchemaError,
    IntegrityError,
)

__all__ = [
    "VideoDB",
    "DataEncoder",
    "DataDecoder",
    "VideoSchema",
    "VideoCRUD",
    "VideoQuery",
    "DataIntegrity",
    "VideoStorageError",
    "VideoEncodingError",
    "VideoDecodingError",
    "SchemaError",
    "IntegrityError",
]
