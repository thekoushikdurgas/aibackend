"""Optional zstd compression helpers (lazy import with typed surface)."""

from __future__ import annotations

import zlib
from typing import Any, Optional

_zstd_module: Optional[Any] = None
_zstd_import_attempted = False


def zstd_available() -> bool:
    """True when the zstandard package is installed."""
    _ensure_zstd()
    return _zstd_module is not None


def _ensure_zstd() -> Optional[Any]:
    global _zstd_module, _zstd_import_attempted
    if _zstd_import_attempted:
        return _zstd_module
    _zstd_import_attempted = True
    try:
        import zstandard as zstd

        _zstd_module = zstd
    except ImportError:
        _zstd_module = None
    return _zstd_module


def zstd_compress(data: bytes, level: int = 3) -> bytes:
    """Compress with zstd; fall back to zlib if zstandard is unavailable."""
    zstd = _ensure_zstd()
    if zstd is not None:
        cctx = zstd.ZstdCompressor(level=level)
        return cctx.compress(data)
    return zlib.compress(data, level=6)


def zstd_decompress(data: bytes) -> bytes:
    """Decompress zstd data."""
    zstd = _ensure_zstd()
    if zstd is None:
        raise ValueError(
            "zstandard package required to decompress VSQZ streams. "
            "Install it with: pip install zstandard"
        )
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)
