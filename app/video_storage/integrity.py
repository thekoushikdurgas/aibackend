"""Data integrity verification and repair for video storage."""

import hashlib
import shutil
from typing import Dict, Any
import numpy as np

from .exceptions import IntegrityError


class DataIntegrity:
    """Data integrity verification and repair for Video Database."""

    def __init__(self, video_db):
        self.video_db = video_db
        self.decoder = video_db.decoder
        self.encoder = video_db.encoder

    def validate_all(self) -> bool:
        """Validate complete video database integrity."""
        try:
            # Validate frame structure
            if not self._validate_frame_structure():
                return False

            # Validate header integrity
            if not self._validate_header_integrity():
                return False

            # Validate data checksum
            if not self._validate_data_checksum():
                return False

            # Validate schema consistency
            if not self._validate_schema_consistency():
                return False

            # Validate round-trip integrity
            if not self._validate_round_trip():
                return False

            return True

        except Exception:
            return False

    def _validate_frame_structure(self) -> bool:
        """Validate frame dimensions and format."""
        if not self.video_db._frames:
            return False

        for i, frame in enumerate(self.video_db._frames):
            expected_shape = (
                self.video_db.encoder.height,
                self.video_db.encoder.width,
                4,
            )
            if frame.shape != expected_shape:
                return False

            # Check alpha channel is 255
            if not np.all(frame[:, :, 3] == 255):
                return False

        return True

    def _validate_header_integrity(self) -> bool:
        """Validate frame header structure and magic bytes."""
        if not self.video_db._frames:
            return False

        try:
            header = self.decoder._extract_header_from_frame(self.video_db._frames[0])
            return header.validate()
        except Exception:
            return False

    def _validate_data_checksum(self) -> bool:
        """Validate payload checksum against sidecar manifest when present."""
        if not self.video_db._frames or not self.video_db.schema:
            return True

        try:
            from .manifest import read_manifest

            manifest = read_manifest(self.video_db.video_path)
            expected = manifest.get("payload_sha256") if manifest else None
            if not expected:
                return True  # legacy videos without manifest

            data_bytes = self.decoder.decode_frames_to_bytes(self.video_db._frames)
            actual = hashlib.sha256(data_bytes).hexdigest()
            return actual == expected

        except Exception:
            return False

    def _validate_schema_consistency(self) -> bool:
        """Validate schema consistency with data."""
        if not self.video_db.schema:
            return False

        try:
            # Get row count from data
            actual_row_count = self.decoder.count_rows_in_frames(self.video_db._frames)

            # Compare with schema row count
            return actual_row_count == self.video_db.schema.row_count

        except Exception:
            return False

    def _validate_round_trip(self) -> bool:
        """Validate complete round-trip integrity."""
        try:
            # Export current data
            original_data = self.decoder.decode_frames_to_bytes(self.video_db._frames)

            # Re-encode with same schema
            frames = self.encoder.encode_bytes_to_frames(
                original_data,
                self.video_db.schema,
                compression=self.video_db.schema.compression_enabled,
            )

            # Decode again
            round_trip_data = self.decoder.decode_frames_to_bytes(frames)

            # Compare
            return original_data == round_trip_data

        except Exception:
            return False

    def validate_frame_range(self, start_frame: int, end_frame: int) -> Dict[str, Any]:
        """Validate integrity of specific frame range."""
        if not self.video_db._frames:
            return {"valid": False, "error": "No frames available"}

        if start_frame < 0 or end_frame >= len(self.video_db._frames):
            return {"valid": False, "error": "Frame range out of bounds"}

        result: Dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "frame_count": end_frame - start_frame + 1,
        }

        try:
            # Validate each frame in range
            for i in range(start_frame, end_frame + 1):
                frame = self.video_db._frames[i]

                # Check frame shape
                expected_shape = (
                    self.video_db.encoder.height,
                    self.video_db.encoder.width,
                    4,
                )
                if frame.shape != expected_shape:
                    result["errors"].append(f"Frame {i}: Invalid shape {frame.shape}")
                    result["valid"] = False

                # Check alpha channel
                if not np.all(frame[:, :, 3] == 255):
                    result["warnings"].append(f"Frame {i}: Alpha channel not uniform")

            # Validate header if first frame is included
            if start_frame == 0:
                try:
                    header = self.decoder._extract_header_from_frame(
                        self.video_db._frames[0]
                    )
                    if not header.validate():
                        result["errors"].append("Frame 0: Invalid header")
                        result["valid"] = False
                except Exception as e:
                    result["errors"].append(f"Frame 0: Header error - {e}")
                    result["valid"] = False

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Validation error: {e}")

        return result

    def repair(self) -> bool:
        """Attempt to repair corrupted video database."""
        if not self.video_db._frames:
            return False

        try:
            # Create backup
            backup_path = self.video_db.video_path.with_suffix(".backup.mp4")
            shutil.copy2(self.video_db.video_path, backup_path)

            # Attempt repair strategies
            repaired = False

            # Strategy 1: Fix alpha channel
            if self._fix_alpha_channels():
                repaired = True

            # Strategy 2: Re-encode with current data
            if not repaired and self._reencode_from_data():
                repaired = True

            # Strategy 3: Rebuild from header if possible
            if not repaired and self._rebuild_from_header():
                repaired = True

            if repaired:
                # Validate repair
                if self.validate_all():
                    # Remove backup if repair successful
                    backup_path.unlink(missing_ok=True)
                    return True
                else:
                    # Restore backup if repair failed validation
                    shutil.copy2(backup_path, self.video_db.video_path)
                    backup_path.unlink(missing_ok=True)

            return False

        except Exception:
            return False

    def _fix_alpha_channels(self) -> bool:
        """Fix alpha channel values in all frames."""
        try:
            fixed_frames = []

            for frame in self.video_db._frames:
                fixed_frame = frame.copy()
                fixed_frame[:, :, 3] = 255
                fixed_frames.append(fixed_frame)

            # Save fixed frames
            self.video_db._save_frames(fixed_frames)
            self.video_db._frames = fixed_frames

            return True

        except Exception:
            return False

    def _reencode_from_data(self) -> bool:
        """Re-encode video from extracted data."""
        try:
            # Extract current data
            data_bytes = self.decoder.decode_frames_to_bytes(self.video_db._frames)

            if not data_bytes:
                return False

            # Re-encode with current schema
            frames = self.encoder.encode_bytes_to_frames(
                data_bytes,
                self.video_db.schema,
                compression=self.video_db.schema.compression_enabled,
            )

            # Save re-encoded frames
            self.video_db._save_frames(frames)
            self.video_db._frames = frames

            return True

        except Exception:
            return False

    def _rebuild_from_header(self) -> bool:
        """Attempt to rebuild from header information."""
        try:
            # Extract header from first frame
            header = self.decoder._extract_header_from_frame(self.video_db._frames[0])

            if not header.validate():
                return False

            # Create minimal valid frames with just header
            header_frame = self.video_db._frames[0].copy()

            # Ensure header is properly encoded
            header_bytes = header.to_bytes()
            frame_data = self.decoder._rgba_frame_to_bytes(header_frame)

            # Replace header part
            new_frame_data = header_bytes + frame_data[len(header_bytes) :]
            new_frame = self.encoder._bytes_to_rgba_frame(new_frame_data)

            # Keep only first frame (header only)
            self.video_db._save_frames([new_frame])
            self.video_db._frames = [new_frame]

            # Update schema row count to 0 (data lost)
            header.schema.row_count = 0

            return True

        except Exception:
            return False

    def get_integrity_report(self) -> Dict[str, Any]:
        """Get detailed integrity report."""
        report: Dict[str, Any] = {
            "overall_valid": False,
            "checks": {},
            "statistics": {},
            "recommendations": [],
        }

        try:
            # Overall validation
            report["overall_valid"] = self.validate_all()

            # Individual checks
            report["checks"]["frame_structure"] = self._validate_frame_structure()
            report["checks"]["header_integrity"] = self._validate_header_integrity()
            report["checks"]["data_checksum"] = self._validate_data_checksum()
            report["checks"]["schema_consistency"] = self._validate_schema_consistency()
            report["checks"]["round_trip"] = self._validate_round_trip()

            # Statistics
            if self.video_db._frames:
                report["statistics"]["frame_count"] = len(self.video_db._frames)
                report["statistics"][
                    "video_size_mb"
                ] = self.video_db.video_path.stat().st_size / (1024 * 1024)

                if self.video_db.schema:
                    report["statistics"]["row_count"] = self.video_db.schema.row_count
                    report["statistics"]["column_count"] = len(
                        self.video_db.schema.columns
                    )
                    report["statistics"][
                        "compression_enabled"
                    ] = self.video_db.schema.compression_enabled

            # Recommendations
            if not report["overall_valid"]:
                report["recommendations"].append(
                    "Run repair() to attempt fixing corruption"
                )

            if not report["checks"]["frame_structure"]:
                report["recommendations"].append(
                    "Frame structure issues detected - consider re-encoding"
                )

            if not report["checks"]["round_trip"]:
                report["recommendations"].append(
                    "Round-trip integrity failed - data may be corrupted"
                )

            if self.video_db.schema and self.video_db.schema.row_count == 0:
                report["recommendations"].append("Database appears to be empty")

        except Exception as e:
            report["error"] = str(e)
            report["recommendations"].append("Unable to complete integrity check")

        return report

    def create_checksum(self) -> str:
        """Create checksum for entire video database."""
        if not self.video_db.video_path.exists():
            raise IntegrityError("Video file does not exist")

        # Calculate file checksum
        with open(self.video_db.video_path, "rb") as f:
            file_hash = hashlib.sha256()
            while chunk := f.read(8192):
                file_hash.update(chunk)

        return file_hash.hexdigest()

    def verify_checksum(self, expected_checksum: str) -> bool:
        """Verify video database against expected checksum."""
        try:
            actual_checksum = self.create_checksum()
            return actual_checksum == expected_checksum
        except Exception:
            return False
