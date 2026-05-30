"""Video-backed user rows with bcrypt + JWT (workspace-scoped)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
import bcrypt

from ..video_storage import VideoDB
from .video_service import _resolve_video_file, list_video_tables, query_video_database

USERS_TABLE = "vsql_users"
JWT_ALG = "HS256"
JWT_SECRET = os.environ.get("VSQL_JWT_SECRET", "dev-insecure-change-me")


def ensure_users_table(db_id: str) -> None:
    if USERS_TABLE in list_video_tables(db_id):
        return
    q = (
        f'CREATE TABLE "{USERS_TABLE}" '
        "(email TEXT, password_hash TEXT, created_at TEXT)"
    )
    r = query_video_database(db_id, q)
    if r.get("error"):
        raise ValueError(str(r["error"]))


def register_user(db_id: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user row in the workspace video table."""
    ensure_users_table(db_id)
    email_clean = email.strip().lower()
    if not email_clean or len(password) < 8:
        return {"ok": False, "message": "valid email and password (8+ chars) required"}
    sel = query_video_database(db_id, f'SELECT email FROM "{USERS_TABLE}" LIMIT 2000')
    for row in sel.get("rows") or []:
        if row and str(row[0]).lower() == email_clean:
            return {"ok": False, "message": "email already registered"}
    video_file = _resolve_video_file(db_id, USERS_TABLE)
    ts = datetime.now(timezone.utc).isoformat()
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with VideoDB(video_file, mode="rw") as vdb:
        vdb.crud.insert_row(
            {
                "email": email_clean,
                "password_hash": pw_hash,
                "created_at": ts,
            }
        )
    return {"ok": True, "message": "registered"}


def login_user(db_id: str, email: str, password: str) -> Dict[str, Any]:
    """Verify credentials and return a signed JWT."""
    if USERS_TABLE not in list_video_tables(db_id):
        return {"ok": False, "message": "invalid credentials"}
    email_clean = email.strip().lower()
    sel = query_video_database(
        db_id,
        f'SELECT email, password_hash FROM "{USERS_TABLE}" LIMIT 5000',
    )
    if sel.get("error"):
        return {"ok": False, "message": "invalid credentials"}
    for row in sel.get("rows") or []:
        if not row or len(row) < 2:
            continue
        em, ph = row[0], row[1]
        if str(em).lower() != email_clean:
            continue
        if bcrypt.checkpw(password.encode("utf-8"), str(ph).encode("utf-8")):
            token = jwt.encode(
                {
                    "sub": email_clean,
                    "db": db_id,
                    "exp": datetime.now(timezone.utc) + timedelta(days=7),
                    "jti": str(uuid.uuid4()),
                },
                JWT_SECRET,
                algorithm=JWT_ALG,
            )
            if isinstance(token, bytes):
                token = token.decode("ascii")
            return {"ok": True, "token": token}
        return {"ok": False, "message": "invalid credentials"}
    return {"ok": False, "message": "invalid credentials"}
