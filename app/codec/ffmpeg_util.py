"""FFmpeg executable resolution (system PATH or imageio-ffmpeg bundle)."""

from __future__ import annotations

import shutil
from typing import Optional


def ffmpeg_executable() -> Optional[str]:
    """Return path to ffmpeg binary, or None if unavailable."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        return bundled if bundled else None
    except Exception:
        return None
