"""CSV import analysis and normalization helpers."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

from app.codec.format_constants import BYTES_PER_PIXEL, FRAME_HEIGHT, FRAME_WIDTH
from app.video_storage.schema import FrameHeader, VideoSchema

SUPPORTED_TYPES = {"INTEGER", "REAL", "TEXT", "BLOB"}
RESOLUTION_PRESETS = [
    (640, 360, "small preview"),
    (1280, 720, "current compatibility preset"),
    (1920, 1080, "fewer frames for larger imports"),
]


def sanitize_identifier(value: str, fallback: str = "column") -> str:
    """Return a stable GraphQL/SQL-friendly identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", (value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def unique_names(names: list[str]) -> list[str]:
    """Make a list of identifiers unique while preserving order."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for raw in names:
        base = sanitize_identifier(raw)
        next_count = seen.get(base, 0)
        seen[base] = next_count + 1
        out.append(base if next_count == 0 else f"{base}_{next_count + 1}")
    return out


def _infer_type(values: list[str]) -> tuple[str, float]:
    non_empty = [v.strip() for v in values if v is not None and v.strip() != ""]
    if not non_empty:
        return "TEXT", 0.0

    def all_parse(fn) -> bool:
        try:
            for value in non_empty:
                fn(value)
            return True
        except ValueError:
            return False

    if all_parse(lambda v: int(v, 10)) and all("." not in v for v in non_empty):
        return "INTEGER", 1.0
    if all_parse(float):
        return "REAL", 0.95
    return "TEXT", 0.85


def read_csv_rows(
    path: Path,
    *,
    delimiter: str = ",",
    quote_char: str = '"',
) -> list[list[str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(
            f, delimiter=delimiter or ",", quotechar=(quote_char or '"')[0]
        )
        return [row for row in reader if row]


def analyze_csv_path(
    path: Path,
    *,
    delimiter: str = ",",
    quote_char: str = '"',
    sample_rows: int = 100,
    compression: bool = True,
) -> dict[str, Any]:
    rows = read_csv_rows(path, delimiter=delimiter, quote_char=quote_char)
    if not rows:
        raise ValueError("CSV file is empty")

    headers = rows[0]
    sanitized = unique_names(headers)
    data_rows = rows[1:]
    sample = data_rows[: max(1, sample_rows)]
    duplicate_headers = [
        name
        for name, count in Counter([h.strip() for h in headers]).items()
        if count > 1
    ]
    warnings: list[str] = []
    if duplicate_headers:
        warnings.append(
            "Duplicate headers were found and will be renamed: "
            + ", ".join(duplicate_headers)
        )

    columns: list[dict[str, Any]] = []
    for index, (source, target) in enumerate(zip(headers, sanitized)):
        values = [row[index] if index < len(row) else "" for row in sample]
        all_values = [row[index] if index < len(row) else "" for row in data_rows]
        inferred_type, confidence = _infer_type(values)
        non_empty = [v for v in all_values if v.strip() != ""]
        unique_count = len(set(non_empty))
        empty_count = len(all_values) - len(non_empty)
        is_unique = bool(non_empty) and unique_count == len(non_empty)
        columns.append(
            {
                "index": index,
                "sourceName": source,
                "suggestedName": target,
                "inferredType": inferred_type,
                "confidence": confidence,
                "emptyCount": empty_count,
                "uniqueCount": unique_count,
                "isUniqueCandidate": is_unique,
                "sampleValues": values[:5],
            }
        )

    normalized_bytes = _rows_to_csv_bytes([sanitized] + data_rows)
    payload_bytes = (
        zlib.compress(normalized_bytes, level=9) if compression else normalized_bytes
    )
    schema = schema_from_plan(
        {
            "columns": [
                {
                    "sourceName": col["sourceName"],
                    "targetName": col["suggestedName"],
                    "dataType": col["inferredType"],
                    "include": True,
                    "nullable": col["emptyCount"] > 0,
                    "unique": col["isUniqueCandidate"],
                    "primaryKey": False,
                }
                for col in columns
            ]
        },
        headers,
        columns,
    )
    recommendations = recommend_resolutions(
        payload_bytes=len(payload_bytes),
        schema_bytes=len(json.dumps(schema.to_dict()).encode("utf-8")),
    )

    return {
        "headers": headers,
        "rowCount": len(data_rows),
        "sampleRowCount": len(sample),
        "columns": columns,
        "warnings": warnings,
        "resolutions": recommendations,
    }


def schema_from_plan(
    import_plan: dict[str, Any] | None,
    headers: list[str],
    analysis_columns: list[dict[str, Any]] | None = None,
) -> VideoSchema:
    analysis_by_source = {c.get("sourceName"): c for c in (analysis_columns or [])}
    fallback_names = unique_names(headers)
    schema = VideoSchema()
    plan_columns = (import_plan or {}).get("columns") or []
    if not plan_columns:
        plan_columns = [
            {
                "sourceName": source,
                "targetName": target,
                "dataType": analysis_by_source.get(source, {}).get(
                    "inferredType", "TEXT"
                ),
                "include": True,
                "nullable": True,
                "unique": False,
                "primaryKey": False,
            }
            for source, target in zip(headers, fallback_names)
        ]
    schema.table_name = sanitize_identifier(
        str((import_plan or {}).get("tableName") or "data"),
        fallback="data",
    )

    used: set[str] = set()
    for index, col in enumerate(plan_columns):
        if col.get("include", True) is False:
            continue
        source = str(
            col.get("sourceName") or (headers[index] if index < len(headers) else "")
        )
        target = sanitize_identifier(
            str(col.get("targetName") or source or f"column_{index+1}")
        )
        base = target
        counter = 2
        while target in used:
            target = f"{base}_{counter}"
            counter += 1
        used.add(target)

        data_type = str(col.get("dataType") or "TEXT").upper()
        if data_type not in SUPPORTED_TYPES:
            data_type = "TEXT"
        constraints = {"unique": bool(col.get("unique", False))}
        schema.add_column(
            target,
            data_type,
            nullable=bool(col.get("nullable", True)),
            primary_key=bool(col.get("primaryKey", False)),
            default=col.get("defaultValue"),
            constraints=constraints,
        )
    return schema


def normalize_csv_with_plan(
    src: Path,
    dest: Path,
    import_plan: dict[str, Any] | None,
) -> tuple[Path, VideoSchema]:
    rows = read_csv_rows(src)
    if not rows:
        raise ValueError("CSV file is empty")
    headers = rows[0]
    analysis = analyze_rows_for_schema(rows)
    schema = schema_from_plan(import_plan, headers, analysis)
    plan_columns = (import_plan or {}).get("columns") or [
        {"sourceName": source, "targetName": target, "include": True}
        for source, target in zip(headers, schema.get_column_names())
    ]
    source_indexes = {name: i for i, name in enumerate(headers)}
    output_rows = [schema.get_column_names()]
    for row in rows[1:]:
        out: list[Any] = []
        for col in plan_columns:
            if col.get("include", True) is False:
                continue
            source = str(col.get("sourceName") or "")
            default = col.get("defaultValue", "")
            idx = source_indexes.get(source)
            out.append(row[idx] if idx is not None and idx < len(row) else default)
        output_rows.append(out)
    with open(dest, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(output_rows)
    return dest, schema


def analyze_rows_for_schema(rows: list[list[str]]) -> list[dict[str, Any]]:
    headers = rows[0] if rows else []
    data_rows = rows[1:]
    sanitized = unique_names(headers)
    result = []
    for index, (source, target) in enumerate(zip(headers, sanitized)):
        values = [row[index] if index < len(row) else "" for row in data_rows]
        inferred_type, confidence = _infer_type(values[:100])
        non_empty = [v for v in values if v.strip() != ""]
        result.append(
            {
                "sourceName": source,
                "suggestedName": target,
                "inferredType": inferred_type,
                "confidence": confidence,
                "emptyCount": len(values) - len(non_empty),
                "uniqueCount": len(set(non_empty)),
                "isUniqueCandidate": bool(non_empty)
                and len(set(non_empty)) == len(non_empty),
            }
        )
    return result


def recommend_resolutions(
    payload_bytes: int, schema_bytes: int
) -> list[dict[str, Any]]:
    overhead = FrameHeader.HEADER_SIZE + (
        4 + schema_bytes if schema_bytes > FrameHeader.MAX_EMBEDDED_SCHEMA_JSON else 0
    )
    total = payload_bytes + overhead
    current_pixels = FRAME_WIDTH * FRAME_HEIGHT
    recs: list[dict[str, Any]] = []
    for width, height, label in RESOLUTION_PRESETS:
        capacity = width * height * BYTES_PER_PIXEL
        frames = max(1, math.ceil(total / capacity))
        recs.append(
            {
                "width": width,
                "height": height,
                "label": label,
                "estimatedFrames": frames,
                "estimatedPayloadBytes": total,
                "isCurrent": width * height == current_pixels,
                "reason": (
                    "Current encoder compatibility preset"
                    if width * height == current_pixels
                    else f"Estimated {frames} payload frame{'s' if frames != 1 else ''}"
                ),
            }
        )
    # Recommend smallest preset that fits in one frame; otherwise largest preset.
    recommended = next((r for r in recs if r["estimatedFrames"] == 1), recs[-1])
    for rec in recs:
        rec["isRecommended"] = (
            rec["width"] == recommended["width"]
            and rec["height"] == recommended["height"]
        )
    return recs


def _rows_to_csv_bytes(rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue().encode("utf-8")
