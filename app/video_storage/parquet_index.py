"""Parquet/Arrow columnar sidecar for VSQL video databases.

Architecture (from docs/bigquery.md):
  - VSQL MKV  = archival / exact byte recovery layer
  - Parquet   = analytics / index layer (fast column-pruned reads)

This module builds a ``vsql-index.parquet`` file alongside every MKV,
containing all logical data columns plus three internal pointer columns:

  _vsql_row         int64  — 0-based row position in the payload
  _vsql_frame       int32  — frame index in the MKV that carries this row
  _vsql_byte_offset int64  — byte offset within the decoded payload stream
  _vsql_byte_length int32  — byte length of this row's CSV line (incl. newline)

Queries that only need analytics (aggregations, filters) hit the Parquet
file directly.  Only when the caller needs the *exact original payload*
does it decode the MKV frame range from the pointer columns.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..services.perf_event_log import append_event, db_id_from_video_path

logger = logging.getLogger(__name__)

# Bytes per RGBA frame pixel actually used for payload (3 channels, A=255).
_FRAME_PAYLOAD_BYTES = 1280 * 720 * 3


def _try_import_pyarrow():
    try:
        import pyarrow as pa  # type: ignore[import-untyped]
        import pyarrow.parquet as pq  # type: ignore[import-untyped]

        return pa, pq
    except ImportError:
        return None, None


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_parquet_index(
    csv_content: str,
    output_path: Path,
    *,
    video_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Parse *csv_content* and write a columnar Parquet index to *output_path*.

    Args:
        csv_content: Decoded CSV text from the VSQL payload.
        output_path: Where to write ``vsql-index.parquet``.
        video_path:  The companion MKV file (used only for size reporting).

    Returns:
        A dict with build statistics: rows, columns, file_size_bytes, elapsed_ms.
    """
    pa, pq = _try_import_pyarrow()
    if pa is None:
        logger.warning(
            "pyarrow not installed — Parquet index skipped. "
            "Install with: pip install pyarrow"
        )
        return {"rows": 0, "columns": 0, "file_size_bytes": 0, "elapsed_ms": 0.0}

    t0 = time.perf_counter()

    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    if len(lines) < 2:
        return {"rows": 0, "columns": 0, "file_size_bytes": 0, "elapsed_ms": 0.0}

    headers = [h.strip() for h in lines[0].split(",")]
    data_lines = lines[1:]

    # Build column arrays
    col_data: Dict[str, List[str]] = {h: [] for h in headers}
    row_ids: List[int] = []
    frame_ids: List[int] = []
    byte_offsets: List[int] = []
    byte_lengths: List[int] = []

    # Calculate byte offsets within the payload for each row.
    # The header line occupies bytes [0, len(header_line)+1).
    header_line_bytes = (lines[0] + "\n").encode("utf-8")
    cursor = len(header_line_bytes)

    for row_idx, line in enumerate(data_lines):
        values = line.split(",")
        for col_idx, h in enumerate(headers):
            col_data[h].append(values[col_idx] if col_idx < len(values) else "")

        row_bytes = (line + "\n").encode("utf-8")
        byte_offsets.append(cursor)
        byte_lengths.append(len(row_bytes))

        # Map byte offset → frame index (accounting for header in frame 0)
        frame_capacity = _FRAME_PAYLOAD_BYTES
        if cursor < frame_capacity:
            frame_ids.append(0)
        else:
            frame_ids.append(1 + (cursor - frame_capacity) // frame_capacity)

        row_ids.append(row_idx)
        cursor += len(row_bytes)

    # Build PyArrow arrays with inferred types
    pa_arrays: Dict[str, Any] = {}
    for h in headers:
        raw = col_data[h]
        pa_arrays[h] = _infer_pa_array(raw, pa)

    # Append pointer columns
    pa_arrays["_vsql_row"] = pa.array(row_ids, type=pa.int64())
    pa_arrays["_vsql_frame"] = pa.array(frame_ids, type=pa.int32())
    pa_arrays["_vsql_byte_offset"] = pa.array(byte_offsets, type=pa.int64())
    pa_arrays["_vsql_byte_length"] = pa.array(byte_lengths, type=pa.int32())

    table = pa.table(pa_arrays)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        str(output_path),
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    file_size = output_path.stat().st_size if output_path.exists() else 0

    logger.info(
        "Parquet index built: %d rows, %d columns, %.1f KB in %.1f ms",
        len(data_lines),
        len(headers),
        file_size / 1024,
        elapsed_ms,
    )

    if video_path is not None:
        append_event(
            "parquet_index_build",
            float(elapsed_ms),
            db_id=db_id_from_video_path(video_path),
            bytes_in=len(csv_content.encode("utf-8")),
            bytes_out=int(file_size),
            rows=int(len(data_lines)),
            meta={
                "columns": int(len(headers)),
                "output_path": str(output_path),
            },
        )

    return {
        "rows": len(data_lines),
        "columns": len(headers),
        "file_size_bytes": file_size,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Query helper
# ---------------------------------------------------------------------------


def query_parquet_index(
    parquet_path: Path,
    columns: Optional[List[str]] = None,
    filters: Optional[Any] = None,
) -> Optional[Any]:
    """Query the Parquet index using columnar predicate pushdown.

    Args:
        parquet_path: Path to ``vsql-index.parquet``.
        columns:      List of column names to return (column pruning).
                      Pass ``None`` to return all columns.
        filters:      PyArrow-compatible filter expression or list of tuples,
                      e.g. ``[("age", ">", 30)]`` or a ``pc.field("age") > 30``
                      expression.  ``None`` returns all rows.

    Returns:
        A ``pyarrow.Table`` or ``None`` if the index does not exist / pyarrow
        is unavailable.
    """
    pa, pq = _try_import_pyarrow()
    if pa is None or not parquet_path.is_file():
        return None

    table = pq.read_table(
        str(parquet_path),
        columns=columns,
        filters=filters,
    )
    return table


# ---------------------------------------------------------------------------
# Arrow export
# ---------------------------------------------------------------------------


def export_as_arrow(csv_content: str, output_path: Path) -> Dict[str, Any]:
    """Write an Arrow IPC file from *csv_content*.

    Arrow IPC (Feather v2) is optimised for zero-copy in-memory interchange
    and is typically the fastest format to both write and read.

    Returns stats dict: rows, columns, file_size_bytes, elapsed_ms.
    """
    pa, pq = _try_import_pyarrow()
    if pa is None:
        logger.warning("pyarrow not installed — Arrow export skipped.")
        return {"rows": 0, "columns": 0, "file_size_bytes": 0, "elapsed_ms": 0.0}

    import pyarrow.ipc as ipc  # type: ignore[import-untyped]

    t0 = time.perf_counter()

    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    if len(lines) < 2:
        return {"rows": 0, "columns": 0, "file_size_bytes": 0, "elapsed_ms": 0.0}

    headers = [h.strip() for h in lines[0].split(",")]
    col_data: Dict[str, List[str]] = {h: [] for h in headers}
    for line in lines[1:]:
        values = line.split(",")
        for col_idx, h in enumerate(headers):
            col_data[h].append(values[col_idx] if col_idx < len(values) else "")

    pa_arrays = {h: _infer_pa_array(col_data[h], pa) for h in headers}
    table = pa.table(pa_arrays)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ipc.new_file(str(output_path), table.schema) as writer:
        writer.write_table(table)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    file_size = output_path.stat().st_size if output_path.exists() else 0

    return {
        "rows": len(lines) - 1,
        "columns": len(headers),
        "file_size_bytes": file_size,
        "elapsed_ms": elapsed_ms,
    }


def csv_to_arrow_table(csv_content: str) -> Optional[Any]:
    """Return a pyarrow.Table from *csv_content*, or None if pyarrow missing."""
    pa, _ = _try_import_pyarrow()
    if pa is None:
        return None

    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    if len(lines) < 2:
        return pa.table({})

    headers = [h.strip() for h in lines[0].split(",")]
    col_data: Dict[str, List[str]] = {h: [] for h in headers}
    for line in lines[1:]:
        values = line.split(",")
        for col_idx, h in enumerate(headers):
            col_data[h].append(values[col_idx] if col_idx < len(values) else "")

    return pa.table({h: _infer_pa_array(col_data[h], pa) for h in headers})


# ---------------------------------------------------------------------------
# Storage metrics helper
# ---------------------------------------------------------------------------


def compute_storage_metrics(
    csv_content: str,
    mkv_path: Optional[Path],
    parquet_path: Optional[Path],
    codec: str = "ffv1",
    compression_algorithm: str = "zstd",
    encode_time_ms: float = 0.0,
) -> Dict[str, Any]:
    """Compute storage metrics comparing the MKV to estimated columnar formats.

    Returns a dict consumed by ``VideoDB.get_storage_metrics()`` and the
    ``StorageMetrics`` GraphQL type.
    """
    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    row_count = max(0, len(lines) - 1)
    estimated_csv_bytes = len(csv_content.encode("utf-8"))

    mkv_bytes = mkv_path.stat().st_size if (mkv_path and mkv_path.is_file()) else 0
    parquet_bytes = (
        parquet_path.stat().st_size if (parquet_path and parquet_path.is_file()) else 0
    )

    # Rough Parquet estimate when sidecar doesn't exist yet (~25% of CSV size).
    estimated_parquet_bytes = (
        parquet_bytes if parquet_bytes else max(1, int(estimated_csv_bytes * 0.25))
    )

    compression_ratio = round(estimated_csv_bytes / mkv_bytes, 3) if mkv_bytes else 0.0
    parquet_vs_mkv = (
        round(parquet_bytes / mkv_bytes, 3) if (parquet_bytes and mkv_bytes) else 0.0
    )

    # Frame count (rough estimate from MKV size / frame payload)
    frame_count = max(1, mkv_bytes // _FRAME_PAYLOAD_BYTES) if mkv_bytes else 0

    return {
        "mkv_bytes": mkv_bytes,
        "parquet_index_bytes": parquet_bytes,
        "row_count": row_count,
        "frame_count": frame_count,
        "compression_ratio": compression_ratio,
        "codec": codec,
        "compression_algorithm": compression_algorithm,
        "estimated_csv_bytes": estimated_csv_bytes,
        "estimated_parquet_bytes": estimated_parquet_bytes,
        "parquet_vs_mkv_ratio": parquet_vs_mkv,
        "encode_time_ms": encode_time_ms,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _infer_pa_array(raw: List[str], pa: Any) -> Any:
    """Try integer → float → string inference for a column."""
    if not raw:
        return pa.array(raw, type=pa.string())

    # Try integer
    try:
        ints = [int(v) if v.strip() else None for v in raw]
        return pa.array(ints, type=pa.int64())
    except (ValueError, TypeError):
        pass

    # Try float
    try:
        floats = [float(v) if v.strip() else None for v in raw]
        return pa.array(floats, type=pa.float64())
    except (ValueError, TypeError):
        pass

    return pa.array(raw, type=pa.string())
