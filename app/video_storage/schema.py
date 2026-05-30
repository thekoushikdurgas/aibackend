"""Video schema management for metadata storage in frame headers."""

import json
import struct
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .exceptions import SchemaError, FrameHeaderError


@dataclass
class ColumnDefinition:
    """Column definition stored in video metadata."""

    name: str
    data_type: str  # 'TEXT', 'INTEGER', 'REAL', 'BLOB'
    nullable: bool = True
    primary_key: bool = False
    default: Optional[Any] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class VideoSchema:
    """Schema information stored in video frame header."""

    version: int = 1
    columns: List[ColumnDefinition] = field(default_factory=list)
    row_count: int = 0
    compression_enabled: bool = True
    checksum_length: int = 32
    table_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.columns is None:
            self.columns = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary for JSON serialization."""
        return {
            "v": self.version,
            "cols": [
                {
                    "n": col.name,
                    "t": col.data_type,
                    "null": col.nullable,
                    "pk": col.primary_key,
                    "def": col.default,
                    "con": col.constraints or {},
                }
                for col in self.columns
            ],
            "rows": self.row_count,
            "comp": self.compression_enabled,
            "table": self.table_name,
            "created": self.created_at,
            "updated": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoSchema":
        """Create schema from dictionary."""
        # Handle both full and minimal schema formats
        if "cols" in data:
            columns = [
                ColumnDefinition(
                    name=col["n"],
                    data_type=col["t"],
                    nullable=col.get("null", True),
                    primary_key=col.get("pk", False),
                    default=col.get("def"),
                    constraints=col.get("con") or {},
                )
                for col in data["cols"]
            ]
            version = data.get("v", 1)
            row_count = data.get("rows", 0)
            compression = data.get("comp", True)
            table_name = data.get("table")
            created_at = data.get("created")
            updated_at = data.get("updated")
        else:
            # Full format
            columns = [ColumnDefinition(**col) for col in data.get("columns", [])]
            version = data.get("version", 1)
            row_count = data.get("row_count", 0)
            compression = data.get("compression_enabled", True)
            table_name = data.get("table_name")
            created_at = data.get("created_at")
            updated_at = data.get("updated_at")

        return cls(
            version=version,
            columns=columns,
            row_count=row_count,
            compression_enabled=compression,
            table_name=table_name,
            created_at=created_at,
            updated_at=updated_at,
        )

    def add_column(self, name: str, data_type: str, **kwargs) -> None:
        """Add a new column to the schema."""
        if any(col.name == name for col in self.columns):
            raise SchemaError(f"Column '{name}' already exists")

        column = ColumnDefinition(name=name, data_type=data_type, **kwargs)
        self.columns.append(column)
        self.updated_at = self._get_timestamp()

    def remove_column(self, name: str) -> None:
        """Remove a column from the schema."""
        self.columns = [col for col in self.columns if col.name != name]
        self.updated_at = self._get_timestamp()

    def get_column(self, name: str) -> Optional[ColumnDefinition]:
        """Get column definition by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_column_names(self) -> List[str]:
        """Get all column names."""
        return [col.name for col in self.columns]

    def infer_from_csv_header(self, header_row: List[str]) -> None:
        """Infer basic schema from CSV header row."""
        self.columns = []
        for col_name in header_row:
            # Default to TEXT type, can be refined later
            self.add_column(col_name, "TEXT")

    def infer_types_from_sample(self, sample_rows: List[List[str]]) -> None:
        """Refine column types based on sample data."""
        if not self.columns or not sample_rows:
            return

        for i, column in enumerate(self.columns):
            if i >= len(sample_rows[0]):
                continue

            # Sample values for this column
            values = [row[i] for row in sample_rows if i < len(row)]

            # Infer type from sample values
            inferred_type = self._infer_type_from_values(values)
            column.data_type = inferred_type

        self.updated_at = self._get_timestamp()

    def _infer_type_from_values(self, values: List[str]) -> str:
        """Infer data type from sample values."""
        if not values:
            return "TEXT"

        nonempty = [v for v in values if v is not None and str(v).strip() != ""]
        if not nonempty:
            # Avoid ``all(()) is True`` on all-blank columns (would wrongly infer INTEGER).
            return "TEXT"

        # Check for INTEGER
        if all(self._is_integer(v) for v in nonempty):
            return "INTEGER"

        # Check for REAL (float)
        if all(self._is_real(v) for v in nonempty):
            return "REAL"

        # Default to TEXT
        return "TEXT"

    def _is_integer(self, value: str) -> bool:
        """Check if string represents an integer."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_real(self, value: str) -> bool:
        """Check if string represents a real number."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class FrameHeader:
    """Frame header structure for video metadata storage."""

    # Embedded JSON schema in header[32:32+len] (legacy, small schemas only).
    MAGIC_EMBEDDED = b"VDB\x00"
    # Full schema JSON stored in the payload after this header (length-prefixed).
    MAGIC_EXTERNAL_SCHEMA = b"VDB\x01"
    HEADER_SIZE = 256  # Fixed header size in first frame RGB block

    # Max UTF-8 JSON bytes that fit in header after offset 32.
    MAX_EMBEDDED_SCHEMA_JSON = HEADER_SIZE - 32

    def __init__(self, schema: VideoSchema):
        self.schema = schema
        self.checksum = b""
        # When True, full schema JSON is in the frame payload prefix (see encoder).
        self.is_external_schema: bool = False
        # Byte length of full schema JSON in payload (set when is_external_schema).
        self.external_schema_json_length: int = 0

    def to_bytes(self) -> bytes:
        """Convert header to bytes for frame storage."""
        if self.is_external_schema:
            return self._to_bytes_external_schema(self.external_schema_json_length)

        schema_json = json.dumps(self.schema.to_dict()).encode("utf-8")

        if len(schema_json) > self.MAX_EMBEDDED_SCHEMA_JSON:
            return self._to_bytes_external_schema(len(schema_json))
        return self._to_bytes_embedded_schema(schema_json)

    def _to_bytes_embedded_schema(self, schema_json: bytes) -> bytes:
        header = bytearray(self.HEADER_SIZE)

        header[0:4] = self.MAGIC_EMBEDDED

        struct.pack_into(">I", header, 4, self.schema.version)
        struct.pack_into(">I", header, 8, len(schema_json))
        struct.pack_into(">I", header, 12, self.schema.row_count)
        struct.pack_into(">I", header, 16, len(self.schema.columns))
        struct.pack_into(">I", header, 20, 1 if self.schema.compression_enabled else 0)
        struct.pack_into(">I", header, 24, self.schema.checksum_length)
        header[32 : 32 + len(schema_json)] = schema_json

        return bytes(header)

    def _to_bytes_external_schema(self, full_schema_json_len: int) -> bytes:
        """Header for large schemas: metadata only; full JSON follows in payload."""
        header = bytearray(self.HEADER_SIZE)
        header[0:4] = self.MAGIC_EXTERNAL_SCHEMA
        struct.pack_into(">I", header, 4, self.schema.version)
        struct.pack_into(">I", header, 8, full_schema_json_len)
        struct.pack_into(">I", header, 12, self.schema.row_count)
        struct.pack_into(">I", header, 16, len(self.schema.columns))
        struct.pack_into(">I", header, 20, 1 if self.schema.compression_enabled else 0)
        struct.pack_into(">I", header, 24, self.schema.checksum_length)
        return bytes(header)

    @classmethod
    def from_bytes(cls, data: bytes) -> "FrameHeader":
        """Parse header from frame bytes."""
        if len(data) < cls.HEADER_SIZE:
            raise FrameHeaderError("Header data too short")

        magic = data[0:4]
        if magic == cls.MAGIC_EXTERNAL_SCHEMA:
            return cls._from_bytes_external(data)
        if magic == cls.MAGIC_EMBEDDED:
            return cls._from_bytes_embedded(data)
        raise FrameHeaderError(f"Invalid magic bytes: {magic!r}")

    @classmethod
    def _from_bytes_embedded(cls, data: bytes) -> "FrameHeader":
        schema_length = struct.unpack_from(">I", data, 8)[0]
        if schema_length == 0 or schema_length > cls.MAX_EMBEDDED_SCHEMA_JSON:
            raise FrameHeaderError(f"Invalid schema length: {schema_length}")

        schema_json = data[32 : 32 + schema_length].decode("utf-8")

        try:
            schema_dict = json.loads(schema_json)
            schema = VideoSchema.from_dict(schema_dict)
        except (json.JSONDecodeError, KeyError) as e:
            raise FrameHeaderError(f"Invalid schema JSON: {e}") from e

        return cls(schema)

    @classmethod
    def _from_bytes_external(cls, data: bytes) -> "FrameHeader":
        external_len = struct.unpack_from(">I", data, 8)[0]
        if external_len < 2 or external_len > 16 * 1024 * 1024:
            raise FrameHeaderError(f"Invalid external schema length: {external_len}")

        row_count = struct.unpack_from(">I", data, 12)[0]
        ncol = struct.unpack_from(">I", data, 16)[0]
        comp = struct.unpack_from(">I", data, 20)[0]
        checksum_length = struct.unpack_from(">I", data, 24)[0]
        version = struct.unpack_from(">I", data, 4)[0]

        placeholder = VideoSchema(
            version=version,
            columns=[],
            row_count=row_count,
            compression_enabled=bool(comp),
            checksum_length=checksum_length,
        )
        header = cls(placeholder)
        header.is_external_schema = True
        header.external_schema_json_length = external_len
        if ncol > 0:
            header.schema.columns = [
                ColumnDefinition(name=f"col_{i}", data_type="TEXT") for i in range(ncol)
            ]
        return header

    def validate(self) -> bool:
        """Validate header integrity."""
        try:
            if self.is_external_schema:
                b = self._to_bytes_external_schema(self.external_schema_json_length)
                return (
                    len(b) == self.HEADER_SIZE and self.external_schema_json_length >= 2
                )
            b = self.to_bytes()
            return (
                len(b) == self.HEADER_SIZE
                and self.schema.version > 0
                and len(self.schema.columns) > 0
            )
        except Exception:
            return False
