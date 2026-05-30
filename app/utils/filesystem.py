"""Filesystem helpers with explicit error handling (no ignore_errors)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def safe_rmtree(path: PathLike) -> None:
    """Remove a directory tree when it exists; log OSError instead of swallowing."""
    p = Path(path)
    if not p.is_dir():
        return
    try:
        shutil.rmtree(p)
    except OSError as exc:
        logger.warning("Failed to remove directory %s: %s", p, exc)
