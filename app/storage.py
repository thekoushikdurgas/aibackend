"""Workspace paths for each vSQL database instance."""

import json
import re
import uuid
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    d = repo_root() / "data" / "vsql"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_database_id() -> str:
    return str(uuid.uuid4())


def database_dir(db_id: str) -> Path:
    d = data_dir() / db_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def video_path(db_id: str) -> Path:
    return database_dir(db_id) / "vsql-export.mkv"


def video_metadata_path(db_id: str) -> Path:
    return database_dir(db_id) / "metadata.json"


def table_slug(table_name: str) -> str:
    """Return a filesystem-safe slug for a logical table name."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", table_name.strip()).strip("_")
    return cleaned or "data"


def table_video_path(db_id: str, table_name: str) -> Path:
    return database_dir(db_id) / "tables" / table_slug(table_name) / "vsql-export.mkv"


def parquet_index_path(db_id: str, table_name: str | None = None) -> Path:
    """Path to the Parquet analytics sidecar for a database or specific table."""
    if table_name:
        return (
            database_dir(db_id)
            / "tables"
            / table_slug(table_name)
            / "vsql-index.parquet"
        )
    return database_dir(db_id) / "vsql-index.parquet"


def arrow_export_path(db_id: str, table_name: str | None = None) -> Path:
    """Path for a one-off Arrow IPC export file."""
    if table_name:
        return (
            database_dir(db_id)
            / "tables"
            / table_slug(table_name)
            / "vsql-export.arrow"
        )
    return database_dir(db_id) / "vsql-export.arrow"


def parquet_export_path(db_id: str, table_name: str | None = None) -> Path:
    """Path for a one-off Parquet export file (download-ready copy)."""
    if table_name:
        return (
            database_dir(db_id)
            / "tables"
            / table_slug(table_name)
            / "vsql-export.parquet"
        )
    return database_dir(db_id) / "vsql-export.parquet"


def load_table_catalog(db_id: str) -> dict[str, Any]:
    path = video_metadata_path(db_id)
    if not path.exists():
        return {"version": 1, "tables": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "tables": []}
    if not isinstance(data, dict):
        return {"version": 1, "tables": []}
    tables = data.get("tables")
    if not isinstance(tables, list):
        tables = []
    return {"version": int(data.get("version", 1)), "tables": tables}


def save_table_catalog(db_id: str, catalog: dict[str, Any]) -> None:
    path = video_metadata_path(db_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")


def list_catalog_tables(db_id: str) -> list[dict[str, str]]:
    catalog = load_table_catalog(db_id)
    result: list[dict[str, str]] = []
    for item in catalog.get("tables", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        slug = str(item.get("slug") or table_slug(name))
        if name:
            result.append({"name": name, "slug": slug})
    return result


def register_table(db_id: str, table_name: str) -> dict[str, str]:
    name = table_name.strip() or "data"
    slug = table_slug(name)
    catalog = load_table_catalog(db_id)
    tables = [
        item
        for item in catalog.get("tables", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip() != name
    ]
    entry = {"name": name, "slug": slug}
    tables.append(entry)
    catalog["tables"] = tables
    save_table_catalog(db_id, catalog)
    return entry


def unregister_table(db_id: str, table_name: str) -> None:
    name = table_name.strip()
    catalog = load_table_catalog(db_id)
    catalog["tables"] = [
        item
        for item in catalog.get("tables", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip() != name
    ]
    save_table_catalog(db_id, catalog)
