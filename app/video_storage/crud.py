"""CRUD operations for video storage."""

import csv
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from .schema import VideoSchema
from .exceptions import VideoStorageError


class VideoCRUD:
    """CRUD operations for Video Database."""

    def __init__(self, video_db):
        self.video_db = video_db
        self.encoder = video_db.encoder
        self.decoder = video_db.decoder

    def insert_row(self, row_data: Dict[str, Any]) -> int:
        """Insert a single row into the video database."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Validate row data against schema
        validated_row = self._validate_row_data(row_data)
        self._validate_unique_constraints([validated_row])

        # Get current data
        current_data = self.video_db.export_to_bytes()
        current_csv = current_data.decode("utf-8")

        # Parse current CSV
        lines = current_csv.strip().split("\n")
        if not lines:
            raise VideoStorageError("Cannot insert into empty database")

        header = lines[0]
        data_rows = lines[1:] if len(lines) > 1 else []

        # Convert row to CSV format
        new_row_values = []
        for col in self.video_db.schema.columns:
            value = validated_row.get(col.name, "")
            new_row_values.append(self._format_value(value, col.data_type))

        new_row_csv = ",".join(new_row_values)

        # Rebuild CSV with new row
        new_csv = "\n".join([header] + data_rows + [new_row_csv])

        # Re-encode with updated data
        new_data_bytes = new_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)

        # Update row count
        self.video_db.schema.row_count += 1

        return self.video_db.schema.row_count

    def insert_rows(self, rows_data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows into the video database."""
        if not rows_data:
            return 0

        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Validate all rows
        validated_rows = [self._validate_row_data(row) for row in rows_data]
        self._validate_unique_constraints(validated_rows)

        # Get current data
        current_data = self.video_db.export_to_bytes()
        current_csv = current_data.decode("utf-8")

        # Parse current CSV
        lines = current_csv.strip().split("\n")
        if not lines:
            raise VideoStorageError("Cannot insert into empty database")

        header = lines[0]
        data_rows = lines[1:] if len(lines) > 1 else []

        # Convert new rows to CSV format
        new_rows_csv = []
        for row in validated_rows:
            row_values = []
            for col in self.video_db.schema.columns:
                value = row.get(col.name, "")
                row_values.append(self._format_value(value, col.data_type))
            new_rows_csv.append(",".join(row_values))

        # Rebuild CSV with new rows
        new_csv = "\n".join([header] + data_rows + new_rows_csv)

        # Re-encode with updated data
        new_data_bytes = new_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)

        # Update row count
        self.video_db.schema.row_count += len(validated_rows)

        return self.video_db.schema.row_count

    @staticmethod
    def _normalize_csv_reader_dict(row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strip CSV header keys so DictReader rows align with schema column names."""
        out: Dict[str, Any] = {}
        for k, v in row_data.items():
            if k is None:
                continue
            nk = k.strip()
            if nk == "":
                continue
            out[nk] = v
        return out

    def _csv_row_to_schema_dict(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map a CSV DictReader row to every schema column (missing keys -> None)."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")
        norm = self._normalize_csv_reader_dict(row_data)
        return {col.name: norm.get(col.name) for col in self.video_db.schema.columns}

    def upsert_rows(self, rows_data: List[Dict[str, Any]]) -> int:
        """Merge rows into the table by unique / primary key; insert when no row matches.

        Incoming CSV rows that match an existing row on all non-empty unique-key
        fields replace that row; otherwise they are appended. Used for append imports.
        """
        if not rows_data:
            return self.count_rows()

        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        unique_cols = self._unique_column_names()
        existing: List[Dict[str, Any]] = [dict(r) for r in self.select_all()]

        for row_raw in rows_data:
            partial = self._csv_row_to_schema_dict(row_raw)
            idx: Optional[int] = None
            if unique_cols:
                idx = self._find_upsert_row_index(existing, partial, unique_cols)
            if idx is not None:
                merged = self._merge_row_for_upsert(existing[idx], partial)
                existing[idx] = self._validate_row_data(
                    merged, sparse_upsert_insert=True
                )
            else:
                existing.append(
                    self._validate_row_data(partial, sparse_upsert_insert=True)
                )

        if unique_cols:
            existing = self._dedupe_rows_by_unique_columns(existing, unique_cols)

        self._validate_unique_constraints(existing, rows_replace_entire_table=True)

        header = ",".join(self.video_db.schema.get_column_names())
        data_lines: List[str] = []
        for erow in existing:
            row_values = []
            for col in self.video_db.schema.columns:
                value = erow.get(col.name, "")
                row_values.append(self._format_value(value, col.data_type))
            data_lines.append(",".join(row_values))

        new_csv = "\n".join([header] + data_lines) if data_lines else header
        new_data_bytes = new_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)
        self.video_db.schema.row_count = len(existing)
        return len(existing)

    def update_row(self, row_index: int, updates: Dict[str, Any]) -> bool:
        """Update a specific row by index."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Get current data
        current_data = self.video_db.export_to_bytes()
        current_csv = current_data.decode("utf-8")

        # Parse current CSV
        lines = current_csv.strip().split("\n")
        if len(lines) <= 1:
            raise VideoStorageError("No data rows to update")

        header = lines[0]
        data_rows = lines[1:]

        if row_index < 0 or row_index >= len(data_rows):
            raise VideoStorageError(f"Row index {row_index} out of range")
        target_row_values = data_rows[row_index].split(",")

        # Apply updates
        proposed_row = {}
        for i, col in enumerate(self.video_db.schema.columns):
            proposed_row[col.name] = (
                target_row_values[i] if i < len(target_row_values) else ""
            )
        for col_name, new_value in updates.items():
            col_index = self._get_column_index(col_name)
            if col_index is not None:
                col_def = self.video_db.schema.columns[col_index]
                formatted_value = self._format_value(new_value, col_def.data_type)
                target_row_values[col_index] = formatted_value
                proposed_row[col_name] = formatted_value
        self._validate_unique_constraints([proposed_row], exclude_row_index=row_index)

        # Rebuild CSV with updated row
        data_rows[row_index] = ",".join(target_row_values)
        new_csv = "\n".join([header] + data_rows)

        # Re-encode with updated data
        new_data_bytes = new_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)

        return True

    def delete_row(self, row_index: int) -> bool:
        """Delete a specific row by index."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Get current data
        current_data = self.video_db.export_to_bytes()
        current_csv = current_data.decode("utf-8")

        # Parse current CSV
        lines = current_csv.strip().split("\n")
        if len(lines) <= 1:
            raise VideoStorageError("No data rows to delete")

        header = lines[0]
        data_rows = lines[1:]

        if row_index < 0 or row_index >= len(data_rows):
            raise VideoStorageError(f"Row index {row_index} out of range")
        del data_rows[row_index]

        # Rebuild CSV without deleted row
        new_csv = "\n".join([header] + data_rows) if data_rows else header

        # Re-encode with updated data
        new_data_bytes = new_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)

        # Update row count
        self.video_db.schema.row_count -= 1

        return True

    def delete_rows(self, row_indices: List[int]) -> int:
        """Delete multiple rows by indices."""
        if not row_indices:
            return 0

        # Sort indices in descending order to avoid index shifting
        sorted_indices = sorted(set(row_indices), reverse=True)

        deleted_count = 0
        for row_index in sorted_indices:
            try:
                if self.delete_row(row_index):
                    deleted_count += 1
            except VideoStorageError:
                # Skip invalid indices
                continue

        return deleted_count

    def select_rows(
        self,
        start: int = 0,
        limit: Optional[int] = None,
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Select rows with optional column filtering."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Get current data
        current_data = self.video_db.export_to_bytes()
        current_csv = current_data.decode("utf-8")

        # Parse current CSV
        lines = current_csv.strip().split("\n")
        if len(lines) <= 1:
            return []

        data_rows = lines[1:]

        # Apply row range
        end = None if limit is None else start + limit
        selected_rows = data_rows[start:end]

        # Parse rows
        result = []
        for row_str in selected_rows:
            row_values = row_str.split(",")
            row_dict = {}

            for i, col in enumerate(self.video_db.schema.columns):
                if i < len(row_values):
                    if columns is None or col.name in columns:
                        row_dict[col.name] = self._parse_value(
                            row_values[i], col.data_type
                        )

            result.append(row_dict)

        return result

    def select_all(self) -> List[Dict[str, Any]]:
        """Select all rows."""
        return self.select_rows()

    def count_rows(self) -> int:
        """Count total rows."""
        return self.video_db.schema.row_count if self.video_db.schema else 0

    def clear_all_data(self) -> None:
        """Clear all data while preserving schema."""
        if not self.video_db.schema:
            raise VideoStorageError("No schema defined")

        # Create empty CSV with just header
        header = ",".join(self.video_db.schema.get_column_names())
        empty_csv = header

        # Re-encode with empty data
        new_data_bytes = empty_csv.encode("utf-8")
        self._reencode_data(new_data_bytes)

        # Update row count
        self.video_db.schema.row_count = 0

    def bulk_import_csv(self, csv_path: Union[str, Path], append: bool = False) -> int:
        """Bulk import from CSV file."""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise VideoStorageError(f"CSV file not found: {csv_path}")

        # Read CSV file
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return 0

        # If not appending and schema exists, clear current data
        if not append and self.video_db.schema:
            self.clear_all_data()

        # If no schema, create from CSV
        if not self.video_db.schema:
            # Create schema from CSV header
            schema = VideoSchema()
            schema.infer_from_csv_header(list(rows[0].keys()))

            # Infer types from sample data
            sample_data = [list(row.values()) for row in rows[:100]]
            schema.infer_types_from_sample(sample_data)

            # Set schema and re-create database
            self.video_db.schema = schema
            self.video_db.create_from_csv(csv_path, overwrite=True)
            return len(rows)

        # Append: merge on unique / primary key columns (upsert); replace: insert fresh rows
        if append:
            return self.upsert_rows(rows)
        return self.insert_rows(rows)

    def _validate_row_data(
        self,
        row_data: Dict[str, Any],
        *,
        sparse_upsert_insert: bool = False,
    ) -> Dict[str, Any]:
        """Validate row data against schema.

        When ``sparse_upsert_insert`` is True (append ``upsert_rows`` only: merged or
        new row), NOT NULL columns still empty after merge/default get CSV-friendly
        fills: ``TEXT`` → ``""``, ``INTEGER`` → ``0``, ``REAL`` → ``0.0`` (after
        ``col.default`` if set). Non-empty cells from merge are unchanged.
        """
        validated = {}

        for col in self.video_db.schema.columns:
            value = row_data.get(col.name)

            if (value is None or value == "") and col.default is not None:
                value = col.default

            if sparse_upsert_insert and not col.primary_key and not col.nullable:
                if col.data_type == "TEXT" and value is None:
                    value = ""
                elif col.data_type == "INTEGER":
                    if value is None or (
                        isinstance(value, str) and value.strip() == ""
                    ):
                        value = 0
                elif col.data_type == "REAL":
                    if value is None or (
                        isinstance(value, str) and value.strip() == ""
                    ):
                        value = 0.0

            # Check required fields
            if not col.primary_key and not col.nullable:
                if value is None:
                    raise VideoStorageError(
                        f"Required column '{col.name}' is null or empty"
                    )
                if value == "" and (
                    not sparse_upsert_insert or col.data_type != "TEXT"
                ):
                    raise VideoStorageError(
                        f"Required column '{col.name}' is null or empty"
                    )

            # Type validation
            if value is not None and value != "":
                try:
                    validated[col.name] = self._validate_value_type(
                        value, col.data_type
                    )
                except ValueError as e:
                    raise VideoStorageError(
                        f"Type validation failed for column '{col.name}': {e}"
                    )
            else:
                validated[col.name] = value

        return validated

    def _unique_column_names(self) -> List[str]:
        if not self.video_db.schema:
            return []
        return [
            col.name
            for col in self.video_db.schema.columns
            if col.primary_key or (col.constraints or {}).get("unique")
        ]

    @staticmethod
    def _unique_cell_key(raw: Any) -> str:
        """Normalize a cell for unique-column checks (None / blank -> '')."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw.strip()
        return str(raw).strip()

    @staticmethod
    def _unique_match_key(col_name: str, raw: Any) -> str:
        """Normalize a unique cell for upsert *matching* only (not stored values)."""
        s = VideoCRUD._unique_cell_key(raw)
        if not s:
            return ""
        cl = col_name.lower()
        if "linkedin" in cl and "url" in cl:
            u = s.lower()
            if u.startswith("http://"):
                u = u[7:]
            elif u.startswith("https://"):
                u = u[8:]
            if u.startswith("www."):
                u = u[4:]
            return u.rstrip("/")
        if "contact_id" in cl or (cl.endswith("_id") and "apollo" in cl):
            try:
                f = float(s.replace(",", ""))
                if abs(f - round(f)) < 1e-9:
                    return str(int(round(f)))
            except ValueError:
                pass
            return s
        return s

    @staticmethod
    def _overlay_non_empty_wins(
        base: Dict[str, Any], over: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Later row wins for fields that are non-empty in `over` (None/blank do not clear)."""
        out = dict(base)
        for k, v in over.items():
            if v is None:
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            out[k] = v
        return out

    def _dedupe_rows_by_unique_columns(
        self, rows: List[Dict[str, Any]], unique_cols: List[str]
    ) -> List[Dict[str, Any]]:
        """Collapse rows that share the same non-empty value for any unique column (CSV batch / bad data)."""
        if len(rows) < 2 or not unique_cols:
            return rows
        out = list(rows)
        for col in unique_cols:
            buckets: dict[str, List[int]] = {}
            for i, row in enumerate(out):
                v = self._unique_cell_key(row.get(col))
                if not v:
                    continue
                buckets.setdefault(v, []).append(i)
            to_remove: set[int] = set()
            replacements: dict[int, Dict[str, Any]] = {}
            for _key, idxs in buckets.items():
                if len(idxs) < 2:
                    continue
                idxs_sorted = sorted(idxs)
                keep = idxs_sorted[0]
                merged = dict(out[keep])
                for j in idxs_sorted[1:]:
                    merged = self._overlay_non_empty_wins(merged, out[j])
                    to_remove.add(j)
                replacements[keep] = merged
            if not to_remove:
                continue
            new_out: List[Dict[str, Any]] = []
            for i, row in enumerate(out):
                if i in to_remove:
                    continue
                if i in replacements:
                    new_out.append(replacements[i])
                else:
                    new_out.append(row)
            out = new_out
        return out

    def _find_upsert_row_index(
        self,
        existing_rows: List[Dict[str, Any]],
        incoming: Dict[str, Any],
        unique_cols: List[str],
    ) -> Optional[int]:
        for idx, row in enumerate(existing_rows):
            if self._incoming_matches_row_on_unique_keys(row, incoming, unique_cols):
                return idx
        for idx, row in enumerate(existing_rows):
            if self._incoming_matches_any_unique_key(row, incoming, unique_cols):
                return idx
        return None

    @staticmethod
    def _merge_row_for_upsert(
        existing_row: Dict[str, Any], incoming_row: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge incoming into existing without clearing fields with empty/None CSV cells."""
        merged = dict(existing_row)
        for key, value in incoming_row.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            merged[key] = value
        return merged

    @staticmethod
    def _incoming_matches_any_unique_key(
        existing: Dict[str, Any],
        incoming: Dict[str, Any],
        unique_cols: List[str],
    ) -> bool:
        """True if any non-empty incoming unique field equals the same field in existing."""
        for col in unique_cols:
            inc = VideoCRUD._unique_match_key(col, incoming.get(col))
            if not inc:
                continue
            ex = VideoCRUD._unique_match_key(col, existing.get(col))
            if ex == inc:
                return True
        return False

    @staticmethod
    def _incoming_matches_row_on_unique_keys(
        existing: Dict[str, Any],
        incoming: Dict[str, Any],
        unique_cols: List[str],
    ) -> bool:
        """True when every non-empty incoming unique-field equals the same field in existing."""
        has_key = False
        for col in unique_cols:
            inc = VideoCRUD._unique_match_key(col, incoming.get(col))
            if not inc:
                continue
            has_key = True
            ex = VideoCRUD._unique_match_key(col, existing.get(col))
            if ex != inc:
                return False
        return has_key

    def _validate_unique_constraints(
        self,
        new_rows: List[Dict[str, Any]],
        exclude_row_index: Optional[int] = None,
        *,
        rows_replace_entire_table: bool = False,
    ) -> None:
        """Reject duplicates for columns marked as unique in schema constraints."""
        if not self.video_db.schema:
            return
        unique_cols = self._unique_column_names()
        if not unique_cols:
            return

        if rows_replace_entire_table:
            existing: List[Dict[str, Any]] = []
        else:
            existing = self.select_all()
            if exclude_row_index is not None:
                existing = [
                    row for idx, row in enumerate(existing) if idx != exclude_row_index
                ]
        for col_name in unique_cols:
            seen = {
                self._unique_cell_key(row.get(col_name))
                for row in existing
                if self._unique_cell_key(row.get(col_name)) != ""
            }
            batch_seen: set[str] = set()
            for row in new_rows:
                value = self._unique_cell_key(row.get(col_name))
                if not value:
                    continue
                if value in seen or value in batch_seen:
                    raise VideoStorageError(
                        f"Unique column '{col_name}' already contains value '{value}'"
                    )
                batch_seen.add(value)

    def _validate_value_type(self, value: Any, data_type: str) -> Any:
        """Validate and convert value to correct type.

        INTEGER/REAL columns may hold non-numeric strings after merge or CSV quirks;
        those values are kept as strings (same as ``_parse_value`` / ``_format_value``).
        """
        if data_type == "INTEGER":
            try:
                return int(float(str(value).strip()))
            except (ValueError, TypeError, OverflowError):
                return str(value)
        elif data_type == "REAL":
            try:
                return float(str(value).strip())
            except (ValueError, TypeError, OverflowError):
                return str(value)
        elif data_type == "TEXT":
            return str(value)
        elif data_type == "BLOB":
            if isinstance(value, str):
                return value.encode("utf-8")
            return value
        else:
            return value

    def _format_value(self, value: Any, data_type: str) -> str:
        """Format value for CSV storage."""
        if value is None or value == "":
            return ""

        if data_type == "INTEGER":
            try:
                return str(int(float(str(value).strip())))
            except (ValueError, TypeError, OverflowError):
                return self._format_text_cell_for_csv(str(value))
        elif data_type == "REAL":
            try:
                return str(float(str(value).strip()))
            except (ValueError, TypeError, OverflowError):
                return self._format_text_cell_for_csv(str(value))
        else:
            return self._format_text_cell_for_csv(str(value))

    @staticmethod
    def _format_text_cell_for_csv(str_value: str) -> str:
        """Escape a string for one CSV field (TEXT / fallback for bad numeric cells)."""
        if "," in str_value or '"' in str_value or "\n" in str_value:
            return '"' + str_value.replace('"', '""') + '"'
        return str_value

    def _parse_value(self, value: str, data_type: str) -> Any:
        """Parse value from CSV storage."""
        if value == "":
            return None

        if data_type == "INTEGER":
            try:
                return int(float(value.strip()))
            except ValueError:
                return value
        elif data_type == "REAL":
            try:
                return float(value.strip())
            except ValueError:
                return value
        else:
            return value

    def _get_column_index(self, column_name: str) -> Optional[int]:
        """Get column index by name."""
        for i, col in enumerate(self.video_db.schema.columns):
            if col.name == column_name:
                return i
        return None

    def _reencode_data(self, new_data_bytes: bytes) -> None:
        """Re-encode video database with new data."""
        frames = self.encoder.encode_bytes_to_frames(
            new_data_bytes,
            self.video_db.schema,
            compression=self.video_db.schema.compression_enabled,
        )

        # Save updated frames
        self.video_db._save_frames(frames)
        self.video_db._frames = frames
