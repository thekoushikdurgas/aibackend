"""Video storage exception classes."""


class VideoStorageError(Exception):
    """Base exception for video storage operations."""

    pass


class VideoEncodingError(VideoStorageError):
    """Raised when data encoding to video frames fails."""

    pass


class VideoDecodingError(VideoStorageError):
    """Raised when video frame decoding fails."""

    pass


class SchemaError(VideoStorageError):
    """Raised when schema operations fail."""

    pass


class IntegrityError(VideoStorageError):
    """Raised when data integrity verification fails."""

    pass


class FrameHeaderError(VideoStorageError):
    """Raised when frame header parsing fails."""

    pass


class QueryError(VideoStorageError):
    """Raised when video query operations fail."""

    pass


class ValidationError(VideoStorageError):
    """Raised when data validation fails."""

    pass
