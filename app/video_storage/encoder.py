"""Direct data to video frame encoder."""

import csv
import json
import struct
import zlib
from typing import Iterator, List, Optional, Union, BinaryIO
from pathlib import Path
import numpy as np

from .schema import VideoSchema, FrameHeader
from .exceptions import VideoEncodingError
from ..codec.compression import zstd_compress
from ..codec.format_constants import FRAME_WIDTH, FRAME_HEIGHT


def _compress(data: bytes, algorithm: str = "zstd", level: int = 3) -> bytes:
    """Compress *data* using the requested algorithm.

    Supported algorithms:
      - "zstd"  — zstandard (default; 3-5x faster than zlib at similar ratios)
      - "zlib"  — legacy deflate

    *level* is the codec level (zstd: 1–22, zlib: 1–9).
    """
    algo = (algorithm or "zstd").lower()
    if algo == "zlib":
        return zlib.compress(data, level=max(1, min(int(level), 9)))
    if algo == "zstd":
        lv = max(1, min(int(level), 22))
        return zstd_compress(data, level=lv)
    return zlib.compress(data, level=9)


class DataEncoder:
    """Encode data directly to RGBA video frames."""

    def __init__(self, width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT):
        self.width = width
        self.height = height
        self.pixels_per_frame = width * height
        self.frame_capacity = self.pixels_per_frame * 3  # RGB only (A=255)

    def encode_csv_to_frames(
        self,
        csv_path: Union[str, Path],
        schema: Optional[VideoSchema] = None,
        compression: bool = True,
        compression_algorithm: str = "zstd",
        compression_level: int = 3,
    ) -> tuple[List[np.ndarray], VideoSchema]:
        """Encode CSV file to RGBA frames."""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise VideoEncodingError(f"CSV file not found: {csv_path}")

        # Read CSV and infer schema if not provided
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = [row for row in reader if row]  # Filter out empty rows

        if not rows:
            raise VideoEncodingError("CSV file is empty")

        # Create schema if not provided
        if schema is None:
            schema = VideoSchema()
            header_row = rows[0]
            schema.infer_from_csv_header(header_row)

            # Infer types from sample data
            sample_rows = rows[1:101]  # Sample first 100 rows
            if sample_rows:
                schema.infer_types_from_sample(sample_rows)

        # Convert CSV to bytes
        csv_bytes = self._csv_to_bytes(rows, schema)

        # Compress if enabled
        if compression:
            csv_bytes = _compress(
                csv_bytes,
                algorithm=compression_algorithm,
                level=compression_level,
            )
            schema.compression_enabled = True
        else:
            schema.compression_enabled = False

        # Update schema with row count (excluding header)
        schema.row_count = len(rows) - 1  # Exclude header

        # Encode to frames
        frames = self._encode_bytes_to_frames(csv_bytes, schema)

        return frames, schema

    def encode_json_to_frames(
        self,
        json_data: Union[str, List[dict], dict],
        schema: Optional[VideoSchema] = None,
        compression: bool = True,
        compression_algorithm: str = "zstd",
        compression_level: int = 3,
    ) -> tuple[List[np.ndarray], VideoSchema]:
        """Encode JSON data to RGBA frames."""
        if isinstance(json_data, str):
            # Load JSON from string
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise VideoEncodingError(f"Invalid JSON: {e}")

        # Convert to CSV-like format
        if isinstance(json_data, dict):
            json_data = [json_data]

        if not json_data:
            raise VideoEncodingError("JSON data is empty")

        # Extract headers from keys
        if isinstance(json_data, list) and len(json_data) > 0:
            headers = list(json_data[0].keys())
        else:
            raise VideoEncodingError("Invalid JSON data structure")

        # Create schema if not provided
        if schema is None:
            schema = VideoSchema()
            for header in headers:
                # Infer type from first non-null value
                sample_values = [str(row.get(header, "")) for row in json_data[:10]]
                data_type = self._infer_type_from_values(sample_values)
                schema.add_column(header, data_type)

        # Convert to rows
        rows = [headers] + [
            [str(row.get(col, "")) for col in headers] for row in json_data
        ]

        # Convert to bytes
        csv_bytes = self._csv_to_bytes(rows, schema)

        # Compress if enabled
        if compression:
            csv_bytes = _compress(
                csv_bytes,
                algorithm=compression_algorithm,
                level=compression_level,
            )
            schema.compression_enabled = True
        else:
            schema.compression_enabled = False

        # Update schema
        schema.row_count = len(json_data)

        # Encode to frames
        frames = self._encode_bytes_to_frames(csv_bytes, schema)

        return frames, schema

    def encode_bytes_to_frames(
        self,
        data: bytes,
        schema: VideoSchema,
        compression: bool = True,
        compression_algorithm: str = "zstd",
        compression_level: int = 3,
    ) -> List[np.ndarray]:
        """Encode raw bytes to RGBA frames."""
        if compression:
            data = _compress(
                data,
                algorithm=compression_algorithm,
                level=compression_level,
            )
            schema.compression_enabled = True
        else:
            schema.compression_enabled = False

        return self._encode_bytes_to_frames(data, schema)

    def _encode_bytes_to_frames(
        self, data: bytes, schema: VideoSchema
    ) -> List[np.ndarray]:
        """Encode bytes to RGBA frames with header."""
        frames = []

        schema_json_utf8 = json.dumps(schema.to_dict()).encode("utf-8")
        # Create header frame
        header = FrameHeader(schema)
        header_bytes = header.to_bytes()

        if len(schema_json_utf8) > FrameHeader.MAX_EMBEDDED_SCHEMA_JSON:
            payload_stream = (
                struct.pack(">I", len(schema_json_utf8)) + schema_json_utf8 + data
            )
        else:
            payload_stream = data

        # Calculate how much data fits in first frame
        first_frame_data_capacity = self.frame_capacity - len(header_bytes)

        # First frame: header + data
        first_frame_data = payload_stream[:first_frame_data_capacity]
        first_frame_bytes = header_bytes + first_frame_data

        # Convert to RGBA frame
        first_frame = self._bytes_to_rgba_frame(first_frame_bytes)
        frames.append(first_frame)

        # Remaining data frames
        remaining_data = payload_stream[first_frame_data_capacity:]

        for i in range(0, len(remaining_data), self.frame_capacity):
            chunk = remaining_data[i : i + self.frame_capacity]
            frame = self._bytes_to_rgba_frame(chunk)
            frames.append(frame)

        return frames

    def _bytes_to_rgba_frame(self, data: bytes) -> np.ndarray:
        """Convert bytes to RGBA frame."""
        # Pad data to frame capacity if needed
        if len(data) > self.frame_capacity:
            raise VideoEncodingError(
                f"Data too large for frame: {len(data)} > {self.frame_capacity}"
            )

        padded_data = data + b"\x00" * (self.frame_capacity - len(data))

        # Convert to RGB array
        rgb_array = np.frombuffer(padded_data, dtype=np.uint8).reshape(-1, 3)

        # Add alpha channel (255 for all pixels)
        rgba_array = np.zeros((self.pixels_per_frame, 4), dtype=np.uint8)
        rgba_array[:, :3] = rgb_array
        rgba_array[:, 3] = 255

        # Reshape to frame dimensions
        frame = rgba_array.reshape(self.height, self.width, 4)

        return frame

    def _csv_to_bytes(self, rows: List[List[str]], schema: VideoSchema) -> bytes:
        """Convert CSV rows to bytes."""
        output = []

        # Write header
        header = ",".join(schema.get_column_names())
        output.append(header)

        # Write data rows with type conversion
        for row in rows[1:]:  # Skip header
            converted_row = []
            for i, value in enumerate(row):
                if i < len(schema.columns):
                    col_def = schema.columns[i]
                    converted_value = self._convert_value(value, col_def.data_type)
                    converted_row.append(converted_value)
                else:
                    converted_row.append(str(value))

            output.append(",".join(converted_row))

        return "\n".join(output).encode("utf-8")

    def _convert_value(self, value: str, data_type: str) -> str:
        """Convert value according to data type."""
        if not value or value == "":
            return ""

        try:
            if data_type == "INTEGER":
                return str(int(float(value)))
            elif data_type == "REAL":
                return str(float(value))
            else:
                return str(value)
        except ValueError:
            return str(value)

    def _infer_type_from_values(self, values: List[str]) -> str:
        """Infer data type from sample values."""
        if not values:
            return "TEXT"

        non_empty_values = [v for v in values if v and v != ""]
        if not non_empty_values:
            return "TEXT"

        # Check for INTEGER
        if all(self._is_integer(v) for v in non_empty_values):
            return "INTEGER"

        # Check for REAL
        if all(self._is_real(v) for v in non_empty_values):
            return "REAL"

        return "TEXT"

    def _is_integer(self, value: str) -> bool:
        """Check if string represents an integer (no decimal point)."""
        try:
            # Check if the string representation has no decimal point
            # and can be converted to integer without losing precision
            if "." in value:
                return False
            int_value = int(value)
            # Convert back to string to ensure no precision loss
            return str(int_value) == value.strip()
        except ValueError:
            return False

    def _is_real(self, value: str) -> bool:
        """Check if string represents a real number."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def stream_encode_csv(
        self, csv_file: BinaryIO, schema: VideoSchema, chunk_size: int = 8192
    ) -> Iterator[np.ndarray]:
        """Stream encode CSV file for large files."""
        # For now, implement simple version - can be enhanced for true streaming
        csv_content = csv_file.read().decode("utf-8-sig")
        lines = csv_content.split("\n")

        rows = [line.split(",") for line in lines if line]

        if not rows:
            raise VideoEncodingError("Empty CSV file")

        # Use regular encoding for now
        frames, _ = self.encode_csv_to_frames_data(rows, schema)

        for frame in frames:
            yield frame

    def encode_csv_to_frames_data(
        self, rows: List[List[str]], schema: VideoSchema
    ) -> tuple[List[np.ndarray], VideoSchema]:
        """Encode CSV data (already parsed) to frames."""
        if not rows:
            raise VideoEncodingError("No data to encode")

        # Convert to bytes
        csv_bytes = self._csv_to_bytes(rows, schema)

        # Compress if enabled
        if schema.compression_enabled:
            csv_bytes = _compress(csv_bytes, algorithm="zstd", level=3)

        # Update row count
        schema.row_count = len(rows) - 1  # Exclude header

        # Encode to frames
        frames = self._encode_bytes_to_frames(csv_bytes, schema)

        return frames, schema
