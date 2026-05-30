"""GraphQL object types."""

from typing import Optional

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class DatabaseInfo:
    id: strawberry.ID
    video_path: str
    video_size_bytes: int = 0
    payload_frame_count: int = 0


@strawberry.type
class SqlResultType:
    columns: Optional[list[str]]
    values_json: str
    rowcount: int


@strawberry.type
class TableSchemaColumn:
    cid: int
    name: str
    type: str
    notnull: int
    default_value: Optional[JSON] = None
    pk: int
    unique: bool = False


@strawberry.type
class TableRowsResult:
    columns: list[str]
    values_json: str
    total_row_count: int = 0
    total_column_count: int = 0


@strawberry.type
class CsvImportResult:
    table: str
    imported_rows: int


@strawberry.type
class CsvColumnAnalysis:
    index: int
    source_name: str
    suggested_name: str
    inferred_type: str
    confidence: float
    empty_count: int
    unique_count: int
    is_unique_candidate: bool
    sample_values: list[str]


@strawberry.type
class ResolutionRecommendation:
    width: int
    height: int
    label: str
    estimated_frames: int
    estimated_payload_bytes: int
    is_current: bool
    is_recommended: bool
    reason: str


@strawberry.type
class CsvAnalysisResult:
    headers: list[str]
    row_count: int
    sample_row_count: int
    columns: list[CsvColumnAnalysis]
    warnings: list[str]
    resolutions: list[ResolutionRecommendation]


@strawberry.type
class EncodeResult:
    video_path: str
    video_url: str
    message: str


@strawberry.type
class FrameMeta:
    payload_frame_count: int
    logical_total_frames: int
    video_size_bytes: int = 0


@strawberry.type
class FramePreview:
    frame_index: int
    mime_type: str
    base64_png: str
    data_url: str


@strawberry.type
class AuthResult:
    ok: bool
    token: Optional[str] = None
    message: Optional[str] = None


@strawberry.type
class FeedbackEntry:
    session_id: str
    message: str
    rating: Optional[int]
    created_at: str


@strawberry.type
class MutationResult:
    ok: bool
    message: Optional[str] = None


@strawberry.type
class VideoIntegrityResult:
    overall_valid: bool
    checks: JSON
    statistics: JSON
    recommendations: list[str]


@strawberry.type
class VideoExportResult:
    exported_rows: int
    total_rows: int
    output_path: str


@strawberry.type
class VideoQueryResult:
    columns: list[str]
    rows: list[list[JSON]]
    row_count: int
    data: JSON


@strawberry.type
class PerformanceEvent:
    """One structured performance / ops timing event (in-process ring buffer)."""

    id: strawberry.ID
    ts: str
    db_id: Optional[strawberry.ID]
    table_name: Optional[str]
    operation: str
    duration_ms: float
    bytes_in: int
    bytes_out: int
    rows: Optional[int]
    meta: JSON


@strawberry.type
class PerformanceLogStats:
    """In-process perf persist queue snapshot (batched writes to VideoDB)."""

    pending_count: int
    last_flush_epoch: Optional[float] = None
    last_error: Optional[str] = None


@strawberry.type
class StorageMetrics:
    """Comparative storage statistics for a VSQL database/table."""

    mkv_bytes: int
    parquet_index_bytes: int
    row_count: int
    frame_count: int
    compression_ratio: float
    codec: str
    compression_algorithm: str
    estimated_csv_bytes: int
    estimated_parquet_bytes: int
    parquet_vs_mkv_ratio: float
    encode_time_ms: float
    parquet_index_exists: bool


@strawberry.type
class FormatExportResult:
    """Result of exporting a VSQL table to an external format."""

    format: str
    download_url: str
    file_size_bytes: int
    row_count: int
    elapsed_ms: float
