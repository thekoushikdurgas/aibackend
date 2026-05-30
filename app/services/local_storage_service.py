"""
Local filesystem storage with HMAC-signed URLs (replaces Supabase Storage).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _root() -> Path:
    return Path(settings.storage_root).resolve()


def _bucket_dir(bucket_name: str) -> Path:
    safe = Path(bucket_name).name
    return _root() / safe


def resolve_signed_storage_file(bucket_name: str, file_path: str) -> Optional[Path]:
    """
    Resolve ``file_path`` under ``bucket_name`` for signed GET reads.
    Returns ``None`` if the path is unsafe or not an existing file.
    """
    rel = Path(file_path)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    base = _bucket_dir(bucket_name)
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        return None
    if not target.is_file():
        return None
    return target


def ensure_buckets_exist(bucket_names: List[str]) -> None:
    for name in bucket_names:
        _bucket_dir(name).mkdir(parents=True, exist_ok=True)


def _sign_message(msg: str) -> str:
    mac = hmac.new(
        settings.storage_hmac_secret.encode(),
        msg.encode(),
        hashlib.sha256,
    ).hexdigest()
    return mac


def build_signed_token(bucket: str, object_path: str, expires_at: int) -> str:
    payload = {"b": bucket, "p": object_path, "exp": expires_at}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = _sign_message(body)
    raw = f"{body}|{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def absolute_signed_file_url(
    request_base_url: str, bucket: str, file_path: str, expires_in: int = 3600
) -> Optional[str]:
    """
    Build a same-origin absolute URL for a signed storage read (replaces GET /files/... route).
    ``request_base_url`` should be e.g. ``str(request.base_url).rstrip("/")``.
    """
    target = resolve_signed_storage_file(bucket, file_path)
    if target is None:
        return None
    exp = int(time.time()) + expires_in
    tok = build_signed_token(bucket, file_path, exp)
    prefix = settings.storage_url_prefix.rstrip("/")
    rel = f"{prefix}/{bucket}/{file_path}?token={tok}"
    root = request_base_url.rstrip("/")
    return f"{root}{rel}"


def verify_signed_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        pad = "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + pad).decode()
        body, sig = raw.rsplit("|", 1)
        if _sign_message(body) != sig:
            return None
        payload = json.loads(body)
        if not isinstance(payload, dict):
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return cast(Dict[str, Any], payload)
    except Exception as e:
        logger.debug("signed token verify failed: %s", e)
        return None


class LocalFileStorage:
    """Bucket-style file layout under ``storage_root``."""

    def __init__(self, use_admin: bool = False):
        self.use_admin = use_admin
        self.buckets = {
            "uploads": settings.storage_bucket_uploads,
            "avatars": settings.storage_bucket_avatars,
            "documents": settings.storage_bucket_documents,
        }
        ensure_buckets_exist(list(self.buckets.values()))

    def _resolve(self, bucket_type: str, file_path: str) -> tuple[str, Path]:
        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Unknown bucket type: {bucket_type}")
        rel = Path(file_path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Invalid file path")
        full = _bucket_dir(bucket_name) / rel
        return bucket_name, full

    def upload_file(
        self,
        bucket_type: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        try:
            _, full = self._resolve(bucket_type, file_path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(file_data)
            if _HAS_PIL and content_type and content_type.startswith("image/"):
                try:
                    thumb = full.with_name(full.name + ".thumb.jpg")
                    with Image.open(full) as im:
                        im.thumbnail((256, 256))
                        im.convert("RGB").save(thumb, format="JPEG", quality=85)
                except Exception as te:
                    logger.debug("thumbnail skip: %s", te)
            return file_path
        except Exception as e:
            logger.error("upload error: %s", e)
            return None

    def download_file(self, bucket_type: str, file_path: str) -> Optional[bytes]:
        try:
            _, full = self._resolve(bucket_type, file_path)
            if not full.is_file():
                return None
            return full.read_bytes()
        except Exception as e:
            logger.error("download error: %s", e)
            return None

    def get_public_url(self, bucket_type: str, file_path: str) -> Optional[str]:
        try:
            bucket_name, _ = self._resolve(bucket_type, file_path)
            prefix = settings.storage_url_prefix.rstrip("/")
            return f"{prefix}/{bucket_name}/{file_path}"
        except Exception as e:
            logger.error("public url error: %s", e)
            return None

    def create_signed_url(
        self, bucket_type: str, file_path: str, expires_in: int = 3600
    ) -> Optional[str]:
        try:
            bucket_name, _ = self._resolve(bucket_type, file_path)
            exp = int(time.time()) + expires_in
            tok = build_signed_token(bucket_name, file_path, exp)
            prefix = settings.storage_url_prefix.rstrip("/")
            return f"{prefix}/{bucket_name}/{file_path}?token={tok}"
        except Exception as e:
            logger.error("signed url error: %s", e)
            return None

    def delete_file(self, bucket_type: str, file_path: str) -> bool:
        try:
            _, full = self._resolve(bucket_type, file_path)
            if full.is_file():
                full.unlink()
            th = full.with_name(full.name + ".thumb.jpg")
            if th.is_file():
                th.unlink()
            return True
        except Exception as e:
            logger.error("delete error: %s", e)
            return False

    def list_files(
        self,
        bucket_type: str,
        folder_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            bucket_name = self.buckets.get(bucket_type)
            if not bucket_name:
                return []
            base = _bucket_dir(bucket_name)
            sub = Path(folder_path or "")
            if sub.is_absolute() or ".." in sub.parts:
                return []
            dir_path = base / sub
            if not dir_path.is_dir():
                return []
            children: List[Path] = []
            for p in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                if p.name.startswith("."):
                    continue
                # Skip auto-generated image thumbnails (e.g. photo.jpg.thumb.jpg)
                if p.is_file() and p.name.endswith(".thumb.jpg"):
                    continue
                children.append(p)
            dirs = [p for p in children if p.is_dir()]
            files_only = [p for p in children if p.is_file()]
            combined = dirs + files_only
            slice_ = combined[offset : offset + limit]
            out: List[Dict[str, Any]] = []
            for p in slice_:
                rel = str(p.relative_to(base)).replace("\\", "/")
                if p.is_dir():
                    out.append(
                        {
                            "name": p.name,
                            "path": rel,
                            "size": 0,
                            "is_directory": True,
                        }
                    )
                else:
                    out.append(
                        {
                            "name": p.name,
                            "path": rel,
                            "size": p.stat().st_size,
                            "is_directory": False,
                        }
                    )
            return out
        except Exception as e:
            logger.error("list error: %s", e)
            return []

    def move_file(self, bucket_type: str, from_path: str, to_path: str) -> bool:
        data = self.download_file(bucket_type, from_path)
        if not data:
            return False
        if not self.upload_file(bucket_type, to_path, data):
            return False
        return self.delete_file(bucket_type, from_path)

    def list_buckets(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for logical, name in self.buckets.items():
            out.append(
                {
                    "id": name,
                    "name": name,
                    "public": False,
                    "logical": logical,
                    "created_at": None,
                    "updated_at": None,
                }
            )
        return out

    def create_bucket(self, bucket_name: str, public: bool = False) -> None:
        _bucket_dir(bucket_name).mkdir(parents=True, exist_ok=True)
        marker = _bucket_dir(bucket_name) / ".bucket_meta.json"
        marker.write_text(json.dumps({"public": public}), encoding="utf-8")

    def delete_bucket(self, bucket_name: str) -> None:
        p = _bucket_dir(bucket_name)
        from app.utils.filesystem import safe_rmtree

        safe_rmtree(p)


def get_local_file_storage(use_admin: bool = False) -> LocalFileStorage:
    return LocalFileStorage(use_admin=use_admin)
