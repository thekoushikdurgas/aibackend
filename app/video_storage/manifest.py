"""Sidecar manifest JSON next to each video file for integrity metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

MANIFEST_VERSION = 1
MANIFEST_SUFFIX = ".vsql-manifest.json"


def sidecar_manifest_path(video_path: Path | str) -> Path:
    """Path to the manifest file accompanying ``video_path`` (same directory)."""
    p = Path(video_path)
    return p.parent / f"{p.stem}{MANIFEST_SUFFIX}"


def write_manifest(
    video_path: Path | str,
    *,
    frame_count: int,
    fps: int,
    payload_sha256: str,
    video_size_bytes: int,
    codec: str = "ffv1",
    container: str = "matroska",
) -> None:
    """Write atomic metadata describing the encoded video and logical payload."""
    vp = Path(video_path)
    data = {
        "version": MANIFEST_VERSION,
        "video_file": vp.name,
        "frame_count": frame_count,
        "fps": fps,
        "codec": codec,
        "container": container,
        "video_size_bytes": video_size_bytes,
        "payload_sha256": payload_sha256,
    }
    path = sidecar_manifest_path(vp)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_manifest(video_path: Path | str) -> Optional[dict[str, Any]]:
    """Load manifest if present; return ``None`` if missing or unreadable."""
    path = sidecar_manifest_path(video_path)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def remove_manifest(video_path: Path | str) -> None:
    """Remove sidecar manifest if it exists (e.g. before overwrite)."""
    path = sidecar_manifest_path(video_path)
    path.unlink(missing_ok=True)
