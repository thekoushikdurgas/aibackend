"""Provision default cloud storage layout for a new user (uploads bucket)."""

from __future__ import annotations

import logging

from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

DEFAULT_FOLDERS = ("Documents", "Pictures", "Downloads", "Music", "Videos")

WELCOME_CONTENT = """# Welcome to DurgasOS

Your personal cloud storage is ready. Files you upload from the Files app appear here.

| Folder | Purpose |
|--------|---------|
| Documents | Docs, PDFs, spreadsheets |
| Pictures | Images |
| Downloads | Downloaded files |
| Music | Audio files |
| Videos | Video files |
"""


def provision_user_storage(user_id: str) -> None:
    """Create Welcome.md and default folders under ``uploads/{user_id}/`` (idempotent-ish)."""
    if not user_id or not user_id.strip():
        logger.warning("provision_user_storage: empty user_id")
        return
    uid = user_id.strip()
    try:
        storage = get_storage_service(use_admin=False)
        welcome_path = f"{uid}/Welcome.md"
        ok = storage.upload_file(
            "uploads",
            welcome_path,
            WELCOME_CONTENT.encode("utf-8"),
            "text/markdown",
            None,
        )
        if not ok:
            logger.error("provision_user_storage: Welcome.md upload failed for %s", uid)
        for folder in DEFAULT_FOLDERS:
            marker = f"{uid}/{folder}/.keep"
            if not storage.upload_file(
                "uploads", marker, b"", "application/octet-stream", None
            ):
                logger.error(
                    "provision_user_storage: failed to create folder marker %s for %s",
                    folder,
                    uid,
                )
    except Exception as e:
        logger.error("provision_user_storage failed for %s: %s", uid, e, exc_info=True)
