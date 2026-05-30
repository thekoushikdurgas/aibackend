"""Video storage service functions."""

import base64
import csv
import re
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import imageio.v2 as imageio
import pandas as pd

from ..storage import (
    list_catalog_tables,
    register_table,
    table_video_path,
    video_path,
)
from ..video_storage import VideoDB, VideoSchema
from .csv_analysis_service import (
    analyze_csv_path,
    normalize_csv_with_plan,
)
from .perf_event_log import maybe_log_frame_preview, timed_operation
from .perf_event_store import is_reserved_table_name

TABLE_IDENT_RE = r"(?:\"([^\"]+)\"|(\w+))"


def _clean_table_name(table_name: str) -> str:
    return table_name.strip().strip('"') or "data"


def _table_name_from_match(match: re.Match[str], group_index: int = 1) -> str:
    return _clean_table_name(
        match.group(group_index) or match.group(group_index + 1) or ""
    )


def _logical_table_name_from_info(info: Dict[str, Any]) -> str:
    if info.get("table_name"):
        return str(info["table_name"])
    names = {c["name"] for c in info.get("columns", [])}
    if {"name", "email", "phone"} <= names:
        return "users"
    return "data"


def _suggest_table_name_from_csv(csv_path: Path) -> str:
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
    except (OSError, StopIteration):
        return "data"
    names = {header.strip() for header in headers}
    if {"name", "email", "phone"} <= names:
        return "users"
    return "data"


def list_video_tables(db_id: str) -> List[str]:
    """Return logical tables in this workspace, including legacy single-video DBs."""
    catalog_names = [
        item["name"]
        for item in list_catalog_tables(db_id)
        if table_video_path(db_id, item["name"]).is_file()
        and not is_reserved_table_name(item["name"])
    ]
    if catalog_names:
        return catalog_names

    legacy = video_path(db_id)
    if not legacy.is_file():
        return []
    with VideoDB(legacy, mode="r") as vdb:
        return [_logical_table_name_from_info(vdb.get_info())]


def _extract_table_name(query: str) -> Optional[str]:
    q = query.strip().rstrip(";")
    patterns = [
        rf"CREATE\s+TABLE\s+{TABLE_IDENT_RE}(?=\s|\()",
        rf"SELECT\s+.+?\s+FROM\s+{TABLE_IDENT_RE}(?=\s|$)",
        rf"INSERT\s+INTO\s+{TABLE_IDENT_RE}(?=\s|\()",
        rf"UPDATE\s+{TABLE_IDENT_RE}\s+SET\b",
        rf"DELETE\s+FROM\s+{TABLE_IDENT_RE}(?=\s|$)",
    ]
    for pattern in patterns:
        match = re.match(pattern, q, re.IGNORECASE | re.DOTALL)
        if match:
            return _table_name_from_match(match)
    return None


def _resolve_video_file(db_id: str, table_name: Optional[str] = None) -> Path:
    """Resolve a table to its video file with legacy single-video fallback."""
    requested = _clean_table_name(table_name or "")
    catalog = list_catalog_tables(db_id)
    if catalog:
        if table_name:
            for item in catalog:
                if item["name"] == requested:
                    return table_video_path(db_id, item["name"])
            return table_video_path(db_id, requested)
        if len(catalog) == 1:
            return table_video_path(db_id, catalog[0]["name"])
        return table_video_path(db_id, requested)

    legacy = video_path(db_id)
    if legacy.is_file():
        return legacy
    return table_video_path(db_id, requested)


def _create_video_file_for_table(db_id: str, table_name: str) -> Path:
    """Use legacy path for unnamed default imports; real table names get catalog entries."""
    name = _clean_table_name(table_name)
    if is_reserved_table_name(name):
        raise ValueError("Table names with reserved prefix __vsql_ are not allowed")
    register_table(db_id, name)
    return table_video_path(db_id, name)


def create_video_database(
    data_source: Union[str, Path, List[dict], dict, bytes],
    db_id: str,
    data_type: str = "csv",
    compression: bool = True,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Create a new video database from various data sources."""
    video_file = video_path(db_id)

    # Create video database instance
    with VideoDB(video_file, mode="rw") as vdb:
        if data_type == "csv":
            vdb.create_from_csv(
                data_source, compression=compression, overwrite=overwrite
            )
        elif data_type == "json":
            vdb.create_from_json(
                data_source, compression=compression, overwrite=overwrite
            )
        elif data_type == "bytes":
            # Need schema for bytes data
            raise ValueError(
                "Schema required for bytes data, use create_video_database_with_schema"
            )
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        return vdb.get_info()


def create_video_database_with_schema(
    data: bytes,
    schema: VideoSchema,
    db_id: str,
    compression: bool = True,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Create video database from raw bytes with explicit schema."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="rw") as vdb:
        vdb.create_from_bytes(
            data, schema, compression=compression, overwrite=overwrite
        )
        return vdb.get_info()


def _import_plan_requires_column_pipeline(import_plan: Dict[str, Any]) -> bool:
    """True when the client sent mapping / options beyond a bare logical table name."""
    if not import_plan:
        return False
    return bool(set(import_plan.keys()) - {"tableName"})


def import_csv_to_video(
    csv_path: Union[str, Path],
    db_id: str,
    append: bool = False,
    compression: bool = True,
    import_plan: Optional[Dict[str, Any]] = None,
    table_name: str = "",
) -> Dict[str, Any]:
    """Import CSV file into video database."""
    csv_path = Path(csv_path)
    merged_plan: Optional[Dict[str, Any]] = None
    if import_plan:
        merged_plan = dict(import_plan)
    if table_name:
        merged_plan = {**(merged_plan or {}), "tableName": table_name}

    mapped_path: Optional[Path] = None
    schema: Optional[VideoSchema] = None
    if merged_plan and _import_plan_requires_column_pipeline(merged_plan):
        mapped_path = csv_path.with_name(f"{csv_path.stem}_mapped.csv")
        csv_path, schema = normalize_csv_with_plan(csv_path, mapped_path, merged_plan)
        _validate_unique_columns(csv_path, schema)

    try:
        target_table = _clean_table_name(
            table_name
            or (merged_plan or {}).get("tableName", "")
            or _suggest_table_name_from_csv(csv_path)
        )
        video_file = _create_video_file_for_table(db_id, target_table)
        csv_sz = int(csv_path.stat().st_size) if csv_path.exists() else 0
        with timed_operation(
            "csv_import", db_id=db_id, table_name=target_table, bytes_in=csv_sz
        ) as extra:
            with VideoDB(video_file, mode="rw") as vdb:
                if not video_file.exists() or not append:
                    # Create new database
                    vdb.create_from_csv(
                        csv_path,
                        schema=schema,
                        compression=compression,
                        overwrite=True,
                    )
                else:
                    # Append to existing database
                    vdb.crud.bulk_import_csv(csv_path, append=True)

                info = vdb.get_info()
                info["table_name"] = target_table
            extra["append"] = append
            extra["row_count"] = int(info.get("row_count", 0) or 0)
        return info
    finally:
        if mapped_path:
            mapped_path.unlink(missing_ok=True)


def analyze_csv_import(
    csv_path: Union[str, Path],
    delimiter: str = ",",
    quote_char: str = '"',
    sample_rows: int = 100,
    compression: bool = True,
) -> Dict[str, Any]:
    """Analyze CSV headers/data for import planning."""
    return analyze_csv_path(
        Path(csv_path),
        delimiter=delimiter,
        quote_char=quote_char,
        sample_rows=sample_rows,
        compression=compression,
    )


def _validate_unique_columns(csv_path: Path, schema: VideoSchema) -> None:
    unique_cols = [
        col.name for col in schema.columns if (col.constraints or {}).get("unique")
    ]
    if not unique_cols:
        return
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for col_name in unique_cols:
        values = [
            str(row.get(col_name, "")).strip()
            for row in rows
            if str(row.get(col_name, "")).strip() != ""
        ]
        if len(values) != len(set(values)):
            raise ValueError(f"Column '{col_name}' contains duplicate values")


def export_video_to_csv(
    db_id: str,
    output_path: Union[str, Path],
    start_row: int = 0,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Export video database to CSV file."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="r") as vdb:
        if start_row == 0 and max_rows is None:
            # Export all data
            vdb.export_to_csv(output_path)
        else:
            # Export partial data
            csv_content = vdb.decoder.decode_partial_frames(
                vdb._frames, start_row, max_rows
            )
            Path(output_path).write_text(csv_content, encoding="utf-8")

        return {
            "exported_rows": (
                min(max_rows, vdb.get_row_count()) if max_rows else vdb.get_row_count()
            ),
            "total_rows": vdb.get_row_count(),
            "output_path": str(output_path),
        }


def export_video_to_json(
    db_id: str,
    output_path: Union[str, Path],
    start_row: int = 0,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Export video database to JSON file."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="r") as vdb:
        if start_row == 0 and max_rows is None:
            # Export all data
            vdb.export_to_json(output_path)
        else:
            # Export partial data
            data = vdb.decoder.decode_frames_to_json(vdb._frames)

            # Apply range limits
            if start_row > 0 or max_rows is not None:
                end_row = None if max_rows is None else start_row + max_rows
                data = data[start_row:end_row]

            import json

            Path(output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

        return {
            "exported_rows": (
                min(max_rows, vdb.get_row_count()) if max_rows else vdb.get_row_count()
            ),
            "total_rows": vdb.get_row_count(),
            "output_path": str(output_path),
        }


def get_video_info(db_id: str, table_name: Optional[str] = None) -> Dict[str, Any]:
    """Get video database information."""
    video_file = _resolve_video_file(db_id, table_name)

    if not video_file.exists():
        return {"error": "Video database not found"}

    with VideoDB(video_file, mode="r") as vdb:
        info = vdb.get_info()
        if table_name:
            info["table_name"] = _clean_table_name(table_name)
        elif not info.get("table_name"):
            info["table_name"] = _logical_table_name_from_info(info)
        return info


def get_frame_preview(
    db_id: str, frame_index: int, table_name: Optional[str] = None
) -> Dict[str, Any]:
    """Return a PNG data URL for a stored RGBA frame."""
    video_file = _resolve_video_file(db_id, table_name)
    if not video_file.exists():
        return {"error": "Video database not found"}

    with VideoDB(video_file, mode="r") as vdb:
        frames = vdb._frames or []
        if not frames:
            return {"error": "No frames available"}
        safe_index = max(0, min(int(frame_index), len(frames) - 1))
        buffer = BytesIO()
        t0 = time.perf_counter()
        imageio.imwrite(buffer, frames[safe_index], format="png")  # type: ignore[call-overload]
        dt_ms = (time.perf_counter() - t0) * 1000.0
        png = buffer.getvalue()
        b64 = base64.b64encode(png).decode("ascii")
        tbl = (
            _clean_table_name(table_name)
            if table_name and str(table_name).strip()
            else None
        )
        maybe_log_frame_preview(db_id, tbl, safe_index, dt_ms, len(png))
        return {
            "frame_index": safe_index,
            "mime_type": "image/png",
            "base64_png": b64,
            "data_url": f"data:image/png;base64,{b64}",
        }


def validate_video_integrity(db_id: str) -> Dict[str, Any]:
    """Validate video database integrity."""
    video_file = video_path(db_id)

    if not video_file.exists():
        return {"valid": False, "error": "Video database not found"}

    with VideoDB(video_file, mode="r") as vdb:
        return vdb.integrity.get_integrity_report()


def _row_index_from_rowid_where(where_clause: Optional[str]) -> Optional[int]:
    """Parse ``WHERE rowid = N`` into a 0-based row index."""
    if not where_clause:
        return None
    m = re.search(r"rowid\s*=\s*(\d+)", where_clause, re.IGNORECASE)
    if not m:
        return None
    return max(0, int(m.group(1)) - 1)


def _parse_create_table(query: str) -> Optional[Tuple[str, VideoSchema]]:
    """Parse ``CREATE TABLE name (col TYPE, ...)`` into schema."""
    q = query.strip().rstrip(";")
    m = re.match(
        rf"CREATE\s+TABLE\s+{TABLE_IDENT_RE}\s*\((.+)\)\s*$",
        q,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    table_name, body = _table_name_from_match(m), m.group(3)
    parts = [p.strip() for p in body.split(",") if p.strip()]
    schema = VideoSchema()
    for part in parts:
        cm = re.match(r"(\w+)\s+(INTEGER|REAL|TEXT|BLOB)\b(.*)$", part, re.IGNORECASE)
        if not cm:
            return None
        cname, ctype, rest = cm.group(1), cm.group(2).upper(), cm.group(3).upper()
        pk = "PRIMARY KEY" in rest
        unique = "UNIQUE" in rest or pk
        nullable = "NOT NULL" not in rest and not pk
        schema.add_column(
            cname,
            ctype,
            nullable=nullable,
            primary_key=pk,
            constraints={"unique": unique},
        )
    schema.table_name = table_name
    return table_name, schema


def _execute_create_table(db_id: str, query: str) -> Dict[str, Any]:
    parsed = _parse_create_table(query)
    if not parsed:
        return {"error": "Invalid CREATE TABLE syntax"}
    table_name, schema = parsed
    video_file = _create_video_file_for_table(db_id, table_name)
    if video_file.exists():
        return {"error": f"Table '{table_name}' already exists"}

    from ..video_storage.encoder import DataEncoder

    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", suffix=".csv", delete=False
    ) as tf:
        writer = csv.writer(tf)
        writer.writerow(schema.get_column_names())
        tmp_path = Path(tf.name)
    try:
        enc = DataEncoder()
        frames, sch = enc.encode_csv_to_frames(
            tmp_path, schema=schema, compression=True
        )
        with VideoDB(video_file, mode="rw") as vdb:
            vdb._save_frames(frames)
            vdb._frames = frames
            vdb.schema = sch
            vdb._loaded = True
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"columns": [], "rows": [], "row_count": 0, "success": True}


def count_table_rows(db_id: str, table_name: Optional[str] = None) -> int:
    """Total logical rows in the table (for pagination UI)."""
    video_file = _resolve_video_file(db_id, table_name)
    if not video_file.exists():
        return 0
    with VideoDB(video_file, mode="rw") as vdb:
        return vdb.query.count()


def select_table_rows_window(
    db_id: str,
    table_name: Optional[str],
    limit: int,
    offset: int,
    column_names: List[str],
) -> Dict[str, Any]:
    """Paged browse using VideoQuery.select (avoids SQL parser comma issues)."""
    video_file = _resolve_video_file(db_id, table_name)
    if not video_file.exists():
        return {"error": "Video database not found"}
    try:
        with VideoDB(video_file, mode="rw") as vdb:
            cols = ["rowid"] + [
                c for c in column_names if c != "rowid" and c != "_rowid"
            ]
            result = vdb.query.select(
                columns=cols,
                where=None,
                order_by=None,
                limit=limit,
                offset=offset,
            )
            out_columns = ["_rowid" if c == "rowid" else c for c in result.columns]
            return {
                "columns": out_columns,
                "rows": result.rows,
                "row_count": result.row_count,
            }
    except Exception as e:
        return {"error": str(e)}


def query_video_database(
    db_id: str, query: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute query on video database."""
    qstrip = query.strip()
    qu = qstrip.upper()

    if qu.startswith("CREATE"):
        return _execute_create_table(db_id, qstrip)

    table_name = _extract_table_name(qstrip)
    video_file = _resolve_video_file(db_id, table_name)
    if not video_file.exists():
        return {"error": "Video database not found"}

    with VideoDB(video_file, mode="rw") as vdb:
        if qu.startswith("SELECT"):
            return _execute_select_query(vdb, query, params)
        if qu.startswith("INSERT"):
            return _execute_insert_query(vdb, query, params)
        if qu.startswith("UPDATE"):
            return _execute_update_query(vdb, query, params)
        if qu.startswith("DELETE"):
            return _execute_delete_query(vdb, query, params)
        return {"error": "Unsupported query type"}


def _execute_select_query(
    vdb: VideoDB, query: str, params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Execute SELECT query."""
    try:
        # Simple SELECT parser
        # Format: SELECT columns FROM table [WHERE condition] [ORDER BY column] [LIMIT n [OFFSET m]]
        import re

        q = query.strip().rstrip(";")

        pattern = (
            r'SELECT\s+(.+?)\s+FROM\s+(?:"[^"]+"|\w+)'
            r"(?:\s+WHERE\s+((?:(?!\s+ORDER\s+BY\b).)+))?"
            r"(?:\s+ORDER\s+BY\s+((?:(?!\s+LIMIT\b).)+))?"
            r"(?:\s+LIMIT\s+(\d+))?"
            r"(?:\s+OFFSET\s+(\d+))?"
            r"\s*$"
        )
        match = re.match(pattern, q, re.IGNORECASE)

        if not match:
            return {"error": "Invalid SELECT syntax"}

        columns_part = match.group(1).strip()
        where_clause = match.group(2).strip() if match.group(2) else None
        if where_clause:
            where_clause = where_clause.rstrip(";").strip()
        order_by = match.group(3).strip() if match.group(3) else None
        limit = int(match.group(4)) if match.group(4) else None
        offset = int(match.group(5)) if match.group(5) else 0

        if re.match(r"^COUNT\s*\(\s*\*\s*\)$", columns_part, re.IGNORECASE):
            cnt = vdb.query.count(where=where_clause)
            return {
                "columns": ["COUNT(*)"],
                "rows": [[cnt]],
                "row_count": 1,
                "data": [{"COUNT(*)": cnt}],
            }

        # Parse columns
        if columns_part == "*":
            columns = None
        else:
            columns = [col.strip() for col in columns_part.split(",")]

        # Execute query
        result = vdb.query.select(
            columns=columns,
            where=where_clause,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

        return {
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
            "data": result.to_dict_list(),
        }

    except Exception as e:
        return {"error": str(e)}


def _execute_insert_query(
    vdb: VideoDB, query: str, params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Execute INSERT query."""
    try:
        # Simple INSERT parser
        # Format: INSERT INTO table (col1, col2) VALUES (val1, val2)
        import re

        pattern = r'INSERT\s+INTO\s+(?:"[^"]+"|\w+)\s*\((.+?)\)\s*VALUES\s*\((.+?)\)'
        match = re.match(pattern, query.strip(), re.IGNORECASE)

        if not match:
            return {"error": "Invalid INSERT syntax"}

        columns = [col.strip() for col in match.group(1).split(",")]
        values = [val.strip().strip("'\"") for val in match.group(2).split(",")]

        # Create row data
        row_data = dict(zip(columns, values))

        # Insert row
        row_id = vdb.crud.insert_row(row_data)

        return {
            "success": True,
            "row_id": row_id,
            "message": "Row inserted successfully",
            "columns": [],
            "rows": [],
            "row_count": 1,
        }

    except Exception as e:
        return {"error": str(e)}


def _execute_update_query(
    vdb: VideoDB, query: str, params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Execute UPDATE query."""
    try:
        # Simple UPDATE parser
        # Format: UPDATE table SET col1 = val1, col2 = val2 WHERE condition
        import re

        pattern = (
            r'UPDATE\s+(?:"[^"]+"|\w+)\s+SET\s+'
            r"((?:(?!\s+WHERE\b).)+)"
            r"(?:\s+WHERE\s+(.+))?\s*$"
        )
        match = re.match(pattern, query.strip().rstrip(";"), re.IGNORECASE)

        if not match:
            return {"error": "Invalid UPDATE syntax"}

        set_clause = match.group(1).strip()
        where_clause = match.group(2).strip() if match.group(2) else None
        if where_clause:
            where_clause = where_clause.rstrip(";").strip()

        # Parse SET clause
        updates = {}
        for set_part in set_clause.split(","):
            col, val = set_part.split("=", 1)
            updates[col.strip()] = val.strip().strip("'\"")

        if where_clause:
            idx = _row_index_from_rowid_where(where_clause)
            if idx is None:
                return {"error": "UPDATE with WHERE requires rowid = N"}
            success = vdb.crud.update_row(idx, updates)
        else:
            success = vdb.crud.update_row(0, updates)

        return {
            "success": success,
            "message": "Row updated successfully" if success else "Update failed",
            "columns": [],
            "rows": [],
            "row_count": 1 if success else 0,
        }

    except Exception as e:
        return {"error": str(e)}


def _execute_delete_query(
    vdb: VideoDB, query: str, params: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Execute DELETE query."""
    try:
        # Simple DELETE parser
        # Format: DELETE FROM table WHERE condition
        import re

        pattern = r'DELETE\s+FROM\s+(?:"[^"]+"|\w+)\s*(?:WHERE\s+(.+))?$'
        match = re.match(pattern, query.strip().rstrip(";"), re.IGNORECASE)

        if not match:
            return {"error": "Invalid DELETE syntax"}

        where_clause = match.group(1).strip() if match.group(1) else None

        if where_clause:
            idx = _row_index_from_rowid_where(where_clause)
            if idx is None:
                return {"error": "DELETE with WHERE requires rowid = N"}
            success = vdb.crud.delete_row(idx)
        else:
            success = vdb.crud.delete_row(0)

        return {
            "success": success,
            "message": "Row deleted successfully" if success else "Delete failed",
            "columns": [],
            "rows": [],
            "row_count": 1 if success else 0,
        }

    except Exception as e:
        return {"error": str(e)}


def encode_video_database(
    db_id: str,
    fps: int = 30,
    logical_total_frames: Optional[int] = None,
    table_name: Optional[str] = None,
    compression_algorithm: str = "zstd",
    compression_level_preset: str = "balanced",
) -> Dict[str, Any]:
    """Re-encode the workspace MKV with optional FPS, black-frame shell, and compression.

    Decodes the current payload (strips any black tail), recompresses tabular bytes,
    rebuilds RGBA frames, writes MKV + Parquet sidecar.
    """
    from ..codec.frames import frames_pad_to_count, split_payload_and_tail

    algo = (compression_algorithm or "zstd").strip().lower()
    if algo not in ("zstd", "zlib"):
        algo = "zstd"

    preset = (compression_level_preset or "balanced").strip().lower()
    zstd_level = {"fast": 1, "balanced": 3, "maximum": 19}.get(preset, 3)
    zlib_level = {"fast": 3, "balanced": 6, "maximum": 9}.get(preset, 6)
    codec_level = zstd_level if algo == "zstd" else zlib_level

    video_file = _resolve_video_file(db_id, table_name)
    if not video_file.exists():
        raise ValueError("Video database not found")

    tbl = (
        _clean_table_name(table_name)
        if table_name and str(table_name).strip()
        else None
    )
    with timed_operation("encode_video", db_id=db_id, table_name=tbl) as extra:
        with VideoDB(video_file, mode="rw", encode_fps=max(1, int(fps))) as vdb:
            if not vdb._frames:
                vdb._load_video()
            if not vdb._frames:
                raise ValueError("No frames loaded")
            payload_only = split_payload_and_tail(vdb._frames)
            payload_bytes = vdb.decoder.decode_frames_to_bytes(payload_only)
            schema = vdb.schema
            if schema is None:
                raise ValueError("No schema in video database")

            new_payload_frames = vdb.encoder.encode_bytes_to_frames(
                payload_bytes,
                schema,
                compression=True,
                compression_algorithm=algo,
                compression_level=codec_level,
            )
            if logical_total_frames is not None:
                lt = int(logical_total_frames)
                final_frames = frames_pad_to_count(new_payload_frames, lt)
            else:
                final_frames = new_payload_frames

            vdb._save_frames(final_frames)
            vdb._frames = final_frames
            vdb._loaded = True
            info = vdb.get_info()

        extra["fps"] = max(1, int(fps))
        extra["frame_count"] = int(len(final_frames))
        if logical_total_frames is not None:
            extra["logical_total_frames"] = int(logical_total_frames)

    return {
        "video_path": str(video_file),
        "frame_count": int(info.get("frame_count", len(final_frames))),
        "fps": max(1, int(fps)),
    }


def get_video_dataframe(db_id: str) -> pd.DataFrame:
    """Get video database as pandas DataFrame."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="r") as vdb:
        return vdb.get_dataframe()


def add_column_to_video(
    db_id: str, column_name: str, data_type: str, default_value: Any = None
) -> Dict[str, Any]:
    """Add a new column to video database."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="rw") as vdb:
        vdb.add_column(column_name, data_type, default_value)
        return vdb.get_info()


def remove_column_from_video(db_id: str, column_name: str) -> Dict[str, Any]:
    """Remove a column from video database."""
    video_file = video_path(db_id)

    with VideoDB(video_file, mode="rw") as vdb:
        vdb.remove_column(column_name)
        return vdb.get_info()


def repair_video_database(db_id: str) -> Dict[str, Any]:
    """Attempt to repair corrupted video database."""
    video_file = video_path(db_id)

    if not video_file.exists():
        return {"success": False, "error": "Video database not found"}

    with VideoDB(video_file, mode="rw") as vdb:
        success = vdb.repair_database()

        return {
            "success": success,
            "message": "Database repaired successfully" if success else "Repair failed",
            "info": vdb.get_info(),
        }
