"""Encode/decode RGBA frame sequences with FFmpeg (lossless-ish MP4)."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import numpy as np

from .format_constants import FRAME_HEIGHT, FRAME_WIDTH


def _ffmpeg_executable() -> str | None:
    """Return path to ffmpeg binary (system PATH or imageio-ffmpeg bundle)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore[import-untyped]

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        return bundled if bundled else None
    except Exception:
        return None


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system or via imageio-ffmpeg."""
    return _ffmpeg_executable() is not None


def require_ffmpeg() -> None:
    """Raise an informative error if ffmpeg is not available."""
    from ..video_storage.exceptions import VideoEncodingError

    if not check_ffmpeg_available():
        raise VideoEncodingError(
            "ffmpeg is not installed or not in PATH. "
            "Please install ffmpeg to use video encoding/decoding features, "
            "or install the imageio-ffmpeg package for a bundled binary. "
            "Visit https://ffmpeg.org/download.html for installation instructions."
        )


def encode_rgba_frames_to_mp4(
    frames: List[np.ndarray],
    output_path: Path,
    fps: int = 30,
) -> None:
    """Pipe raw RGBA frames to FFmpeg (FFV1/Matroska) with atomic replace."""
    from ..video_storage.exceptions import VideoEncodingError

    require_ffmpeg()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ff = _ffmpeg_executable() or "ffmpeg"

    tmp_out = output_path.with_name(output_path.name + ".writing.tmp")
    tmp_out.unlink(missing_ok=True)

    try:
        if not frames:
            raise VideoEncodingError("No frames provided for video encode")
        for i, fr in enumerate(frames):
            if fr.shape != (FRAME_HEIGHT, FRAME_WIDTH, 4):
                raise VideoEncodingError(f"Frame {i} has invalid shape {fr.shape}")
            if fr.dtype != np.uint8:
                raise VideoEncodingError(f"Frame {i} must be uint8, got {fr.dtype}")

        # Rawvideo avoids thousands of intermediate PNG file writes and reads.
        cmd = [
            ff,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s:v",
            f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-f",
            "matroska",
            str(tmp_out),
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            assert proc.stdin is not None
            # Batch all frames into a single contiguous byte buffer and write
            # in one call — avoids repeated Python→OS context switches per frame.
            all_bytes = b"".join(np.ascontiguousarray(f).tobytes() for f in frames)
            proc.stdin.write(all_bytes)
            proc.stdin.close()
            stderr = (
                proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            )
            return_code = proc.wait()
        except OSError as e:
            raise VideoEncodingError(f"Failed to run ffmpeg for encode: {e}") from e
        except BrokenPipeError as e:
            raise VideoEncodingError("ffmpeg encode pipe closed unexpectedly") from e

        if return_code != 0:
            raise VideoEncodingError(
                f"ffmpeg encode failed (exit {return_code}): {stderr.strip() or 'no stderr'}"
            )

        if not tmp_out.is_file():
            raise VideoEncodingError(
                "ffmpeg reported success but output file is missing"
            )

        os.replace(tmp_out, output_path)
    finally:
        tmp_out.unlink(missing_ok=True)


def decode_mp4_to_rgba_frames(
    mp4_path: Path,
    max_frames: int | None = None,
) -> List[np.ndarray]:
    """Decode video to raw RGBA frames via FFmpeg stdout."""
    from ..video_storage.exceptions import VideoDecodingError

    require_ffmpeg()
    mp4_path = Path(mp4_path)
    if not mp4_path.is_file():
        raise VideoDecodingError(f"Video file not found: {mp4_path}")
    ff = _ffmpeg_executable() or "ffmpeg"

    cmd = [
        ff,
        "-loglevel",
        "error",
        "-i",
        str(mp4_path),
    ]
    if max_frames is not None:
        cmd.extend(["-frames:v", str(max(0, int(max_frames)))])
    cmd.extend(["-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"])
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as e:
        raise VideoDecodingError(f"Failed to run ffmpeg for decode: {e}") from e
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "replace").strip()
        raise VideoDecodingError(
            f"ffmpeg decode failed (exit {e.returncode}): {err or 'no stderr'}"
        ) from e

    frame_size = FRAME_HEIGHT * FRAME_WIDTH * 4
    if len(completed.stdout) % frame_size != 0:
        raise VideoDecodingError(
            f"Decoded byte stream length {len(completed.stdout)} is not a whole number of RGBA frames"
        )

    # Single vectorized allocation: one frombuffer + reshape for all frames,
    # then slice into per-frame views — no Python loop, no per-frame copy.
    raw_all = np.frombuffer(completed.stdout, dtype=np.uint8)
    n_frames = len(completed.stdout) // frame_size
    frames_array = raw_all[: n_frames * frame_size].reshape(
        n_frames, FRAME_HEIGHT, FRAME_WIDTH, 4
    )
    # Return writable copies so callers can safely modify frames.
    return [frames_array[i].copy() for i in range(n_frames)]
