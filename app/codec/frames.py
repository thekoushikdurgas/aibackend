"""Map vSQL byte stream to RGBA uint8 frames and back."""

import struct
from typing import List

import numpy as np

from .format_constants import (
    FRAME_CAPACITY,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    HEADER_SIZE,
    MAGIC_VSQL_COMPRESSED,
    MAGIC_VSQL_RAW,
    MAGIC_VSQL_ZSTD,
    PIXELS_PER_FRAME,
    payload_frame_count_for_stream_length,
)


def stream_to_frames(
    stream: bytes, logical_total_frames: int | None = None
) -> List[np.ndarray]:
    """
    Convert byte stream (header + payload) to list of RGBA uint8 arrays (H, W, 4).
    If logical_total_frames is set, append black tail frames (alpha=255).
    """
    if not stream:
        raise ValueError("Empty stream")

    payload_fc = payload_frame_count_for_stream_length(len(stream))
    frames: List[np.ndarray] = []
    offset = 0

    for _ in range(payload_fc):
        take = min(FRAME_CAPACITY, len(stream) - offset)
        if take <= 0:
            break
        buf = bytearray(FRAME_CAPACITY)
        buf[:take] = stream[offset : offset + take]
        offset += take
        frames.append(_buf_to_rgba(np.frombuffer(bytes(buf), dtype=np.uint8)))

    if offset != len(stream):
        raise RuntimeError("Stream framing bug: not all bytes consumed")

    if logical_total_frames is not None:
        if logical_total_frames < len(frames):
            raise ValueError(
                f"logical_total_frames {logical_total_frames} < payload frames {len(frames)}"
            )
        tail = logical_total_frames - len(frames)
        black = _black_rgba()
        for _ in range(tail):
            frames.append(black.copy())

    return frames


def _black_rgba() -> np.ndarray:
    a = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 4), dtype=np.uint8)
    a[:, :, 3] = 255
    return a


def _buf_to_rgba(flat: np.ndarray) -> np.ndarray:
    """flat: length FRAME_CAPACITY uint8 -> (H,W,4) RGBA, A=255."""
    if flat.size != FRAME_CAPACITY:
        raise ValueError(f"Expected {FRAME_CAPACITY} bytes, got {flat.size}")
    rgb = flat.reshape(PIXELS_PER_FRAME, 3)
    rgba = np.empty((PIXELS_PER_FRAME, 4), dtype=np.uint8)
    rgba[:, :3] = rgb
    rgba[:, 3] = 255
    return rgba.reshape(FRAME_HEIGHT, FRAME_WIDTH, 4)


def rgba_to_buf(rgba: np.ndarray) -> bytes:
    """(H,W,4) -> FRAME_CAPACITY bytes from RGB channels only."""
    if rgba.shape != (FRAME_HEIGHT, FRAME_WIDTH, 4):
        raise ValueError(f"Bad frame shape {rgba.shape}")
    p = rgba.reshape(PIXELS_PER_FRAME, 4)
    rgb = p[:, :3].reshape(-1)
    if rgb.size != FRAME_CAPACITY:
        raise ValueError("RGB size mismatch")
    return rgb.tobytes()


def frames_to_stream(frames: List[np.ndarray]) -> bytes:
    """Reassemble full vSQL byte stream from consecutive payload frames (no tail padding)."""
    if not frames:
        raise ValueError("No frames")

    parts: List[bytes] = []
    total_needed: int | None = None
    collected = 0

    for fr in frames:
        raw = rgba_to_buf(fr)
        if total_needed is None:
            if len(raw) < HEADER_SIZE:
                raise ValueError("Frame 0 too small")
            magic = raw[0:4]
            if magic not in (
                MAGIC_VSQL_COMPRESSED,
                MAGIC_VSQL_RAW,
                MAGIC_VSQL_ZSTD,
            ):
                raise ValueError("Invalid vSQL magic in frame 0")
            compressed_length = struct.unpack_from(">I", raw, 8)[0]
            total_needed = HEADER_SIZE + compressed_length
        assert total_needed is not None
        remain = total_needed - collected
        take = min(remain, len(raw))
        parts.append(raw[:take])
        collected += take
        if collected >= total_needed:
            break

    if total_needed is None or collected != total_needed:
        raise ValueError("Truncated frames for vSQL stream")

    return b"".join(parts)


def frames_pad_to_count(
    frames: List[np.ndarray], logical_total: int
) -> List[np.ndarray]:
    """Ensure list length == logical_total by appending black frames."""
    if len(frames) > logical_total:
        raise ValueError("Too many frames for logical_total")
    if len(frames) == logical_total:
        return frames
    black = _black_rgba()
    out = list(frames)
    while len(out) < logical_total:
        out.append(black.copy())
    return out


def split_payload_and_tail(all_frames: List[np.ndarray]) -> List[np.ndarray]:
    """
    Given frames including black tail, return only payload frames needed for stream.
    """
    if not all_frames:
        return []
    raw0 = rgba_to_buf(all_frames[0])
    if len(raw0) < HEADER_SIZE:
        raise ValueError("Invalid frame 0")
    magic = raw0[0:4]
    if magic not in (MAGIC_VSQL_COMPRESSED, MAGIC_VSQL_RAW, MAGIC_VSQL_ZSTD):
        raise ValueError("Invalid magic")
    comp_len = struct.unpack_from(">I", raw0, 8)[0]
    total_len = HEADER_SIZE + comp_len
    pfc = payload_frame_count_for_stream_length(total_len)
    return all_frames[:pfc]
