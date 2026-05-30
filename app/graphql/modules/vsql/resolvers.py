"""GraphQL Query / Mutation resolvers (delegate to services)."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Optional, cast

import strawberry
from starlette.requests import Request
from strawberry.file_uploads import Upload
from strawberry.scalars import JSON
from strawberry.types import Info

from app.codec.format_constants import LOGICAL_TOTAL_FRAMES_DEFAULT
from app.graphql.modules.vsql.uploads import MAX_UPLOAD_BYTES, stream_upload_to_file
from app.graphql.modules.vsql.types import (
    AuthResult,
    CsvAnalysisResult,
    CsvColumnAnalysis,
    CsvImportResult,
    DatabaseInfo,
    EncodeResult,
    FeedbackEntry,
    FormatExportResult,
    FrameMeta,
    FramePreview,
    MutationResult,
    PerformanceEvent,
    PerformanceLogStats,
    ResolutionRecommendation,
    SqlResultType,
    StorageMetrics,
    TableRowsResult,
    TableSchemaColumn,
)
from app.services import feedback_service
from app.services import auth_vsql_service
from app.services import video_service
from app.services.perf_event_log import list_events
from app.services.perf_event_store import list_merged_events, perf_persist_stats
from app.storage import (
    arrow_export_path,
    database_dir,
    new_database_id,
    parquet_export_path,
    parquet_index_path,
    video_path,
)


def _normalize_csv_if_needed(
    src: Path,
    dest_dir: Path,
    delimiter: str,
    quote_char: str,
) -> Path:
    """Return a path to comma-separated UTF-8 CSV for VideoDB when dialect differs."""
    d = delimiter if delimiter else ","
    q = quote_char[0] if quote_char else '"'
    if d == "," and q == '"':
        return src
    dest = dest_dir / "temp_import_normalized.csv"
    with open(src, "r", encoding="utf-8-sig", newline="") as f_in:
        reader = csv.reader(f_in, delimiter=d, quotechar=q)
        with open(dest, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.writer(f_out, lineterminator="\n")
            for row in reader:
                writer.writerow(row)
    return dest


def _logical_table_name(db_id: str) -> str:
    """Match Query.tables: users when name/email/phone columns exist."""
    tables = video_service.list_video_tables(db_id)
    if tables:
        return tables[0]
    info = video_service.get_video_info(db_id)
    if info.get("error"):
        return "data"
    if info.get("table_name"):
        return str(info["table_name"])
    names = {c["name"] for c in info.get("columns", [])}
    if {"name", "email", "phone"} <= names:
        return "users"
    return "data"


def _require_db(db_id: str, table_name: Optional[str] = None) -> Path:
    info = video_service.get_video_info(db_id, table_name=table_name)
    p = Path(str(info.get("video_path", video_path(db_id))))
    if not p.exists():
        raise ValueError("Video database not found")
    return p


def _video_asset_url(
    request: Request, db_id: str, table_name: Optional[str] = None
) -> str:
    base = str(request.base_url).rstrip("/")
    if table_name:
        return f"{base}/databases/{db_id}/tables/{table_name}/download/video"
    return f"{base}/databases/{db_id}/download/video"


@strawberry.type
class Query:
    @strawberry.field
    def tables(self, db_id: strawberry.ID) -> list[str]:
        """Logical table names exposed for this database."""
        try:
            return video_service.list_video_tables(str(db_id))
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def database_info(
        self, db_id: strawberry.ID, table_name: Optional[str] = None
    ) -> DatabaseInfo:
        try:
            info = video_service.get_video_info(str(db_id), table_name=table_name)
            if info.get("error") == "Video database not found":
                return DatabaseInfo(
                    id=strawberry.ID(str(db_id)),
                    video_path="",
                    video_size_bytes=0,
                    payload_frame_count=0,
                )
            if info.get("error"):
                raise ValueError(info["error"])
            return DatabaseInfo(
                id=strawberry.ID(str(db_id)),
                video_path=str(info.get("video_path", "")),
                video_size_bytes=int(info.get("video_size", 0) or 0),
                payload_frame_count=int(info.get("frame_count", 0) or 0),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def storage_metrics(
        self,
        db_id: strawberry.ID,
        table_name: Optional[str] = None,
    ) -> StorageMetrics:
        """Return comparative storage metrics (MKV vs Parquet vs CSV) for a database."""
        try:
            from app.video_storage import VideoDB

            info = video_service.get_video_info(str(db_id), table_name=table_name)
            vpath = Path(str(info.get("video_path", video_path(str(db_id)))))
            if not vpath.exists():
                raise ValueError("Video database not found")

            idx_path = parquet_index_path(str(db_id), table_name)

            with VideoDB(vpath, mode="r") as vdb:
                m = vdb.get_storage_metrics(parquet_index_path=idx_path)

            return StorageMetrics(
                mkv_bytes=int(m.get("mkv_bytes", 0)),
                parquet_index_bytes=int(m.get("parquet_index_bytes", 0)),
                row_count=int(m.get("row_count", 0)),
                frame_count=int(m.get("frame_count", 0)),
                compression_ratio=float(m.get("compression_ratio", 0.0)),
                codec=str(m.get("codec", "ffv1")),
                compression_algorithm=str(m.get("compression_algorithm", "zstd")),
                estimated_csv_bytes=int(m.get("estimated_csv_bytes", 0)),
                estimated_parquet_bytes=int(m.get("estimated_parquet_bytes", 0)),
                parquet_vs_mkv_ratio=float(m.get("parquet_vs_mkv_ratio", 0.0)),
                encode_time_ms=float(m.get("encode_time_ms", 0.0)),
                parquet_index_exists=idx_path.is_file(),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def performance_log_stats(self) -> PerformanceLogStats:
        """Pending batched writes and last flush hints for perf persistence."""
        try:
            s = perf_persist_stats()
            return PerformanceLogStats(
                pending_count=int(s["pending_count"]),
                last_flush_epoch=s.get("last_flush_epoch"),
                last_error=s.get("last_error"),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def performance_events(
        self,
        db_id: Optional[strawberry.ID] = None,
        operation: Optional[str] = None,
        limit: int = 100,
    ) -> list[PerformanceEvent]:
        """Recent structured perf events (newest first), ring + on-disk merge when db_id set."""
        try:
            db_filter = str(db_id) if db_id else None
            op_filter = (operation or "").strip() or None
            if db_filter:
                events = list_merged_events(db_filter, op_filter, int(limit))
            else:
                events = list_events(db_id=None, operation=op_filter, limit=int(limit))
            return [
                PerformanceEvent(
                    id=strawberry.ID(ev.id),
                    ts=ev.ts,
                    db_id=strawberry.ID(ev.db_id) if ev.db_id else None,
                    table_name=ev.table_name,
                    operation=ev.operation,
                    duration_ms=ev.duration_ms,
                    bytes_in=ev.bytes_in,
                    bytes_out=ev.bytes_out,
                    rows=ev.rows,
                    meta=cast(JSON, ev.meta),
                )
                for ev in events
            ]
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def database_schema(
        self, db_id: strawberry.ID, table_name: Optional[str] = None
    ) -> list[TableSchemaColumn]:
        try:
            info = video_service.get_video_info(str(db_id), table_name=table_name)
            if info.get("error") == "Video database not found":
                return []
            if info.get("error"):
                raise ValueError(info["error"])
            columns = info.get("columns", [])
            return [
                TableSchemaColumn(
                    cid=i,
                    name=col["name"],
                    type=col["type"],
                    notnull=0 if col.get("nullable", True) else 1,
                    default_value=col.get("default"),
                    pk=1 if col.get("primary_key", False) else 0,
                    unique=bool((col.get("constraints") or {}).get("unique", False)),
                )
                for i, col in enumerate(columns)
            ]
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def database_rows(
        self,
        db_id: strawberry.ID,
        limit: int = 100,
        offset: int = 0,
        table_name: Optional[str] = None,
        column_offset: int = 0,
        column_limit: Optional[int] = None,
    ) -> TableRowsResult:
        try:
            tid = str(db_id)
            table = (table_name or _logical_table_name(tid)).replace('"', '""')
            info = video_service.get_video_info(tid, table_name=table_name)
            if info.get("error") == "Video database not found":
                return TableRowsResult(
                    columns=[],
                    values_json="[]",
                    total_row_count=0,
                    total_column_count=0,
                )
            if info.get("error"):
                raise ValueError(info["error"])

            schema_cols = [str(c["name"]) for c in info.get("columns", [])]
            total_column_count = len(schema_cols)
            total_row_count = video_service.count_table_rows(tid, table_name)

            if column_limit is None:
                query = (
                    f'SELECT * FROM "{table}" LIMIT {int(limit)} OFFSET {int(offset)}'
                )
                result = video_service.query_video_database(tid, query)
                if result.get("error") == "Video database not found":
                    return TableRowsResult(
                        columns=[],
                        values_json="[]",
                        total_row_count=0,
                        total_column_count=0,
                    )
                if "error" in result:
                    raise ValueError(result["error"])

                return TableRowsResult(
                    columns=result.get("columns", []),
                    values_json=json.dumps(result.get("rows", []), default=str),
                    total_row_count=total_row_count,
                    total_column_count=total_column_count,
                )

            co = max(0, int(column_offset))
            cl = max(1, int(column_limit))
            subset = schema_cols[co : co + cl]
            win = video_service.select_table_rows_window(
                tid, table_name, int(limit), int(offset), subset
            )
            if win.get("error") == "Video database not found":
                return TableRowsResult(
                    columns=[],
                    values_json="[]",
                    total_row_count=0,
                    total_column_count=0,
                )
            if "error" in win:
                raise ValueError(win["error"])

            return TableRowsResult(
                columns=list(win.get("columns", [])),
                values_json=json.dumps(win.get("rows", []), default=str),
                total_row_count=total_row_count,
                total_column_count=total_column_count,
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def frame_meta(
        self,
        db_id: strawberry.ID,
        logical_total_frames: int = LOGICAL_TOTAL_FRAMES_DEFAULT,
        table_name: Optional[str] = None,
    ) -> FrameMeta:
        try:
            info = video_service.get_video_info(str(db_id), table_name=table_name)
            if info.get("error") == "Video database not found":
                return FrameMeta(
                    payload_frame_count=1,
                    logical_total_frames=logical_total_frames,
                    video_size_bytes=0,
                )
            frame_count = int(info.get("frame_count", 0))
            return FrameMeta(
                payload_frame_count=max(1, frame_count),
                logical_total_frames=logical_total_frames,
                video_size_bytes=int(info.get("video_size", 0) or 0),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.field
    def frame_preview(
        self,
        db_id: strawberry.ID,
        frame_index: int,
        table_name: Optional[str] = None,
    ) -> FramePreview:
        try:
            preview = video_service.get_frame_preview(
                str(db_id), frame_index, table_name=table_name
            )
            if "error" in preview:
                b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                return FramePreview(
                    frame_index=frame_index,
                    mime_type="image/png",
                    base64_png=b64,
                    data_url=f"data:image/png;base64,{b64}",
                )
            return FramePreview(
                frame_index=int(preview["frame_index"]),
                mime_type=str(preview["mime_type"]),
                base64_png=str(preview["base64_png"]),
                data_url=str(preview["data_url"]),
            )
        except Exception as e:
            raise ValueError("Frame preview not available") from e

    @strawberry.field
    def video_download_url(
        self, info: Info, db_id: strawberry.ID, table_name: Optional[str] = None
    ) -> str:
        _require_db(str(db_id), table_name=table_name)
        request: Request = info.context["request"]
        return _video_asset_url(request, str(db_id), table_name=table_name)

    @strawberry.field
    def feedback_entries(
        self, db_id: strawberry.ID, limit: int = 50
    ) -> list[FeedbackEntry]:
        try:
            rows = feedback_service.list_feedback(str(db_id), int(limit))
            return [
                FeedbackEntry(
                    session_id=str(r.get("session_id", "")),
                    message=str(r.get("message", "")),
                    rating=r.get("rating"),
                    created_at=str(r.get("created_at", "")),
                )
                for r in rows
            ]
        except Exception as e:
            raise ValueError(str(e))


def _sql_mutation_result(db_id: str, query: str) -> SqlResultType:
    result = video_service.query_video_database(db_id, query)
    if "error" in result:
        raise ValueError(result["error"])
    return SqlResultType(
        columns=result.get("columns", []),
        values_json=json.dumps(result.get("rows", []), default=str),
        rowcount=result.get("row_count", 0),
    )


def _csv_analysis_result(payload: dict[str, Any]) -> CsvAnalysisResult:
    return CsvAnalysisResult(
        headers=list(payload.get("headers", [])),
        row_count=int(payload.get("rowCount", 0)),
        sample_row_count=int(payload.get("sampleRowCount", 0)),
        columns=[
            CsvColumnAnalysis(
                index=int(col.get("index", 0)),
                source_name=str(col.get("sourceName", "")),
                suggested_name=str(col.get("suggestedName", "")),
                inferred_type=str(col.get("inferredType", "TEXT")),
                confidence=float(col.get("confidence", 0.0)),
                empty_count=int(col.get("emptyCount", 0)),
                unique_count=int(col.get("uniqueCount", 0)),
                is_unique_candidate=bool(col.get("isUniqueCandidate", False)),
                sample_values=[str(v) for v in col.get("sampleValues", [])],
            )
            for col in payload.get("columns", [])
        ],
        warnings=[str(w) for w in payload.get("warnings", [])],
        resolutions=[
            ResolutionRecommendation(
                width=int(rec.get("width", 0)),
                height=int(rec.get("height", 0)),
                label=str(rec.get("label", "")),
                estimated_frames=int(rec.get("estimatedFrames", 0)),
                estimated_payload_bytes=int(rec.get("estimatedPayloadBytes", 0)),
                is_current=bool(rec.get("isCurrent", False)),
                is_recommended=bool(rec.get("isRecommended", False)),
                reason=str(rec.get("reason", "")),
            )
            for rec in payload.get("resolutions", [])
        ],
    )


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_database(self) -> DatabaseInfo:
        uid = new_database_id()
        # Video database is created lazily when data is imported
        return DatabaseInfo(
            id=strawberry.ID(uid),
            video_path=str(video_path(uid)),
            video_size_bytes=0,
            payload_frame_count=0,
        )

    @strawberry.mutation
    def execute_query(self, db_id: strawberry.ID, query: str) -> SqlResultType:
        try:
            return _sql_mutation_result(str(db_id), query)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def execute_sql(self, db_id: strawberry.ID, query: str) -> SqlResultType:
        try:
            return _sql_mutation_result(str(db_id), query)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    async def analyze_csv_import(
        self,
        file: Upload,
        delimiter: str = ",",
        quote_char: str = '"',
        sample_rows: int = 100,
        compression: bool = True,
    ) -> CsvAnalysisResult:
        try:
            dest_dir = database_dir(new_database_id())
            temp_path = dest_dir / "temp_analyze.csv"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            await stream_upload_to_file(file, temp_path, max_bytes=MAX_UPLOAD_BYTES)
            try:
                payload = video_service.analyze_csv_import(
                    temp_path,
                    delimiter=delimiter,
                    quote_char=quote_char,
                    sample_rows=sample_rows,
                    compression=compression,
                )
                return _csv_analysis_result(payload)
            finally:
                from app.utils.filesystem import safe_rmtree

                safe_rmtree(dest_dir)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    async def import_csv(
        self,
        db_id: strawberry.ID,
        file: Upload,
        compression: bool = True,
        append: bool = False,
        table_name: str = "",
        delimiter: str = ",",
        quote_char: str = '"',
        import_plan: Optional[JSON] = None,
    ) -> CsvImportResult:
        try:
            name = str(table_name).strip()
            if not name:
                raise ValueError(
                    "tableName is required for each CSV import (logical table name)."
                )

            dest_dir = database_dir(str(db_id))
            temp_path = dest_dir / "temp_import.csv"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            await stream_upload_to_file(file, temp_path, max_bytes=MAX_UPLOAD_BYTES)

            csv_for_import = _normalize_csv_if_needed(
                temp_path, dest_dir, delimiter, quote_char
            )
            try:
                result = video_service.import_csv_to_video(
                    csv_for_import,
                    str(db_id),
                    append=append,
                    compression=compression,
                    import_plan=import_plan if isinstance(import_plan, dict) else None,
                    table_name=name,
                )
            finally:
                temp_path.unlink(missing_ok=True)
                if csv_for_import != temp_path:
                    csv_for_import.unlink(missing_ok=True)

            return CsvImportResult(
                table=str(result.get("table_name") or _logical_table_name(str(db_id))),
                imported_rows=result.get("row_count", 0),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def submit_feedback(
        self,
        db_id: strawberry.ID,
        session_id: str,
        message: str,
        rating: Optional[int] = None,
    ) -> MutationResult:
        try:
            feedback_service.submit_feedback(str(db_id), session_id, message, rating)
            return MutationResult(ok=True, message=None)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def auth_register(
        self, db_id: strawberry.ID, email: str, password: str
    ) -> AuthResult:
        try:
            out = auth_vsql_service.register_user(str(db_id), email, password)
            return AuthResult(
                ok=bool(out.get("ok")),
                token=None,
                message=str(out.get("message")) if out.get("message") else None,
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def auth_login(self, db_id: strawberry.ID, email: str, password: str) -> AuthResult:
        try:
            out = auth_vsql_service.login_user(str(db_id), email, password)
            return AuthResult(
                ok=bool(out.get("ok")),
                token=out.get("token"),
                message=str(out.get("message")) if out.get("message") else None,
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def update_cell(
        self,
        db_id: strawberry.ID,
        table_name: str,
        rowid: int,
        column: str,
        value: Optional[JSON] = None,
    ) -> MutationResult:
        try:
            if value is None:
                lit = "NULL"
            elif isinstance(value, bool):
                lit = "1" if value else "0"
            elif isinstance(value, (int, float)):
                lit = str(value)
            else:
                lit = "'" + str(value).replace("'", "''") + "'"
            safe_table = table_name.replace('"', '""')
            query = (
                f'UPDATE "{safe_table}" SET {column} = {lit} '
                f"WHERE rowid = {int(rowid)};"
            )
            result = video_service.query_video_database(str(db_id), query)
            if "error" in result:
                raise ValueError(result["error"])
            return MutationResult(ok=bool(result.get("success")), message=None)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def update_row(
        self,
        db_id: strawberry.ID,
        table_name: str,
        rowid: int,
        column: str,
        value: Optional[JSON] = None,
    ) -> MutationResult:
        try:
            if not table_name.strip():
                raise ValueError("tableName is required")
            if value is None:
                lit = "NULL"
            elif isinstance(value, bool):
                lit = "1" if value else "0"
            elif isinstance(value, (int, float)):
                lit = str(value)
            else:
                lit = "'" + str(value).replace("'", "''") + "'"
            safe_table = table_name.replace('"', '""')
            query = (
                f'UPDATE "{safe_table}" SET {column} = {lit} '
                f"WHERE rowid = {int(rowid)};"
            )
            result = video_service.query_video_database(str(db_id), query)
            if "error" in result:
                raise ValueError(result["error"])
            return MutationResult(ok=bool(result.get("success")), message=None)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def delete_row(
        self,
        db_id: strawberry.ID,
        rowid: int,
        table_name: Optional[str] = None,
    ) -> MutationResult:
        try:
            if not table_name:
                raise ValueError("tableName is required")
            safe_table = table_name.replace('"', '""')
            query = f'DELETE FROM "{safe_table}" WHERE rowid = {int(rowid)};'
            result = video_service.query_video_database(str(db_id), query)
            if "error" in result:
                raise ValueError(result["error"])
            return MutationResult(ok=bool(result.get("success")), message=None)
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def validate_database(self, db_id: strawberry.ID) -> MutationResult:
        try:
            report = video_service.validate_video_integrity(str(db_id))
            if report.get("overall_valid", False):
                return MutationResult(ok=True, message="Database is valid")
            else:
                return MutationResult(ok=False, message="Database validation failed")
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def repair_database(self, db_id: strawberry.ID) -> MutationResult:
        try:
            result = video_service.repair_video_database(str(db_id))
            if result.get("success", False):
                return MutationResult(ok=True, message="Database repaired successfully")
            else:
                return MutationResult(ok=False, message="Database repair failed")
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    def encode_video(
        self,
        info: Info,
        db_id: strawberry.ID,
        fps: int = 30,
        logical_total_frames: Optional[int] = None,
        table_name: Optional[str] = None,
        compression_algorithm: Optional[str] = "zstd",
        compression_level: Optional[str] = "balanced",
    ) -> EncodeResult:
        """Re-encode the workspace video (FPS, optional 1-hour shell, compression)."""
        try:
            tid = str(db_id)
            out = video_service.encode_video_database(
                tid,
                fps=int(fps),
                logical_total_frames=logical_total_frames,
                table_name=table_name,
                compression_algorithm=str(compression_algorithm or "zstd"),
                compression_level_preset=str(compression_level or "balanced"),
            )
            request: Request = info.context["request"]
            base = str(request.base_url).rstrip("/")
            vpath = str(out.get("video_path", ""))
            tbl = (table_name or "").strip() or None
            if tbl:
                vurl = f"{base}/databases/{tid}/tables/{tbl}/download/video"
            else:
                vurl = f"{base}/databases/{tid}/download/video"
            return EncodeResult(
                video_path=vpath,
                video_url=vurl,
                message="Encode completed",
            )
        except Exception as e:
            raise ValueError(str(e)) from e

    @strawberry.mutation
    def export_as_format(
        self,
        info: Info,
        db_id: strawberry.ID,
        format: str,
        table_name: Optional[str] = None,
    ) -> FormatExportResult:
        """Export a VSQL database/table to an external columnar format.

        Supported formats: ``parquet``, ``arrow``.
        Returns a ``FormatExportResult`` with a ``download_url``.
        """
        try:
            from app.video_storage import VideoDB

            db_id_str = str(db_id)
            fmt = format.lower().strip()
            if fmt not in {"parquet", "arrow"}:
                raise ValueError(
                    f"Unsupported format '{format}'. Use 'parquet' or 'arrow'."
                )

            vinfo = video_service.get_video_info(db_id_str, table_name=table_name)
            vpath = Path(str(vinfo.get("video_path", video_path(db_id_str))))
            if not vpath.exists():
                raise ValueError("Video database not found")

            request: Request = info.context["request"]
            base = str(request.base_url).rstrip("/")

            with VideoDB(vpath, mode="r") as vdb:
                if fmt == "parquet":
                    out_path = parquet_export_path(db_id_str, table_name)
                    stats = vdb.export_parquet(out_path)
                    if table_name:
                        dl_url = f"{base}/databases/{db_id_str}/tables/{table_name}/export/parquet"
                    else:
                        dl_url = f"{base}/databases/{db_id_str}/export/parquet"
                else:
                    out_path = arrow_export_path(db_id_str, table_name)
                    stats = vdb.export_arrow(out_path)
                    if table_name:
                        dl_url = f"{base}/databases/{db_id_str}/tables/{table_name}/export/arrow"
                    else:
                        dl_url = f"{base}/databases/{db_id_str}/export/arrow"

            return FormatExportResult(
                format=fmt,
                download_url=dl_url,
                file_size_bytes=int(stats.get("file_size_bytes", 0)),
                row_count=int(stats.get("rows", 0)),
                elapsed_ms=float(stats.get("elapsed_ms", 0.0)),
            )
        except Exception as e:
            raise ValueError(str(e))

    @strawberry.mutation
    async def decode_mp4(self, file: Upload) -> DatabaseInfo:
        uid = new_database_id()
        dest_dir = database_dir(uid)
        tmp_mp4 = dest_dir / "upload.mkv"
        await stream_upload_to_file(file, tmp_mp4, max_bytes=MAX_UPLOAD_BYTES)

        try:
            # Validate the uploaded video
            from app.video_storage import VideoDB

            with VideoDB(tmp_mp4, mode="r") as vdb:
                if not vdb.validate_integrity():
                    raise ValueError("Invalid video format")

                # Copy to final location
                final_path = video_path(uid)

                shutil.copy2(tmp_mp4, final_path)
                sz = final_path.stat().st_size
                fc = int(vdb.get_info().get("frame_count", 0) or 0)

                return DatabaseInfo(
                    id=strawberry.ID(uid),
                    video_path=str(final_path),
                    video_size_bytes=int(sz),
                    payload_frame_count=int(fc),
                )
        except Exception as e:
            from app.utils.filesystem import safe_rmtree

            safe_rmtree(dest_dir)
            raise ValueError(f"Decode failed: {e}") from e
        finally:
            tmp_mp4.unlink(missing_ok=True)
