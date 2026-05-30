"""Video frame to data decoder."""

import json
import struct
import zlib
from typing import Iterator, List, Optional, Union, Any
from pathlib import Path
import numpy as np

from .schema import FrameHeader, VideoSchema
from .exceptions import VideoDecodingError, FrameHeaderError
from ..codec.format_constants import FRAME_WIDTH, FRAME_HEIGHT

# zstd magic bytes (first 4 bytes of a zstd frame)
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def _decompress(data: bytes) -> bytes:
    """Decompress *data*, auto-detecting zstd vs zlib by inspecting magic bytes."""
    if data[:4] == _ZSTD_MAGIC:
        try:
            import zstandard as zstd  # type: ignore[import-untyped]

            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(data)
        except ImportError:
            raise VideoDecodingError(
                "zstandard package required to decompress zstd-encoded data. "
                "Install it with: pip install zstandard"
            )
    # Fall back to zlib (legacy VSQC streams).
    try:
        return zlib.decompress(data)
    except zlib.error as e:
        raise VideoDecodingError(f"Decompression failed: {e}") from e


class DataDecoder:
    """Decode RGBA video frames back to original data."""

    def __init__(self, width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT):
        self.width = width
        self.height = height
        self.pixels_per_frame = width * height
        self.frame_capacity = self.pixels_per_frame * 3  # RGB only (A=255)

    def decode_frames_to_csv(
        self, frames: List[np.ndarray], output_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Decode frames to CSV format."""
        # Extract header from first frame
        header = self._extract_header_from_frame(frames[0])

        # Extract data bytes from frames
        data_bytes = self._extract_data_from_frames(frames, header)
        schema, data_bytes = self._split_external_schema_prefix(data_bytes, header)

        # Decompress if needed (auto-detects zstd vs zlib via magic bytes)
        if schema.compression_enabled:
            data_bytes = _decompress(data_bytes)

        # Convert to CSV string
        csv_content = data_bytes.decode("utf-8")

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(csv_content, encoding="utf-8")

        return csv_content

    def decode_frames_to_json(
        self, frames: List[np.ndarray], output_path: Optional[Union[str, Path]] = None
    ) -> Union[List[dict], dict]:
        """Decode frames to JSON format."""
        # First decode to CSV
        csv_content = self.decode_frames_to_csv(frames)

        # Parse CSV to get data
        lines = csv_content.strip().split("\n")
        if not lines:
            return []

        headers = lines[0].split(",")
        data = []

        # Extract full schema (embedded or external prefix)
        header = self._extract_header_from_frame(frames[0])
        raw_payload = self._extract_data_from_frames(frames, header)
        schema, _ = self._split_external_schema_prefix(raw_payload, header)

        # Create column type mapping
        col_types = {}
        if schema and schema.columns:
            for col in schema.columns:
                col_types[col.name] = col.data_type

        for line in lines[1:]:
            values = line.split(",")
            row = {}
            for i, header_name in enumerate(headers):
                if i < len(values):
                    value_str = values[i]
                    # Convert string back to original type based on schema
                    converted_value = self._convert_string_to_type(
                        value_str, col_types.get(header_name, "TEXT")
                    )
                    row[header_name] = converted_value
                else:
                    row[header_name] = None
            data.append(row)

        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return data

    def _convert_string_to_type(self, value_str: str, data_type: str) -> Any:
        """Convert string value back to its original data type based on schema."""
        if value_str in ("", "None", "null"):
            return None

        try:
            if data_type == "INTEGER":
                return int(float(value_str))
            elif data_type == "REAL":
                return float(value_str)
            elif data_type == "TEXT":
                return value_str
            elif data_type == "BLOB":
                return value_str.encode("utf-8")
            else:
                # Default to string for unknown types
                return value_str
        except (ValueError, TypeError):
            # If conversion fails, return original string
            return value_str

    def decode_frames_to_bytes(self, frames: List[np.ndarray]) -> bytes:
        """Decode frames to raw bytes."""
        # Extract header from first frame
        header = self._extract_header_from_frame(frames[0])

        # Extract data bytes from frames
        data_bytes = self._extract_data_from_frames(frames, header)
        schema, data_bytes = self._split_external_schema_prefix(data_bytes, header)

        # Decompress if needed (auto-detects zstd vs zlib via magic bytes)
        if schema.compression_enabled:
            data_bytes = _decompress(data_bytes)

        return data_bytes

    def decode_frames_to_dataframe(self, frames: List[np.ndarray]):
        """Decode frames to pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise VideoDecodingError("pandas not available for DataFrame conversion")

        # Decode to CSV first
        csv_content = self.decode_frames_to_csv(frames)

        # Use pandas to parse CSV with proper type inference
        from io import StringIO

        return pd.read_csv(StringIO(csv_content))

    def get_schema_from_frames(self, frames: List[np.ndarray]) -> VideoSchema:
        """Extract schema from frame header."""
        if not frames:
            raise VideoDecodingError("No frames provided")

        header = self._extract_header_from_frame(frames[0])
        if header.is_external_schema:
            raw = self._extract_data_from_frames(frames, header)
            schema, _ = self._split_external_schema_prefix(raw, header)
            return schema
        return header.schema

    def stream_decode_frames(self, frames: Iterator[np.ndarray]) -> Iterator[bytes]:
        """Stream decode frames for large datasets."""
        frame_iter = iter(frames)

        try:
            # Get first frame for header
            first_frame = next(frame_iter)
            header = self._extract_header_from_frame(first_frame)

            # Extract data from first frame
            first_frame_data = self._extract_frame_data(first_frame, header)
            yield first_frame_data

            # Process remaining frames
            for frame in frame_iter:
                frame_data = self._extract_frame_data(frame, header)
                yield frame_data

        except StopIteration:
            raise VideoDecodingError("No frames to decode")

    def _extract_header_from_frame(self, frame: np.ndarray) -> FrameHeader:
        """Extract header from first frame."""
        if frame.shape != (self.height, self.width, 4):
            raise VideoDecodingError(f"Invalid frame shape: {frame.shape}")

        # Convert frame to bytes
        frame_bytes = self._rgba_frame_to_bytes(frame)

        # Extract header bytes
        header_bytes = frame_bytes[: FrameHeader.HEADER_SIZE]

        try:
            header = FrameHeader.from_bytes(header_bytes)
            return header
        except Exception as e:
            raise FrameHeaderError(f"Failed to parse header: {e}")

    def _extract_data_from_frames(
        self, frames: List[np.ndarray], header: FrameHeader
    ) -> bytes:
        """Extract and concatenate data bytes from all frames."""
        data_parts = []

        for i, frame in enumerate(frames):
            frame_data = self._extract_frame_data(
                frame, header, is_first_frame=(i == 0)
            )
            if frame_data:
                data_parts.append(frame_data)

        return b"".join(data_parts)

    def _extract_frame_data(
        self, frame: np.ndarray, header: FrameHeader, is_first_frame: bool = False
    ) -> bytes:
        """Extract data bytes from a single frame."""
        frame_bytes = self._rgba_frame_to_bytes(frame)

        if is_first_frame:
            # First frame: skip header
            header_size = FrameHeader.HEADER_SIZE
            return frame_bytes[header_size:]
        else:
            # Data frame: all bytes are data
            return frame_bytes

    def _rgba_frame_to_bytes(self, frame: np.ndarray) -> bytes:
        """Convert RGBA frame to bytes."""
        if frame.shape != (self.height, self.width, 4):
            raise VideoDecodingError(f"Invalid frame shape: {frame.shape}")

        # Extract RGB channels (ignore alpha)
        rgb_frame = frame[:, :, :3]

        # Flatten to bytes
        return rgb_frame.tobytes()

    def _split_external_schema_prefix(
        self, data_bytes: bytes, header: FrameHeader
    ) -> tuple[VideoSchema, bytes]:
        """If header uses external schema, strip length-prefixed JSON and return full schema."""
        if not header.is_external_schema:
            return header.schema, data_bytes

        elen = header.external_schema_json_length
        if len(data_bytes) < 4 + elen:
            raise VideoDecodingError("Payload too short for external schema")
        prefix_len = struct.unpack_from(">I", data_bytes, 0)[0]
        if prefix_len != elen:
            raise VideoDecodingError(
                f"External schema length mismatch: got {prefix_len}, expected {elen}"
            )
        blob = data_bytes[4 : 4 + elen]
        rest = data_bytes[4 + elen :]
        try:
            merged = VideoSchema.from_dict(json.loads(blob.decode("utf-8")))
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            raise VideoDecodingError(f"Invalid external schema JSON: {e}") from e
        return merged, rest

    def validate_frames(self, frames: List[np.ndarray]) -> bool:
        """Validate frame integrity."""
        try:
            if not frames:
                return False

            # Check first frame header
            header = self._extract_header_from_frame(frames[0])

            # Validate header
            if not header.validate():
                return False

            # Check frame count matches expected
            expected_frames = self._calculate_expected_frame_count(header)
            if len(frames) < expected_frames:
                return False

            # Validate each frame shape
            for i, frame in enumerate(frames):
                if frame.shape != (self.height, self.width, 4):
                    return False

            return True

        except Exception:
            return False

    def _calculate_expected_frame_count(self, header: FrameHeader) -> int:
        """Calculate expected number of frames from header."""
        # This is a simplified calculation - in practice, you'd need
        # to know the actual data size or have it stored in the header
        # For now, assume we have all frames that were provided
        return 1  # Minimum one frame for header

    def decode_partial_frames(
        self,
        frames: List[np.ndarray],
        start_row: int = 0,
        max_rows: Optional[int] = None,
    ) -> str:
        """Decode specific row range from frames."""
        # Get full CSV content
        csv_content = self.decode_frames_to_csv(frames)

        # Split into lines
        lines = csv_content.strip().split("\n")
        if not lines:
            return ""

        # Header is always included
        header_line = lines[0]
        data_lines = lines[1:]

        # Calculate slice
        end_row = None if max_rows is None else start_row + max_rows

        # Slice data lines
        selected_lines = data_lines[start_row:end_row]

        # Reconstruct CSV
        if selected_lines:
            return "\n".join([header_line] + selected_lines)
        else:
            return header_line  # Return only header if no data selected

    def count_rows_in_frames(self, frames: List[np.ndarray]) -> int:
        """Count total rows in frames without full decode."""
        try:
            schema = self.get_schema_from_frames(frames)
            return schema.row_count
        except Exception:
            return 0
