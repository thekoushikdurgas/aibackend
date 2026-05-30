"""Video Database Engine - Core interface for video-based storage."""

import hashlib
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import numpy as np

from .schema import VideoSchema
from .encoder import DataEncoder
from .decoder import DataDecoder
from .crud import VideoCRUD
from .query import VideoQuery
from .integrity import DataIntegrity
from .manifest import read_manifest, remove_manifest, write_manifest
from .exceptions import VideoStorageError, VideoDecodingError, VideoEncodingError
from .parquet_index import (
    build_parquet_index,
    export_as_arrow,
    compute_storage_metrics,
)
from ..codec.video import encode_rgba_frames_to_mp4, decode_mp4_to_rgba_frames
from ..services.perf_event_log import (
    append_event,
    db_id_from_video_path,
    timed_operation,
)

logger = logging.getLogger(__name__)


class VideoDB:
    """Main Video Database interface."""

    def __init__(
        self,
        video_path: Union[str, Path],
        mode: str = "rw",
        *,
        encode_fps: int = 30,
    ):
        """
        Initialize Video Database.

        Args:
            video_path: Path to video file
            mode: Access mode ('r' read-only, 'w' write-only, 'rw' read-write)
            encode_fps: FPS used when writing MKV/FFV1 (must match decode assumptions for time mapping)
        """
        self.video_path = Path(video_path)
        self.mode = mode
        self.encode_fps = max(1, int(encode_fps))
        self.schema: Optional[VideoSchema] = None
        self._frames: Optional[List[np.ndarray]] = None
        self._loaded = False
        self._last_encode_ms: float = 0.0

        # Initialize components
        self.encoder = DataEncoder()
        self.decoder = DataDecoder()
        self.crud = VideoCRUD(self)
        self.query = VideoQuery(self)
        self.integrity = DataIntegrity(self)

        # Load existing video if it exists
        if self.video_path.exists() and "r" in mode:
            self._load_video()

    def _load_video(self) -> None:
        """Load existing video file."""
        db_id = db_id_from_video_path(self.video_path)
        vin = int(self.video_path.stat().st_size) if self.video_path.exists() else 0
        with timed_operation("video_decode", db_id=db_id, bytes_in=vin) as extra:
            try:
                self._frames = decode_mp4_to_rgba_frames(self.video_path)
                if self._frames:
                    self.schema = self.decoder.get_schema_from_frames(self._frames)
                manifest = read_manifest(self.video_path)
                expected = manifest.get("payload_sha256") if manifest else None
                if expected and self._frames:
                    payload = self.decoder.decode_frames_to_bytes(self._frames)
                    digest = hashlib.sha256(payload).hexdigest()
                    if digest != expected:
                        raise VideoStorageError(
                            "Manifest checksum mismatch: decoded payload does not match "
                            f"stored hash (expected {expected[:16]}…)"
                        )
                self._loaded = True
                if self._frames:
                    extra["frame_count"] = int(len(self._frames))
            except (VideoDecodingError, VideoEncodingError):
                raise
            except VideoStorageError:
                raise
            except Exception as e:
                raise VideoStorageError(f"Failed to load video: {e}") from e

    def create_from_csv(
        self,
        csv_path: Union[str, Path],
        schema: Optional[VideoSchema] = None,
        compression: bool = True,
        overwrite: bool = False,
    ) -> None:
        """Create new video database from CSV file."""
        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        if self.video_path.exists() and not overwrite:
            raise VideoStorageError(f"Video file already exists: {self.video_path}")

        # Encode CSV to frames
        frames, schema = self.encoder.encode_csv_to_frames(
            csv_path, schema=schema, compression=compression
        )

        # Save frames to video
        self._save_frames(frames)

        # Update internal state
        self._frames = frames
        self.schema = schema
        self._loaded = True

    def create_from_json(
        self,
        json_data: Union[str, List[dict], dict],
        compression: bool = True,
        overwrite: bool = False,
    ) -> None:
        """Create new video database from JSON data."""
        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        if self.video_path.exists() and not overwrite:
            raise VideoStorageError(f"Video file already exists: {self.video_path}")

        # Encode JSON to frames
        frames, schema = self.encoder.encode_json_to_frames(
            json_data, compression=compression
        )

        # Save frames to video
        self._save_frames(frames)

        # Update internal state
        self._frames = frames
        self.schema = schema
        self._loaded = True

    def create_from_bytes(
        self,
        data: bytes,
        schema: VideoSchema,
        compression: bool = True,
        overwrite: bool = False,
    ) -> None:
        """Create new video database from raw bytes."""
        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        if self.video_path.exists() and not overwrite:
            raise VideoStorageError(f"Video file already exists: {self.video_path}")

        # Encode bytes to frames
        frames = self.encoder.encode_bytes_to_frames(
            data, schema, compression=compression
        )

        # Save frames to video
        self._save_frames(frames)

        # Update internal state
        self._frames = frames
        self.schema = schema
        self._loaded = True

    def _save_frames(
        self,
        frames: List[np.ndarray],
        parquet_index_path: Optional[Path] = None,
    ) -> float:
        """Save frames to video (atomic write + round-trip check + manifest + Parquet index).

        Args:
            frames: RGBA frame list to encode.
            parquet_index_path: If provided, write a Parquet analytics sidecar here.
                                Defaults to ``video_path.with_suffix('').parent /
                                vsql-index.parquet`` when not specified.

        Returns:
            Encode time in milliseconds.
        """
        if "w" not in self.mode:
            raise VideoStorageError("Write access required")
        try:
            self.video_path.parent.mkdir(parents=True, exist_ok=True)
            remove_manifest(self.video_path)
            original_payload = self.decoder.decode_frames_to_bytes(frames)
            payload_sha256 = hashlib.sha256(original_payload).hexdigest()

            t0 = time.perf_counter()
            encode_rgba_frames_to_mp4(frames, self.video_path, fps=self.encode_fps)
            encode_ms = (time.perf_counter() - t0) * 1000

            t_round = time.perf_counter()
            round_frames = decode_mp4_to_rgba_frames(self.video_path)
            round_trip_ms = (time.perf_counter() - t_round) * 1000
            round_payload = self.decoder.decode_frames_to_bytes(round_frames)
            if round_payload != original_payload:
                raise VideoStorageError(
                    "Encode/decode round-trip failed: logical payload bytes differ after MKV write"
                )

            video_size = self.video_path.stat().st_size
            write_manifest(
                self.video_path,
                frame_count=len(frames),
                fps=self.encode_fps,
                payload_sha256=payload_sha256,
                video_size_bytes=video_size,
            )

            # Auto-build Parquet analytics sidecar alongside the MKV.
            idx_path = parquet_index_path or (
                self.video_path.parent / "vsql-index.parquet"
            )
            try:
                csv_content = self.decoder.decode_frames_to_csv(frames)
                build_parquet_index(csv_content, idx_path, video_path=self.video_path)
            except Exception as exc:
                logger.warning("Parquet index build skipped: %s", exc)

            self._last_encode_ms = encode_ms
            append_event(
                "mkv_write",
                encode_ms,
                db_id=db_id_from_video_path(self.video_path),
                bytes_out=int(video_size),
                rows=len(frames),
                meta={
                    "frame_count": int(len(frames)),
                    "round_trip_decode_ms": float(round_trip_ms),
                },
            )
            return encode_ms

        except (VideoEncodingError, VideoDecodingError):
            raise
        except VideoStorageError:
            raise
        except Exception as e:
            raise VideoStorageError(f"Failed to save video: {e}") from e

    def get_schema(self) -> Optional[VideoSchema]:
        """Get database schema."""
        return self.schema

    def get_row_count(self) -> int:
        """Get total number of rows."""
        return self.schema.row_count if self.schema else 0

    def get_column_names(self) -> List[str]:
        """Get column names."""
        return self.schema.get_column_names() if self.schema else []

    def export_to_csv(self, output_path: Union[str, Path]) -> None:
        """Export video database to CSV file."""
        if not self._loaded:
            self._load_video()

        if not self._frames:
            raise VideoStorageError("No data to export")

        self.decoder.decode_frames_to_csv(self._frames, output_path)

    def export_to_json(self, output_path: Union[str, Path]) -> None:
        """Export video database to JSON file."""
        if not self._loaded:
            self._load_video()

        if not self._frames:
            raise VideoStorageError("No data to export")

        self.decoder.decode_frames_to_json(self._frames, output_path)

    def export_to_bytes(self) -> bytes:
        """Export video database to raw bytes."""
        if not self._loaded:
            self._load_video()

        if not self._frames:
            raise VideoStorageError("No data to export")

        return self.decoder.decode_frames_to_bytes(self._frames)

    def get_dataframe(self):
        """Get data as pandas DataFrame."""
        if not self._loaded:
            self._load_video()

        if not self._frames:
            raise VideoStorageError("No data available")

        return self.decoder.decode_frames_to_dataframe(self._frames)

    def add_column(self, name: str, data_type: str, default_value: Any = None) -> None:
        """Add a new column to the schema."""
        if not self.schema:
            raise VideoStorageError("No schema loaded")

        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        # Add column to schema
        self.schema.add_column(name, data_type, default=default_value)

        # Re-encode with new schema
        self._reencode_with_updated_schema()

    def remove_column(self, name: str) -> None:
        """Remove a column from the schema."""
        if not self.schema:
            raise VideoStorageError("No schema loaded")

        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        # Remove column from schema
        self.schema.remove_column(name)

        # Re-encode with updated schema
        self._reencode_with_updated_schema()

    def _reencode_with_updated_schema(self) -> None:
        """Re-encode data with updated schema."""
        if not self._frames:
            return

        # Export current data
        current_data = self.export_to_bytes()

        # Re-encode with new schema
        if self.schema is None:
            raise VideoStorageError("No schema defined for re-encoding")

        frames = self.encoder.encode_bytes_to_frames(
            current_data, self.schema, compression=self.schema.compression_enabled
        )

        # Save updated frames
        self._save_frames(frames)
        self._frames = frames

    def validate_integrity(self) -> bool:
        """Validate video database integrity."""
        if not self._loaded:
            self._load_video()

        return self.integrity.validate_all()

    def repair_database(self) -> bool:
        """Attempt to repair corrupted video database."""
        if "w" not in self.mode:
            raise VideoStorageError("Write access required")

        return self.integrity.repair()

    def get_info(self) -> Dict[str, Any]:
        """Get database information."""
        info: Dict[str, Any] = {
            "video_path": str(self.video_path),
            "video_size": (
                self.video_path.stat().st_size if self.video_path.exists() else 0
            ),
            "frame_count": len(self._frames) if self._frames else 0,
            "loaded": self._loaded,
            "mode": self.mode,
        }

        if self.schema:
            info.update(
                {
                    "schema_version": self.schema.version,
                    "table_name": self.schema.table_name,
                    "row_count": self.schema.row_count,
                    "column_count": len(self.schema.columns),
                    "compression_enabled": self.schema.compression_enabled,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.data_type,
                            "nullable": col.nullable,
                            "primary_key": col.primary_key,
                            "default": col.default,
                            "constraints": col.constraints or {},
                        }
                        for col in self.schema.columns
                    ],
                    "created_at": self.schema.created_at,
                    "updated_at": self.schema.updated_at,
                }
            )

        return info

    # ------------------------------------------------------------------
    # Storage metrics & multi-format export
    # ------------------------------------------------------------------

    def get_storage_metrics(
        self,
        parquet_index_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Return a dict of storage metrics for the MKV + Parquet sidecar.

        Compares the on-disk MKV size against the Parquet index and CSV
        equivalents so the frontend can show format comparison stats.
        """
        if not self._loaded and self.video_path.exists():
            self._load_video()

        idx_path = parquet_index_path or (self.video_path.parent / "vsql-index.parquet")
        csv_content = ""
        if self._frames:
            try:
                csv_content = self.decoder.decode_frames_to_csv(self._frames)
            except Exception:
                pass

        compression_algo = "zstd"
        if self.schema and not self.schema.compression_enabled:
            compression_algo = "none"

        return compute_storage_metrics(
            csv_content=csv_content,
            mkv_path=self.video_path,
            parquet_path=idx_path if idx_path.is_file() else None,
            codec="ffv1",
            compression_algorithm=compression_algo,
            encode_time_ms=self._last_encode_ms,
        )

    def export_parquet(self, output_path: Path) -> Dict[str, Any]:
        """Write a standalone Parquet export file and return stats."""
        if not self._loaded and self.video_path.exists():
            self._load_video()
        if not self._frames:
            raise VideoStorageError("No data to export")
        csv_content = self.decoder.decode_frames_to_csv(self._frames)
        return build_parquet_index(
            csv_content,
            output_path,
            video_path=self.video_path,
        )

    def export_arrow(self, output_path: Path) -> Dict[str, Any]:
        """Write a standalone Arrow IPC export file and return stats."""
        if not self._loaded and self.video_path.exists():
            self._load_video()
        if not self._frames:
            raise VideoStorageError("No data to export")
        csv_content = self.decoder.decode_frames_to_csv(self._frames)
        return export_as_arrow(csv_content, output_path)

    def close(self) -> None:
        """Close video database."""
        # Clear frames from memory
        self._frames = None
        self._loaded = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __len__(self) -> int:
        """Get number of rows."""
        return self.get_row_count()

    def __contains__(self, column_name: str) -> bool:
        """Check if column exists."""
        return column_name in self.get_column_names()


class VideoDBPool:
    """Connection pool for Video Database instances."""

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._connections: Dict[str, VideoDB] = {}
        self._usage_count: Dict[str, int] = {}

    def get_connection(self, video_path: Union[str, Path], mode: str = "rw") -> VideoDB:
        """Get or create a VideoDB connection."""
        path_str = str(video_path)

        if path_str in self._connections:
            self._usage_count[path_str] += 1
            return self._connections[path_str]

        if len(self._connections) >= self.max_connections:
            # Remove least used connection
            least_used = min(self._usage_count.items(), key=lambda x: x[1])
            del self._connections[least_used[0]]
            del self._usage_count[least_used[0]]

        # Create new connection
        conn = VideoDB(video_path, mode)
        self._connections[path_str] = conn
        self._usage_count[path_str] = 1

        return conn

    def close_all(self) -> None:
        """Close all connections."""
        for conn in self._connections.values():
            conn.close()

        self._connections.clear()
        self._usage_count.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()
