"""VSQL Video download and columnar export endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import video_service
from app.storage import arrow_export_path, parquet_export_path

router = APIRouter(tags=["vsql-downloads"])


@router.get("/databases/{db_id}/download/video")
def download_video(db_id: str, table_name: Optional[str] = None):
    """Serve encoded video file (URL returned by GraphQL `videoDownloadUrl`)."""
    info = video_service.get_video_info(db_id, table_name=table_name)
    path = info.get("video_path")
    if not path:
        raise HTTPException(status_code=404, detail="Video not found")

    path = Path(str(path))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@router.get("/databases/{db_id}/tables/{table_name}/download/video")
def download_table_video(db_id: str, table_name: str):
    """Serve a selected table's encoded video file."""
    return download_video(db_id, table_name=table_name)


def _build_and_serve_export(
    db_id: str,
    fmt: str,
    table_name: Optional[str],
    out_path: Path,
) -> FileResponse:
    """Build the requested columnar export on-demand and serve it."""
    if not out_path.is_file():
        info = video_service.get_video_info(db_id, table_name=table_name)
        vpath = info.get("video_path")
        if not vpath:
            raise HTTPException(status_code=404, detail="Video not found")
        vpath = Path(str(vpath))
        if not vpath.is_file():
            raise HTTPException(status_code=404, detail="Video file missing")

        from app.video_storage import VideoDB

        try:
            with VideoDB(vpath, mode="r") as vdb:
                if fmt == "parquet":
                    vdb.export_parquet(out_path)
                else:
                    vdb.export_arrow(out_path)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Export failed: {exc}"
            ) from exc

    if not out_path.is_file():
        raise HTTPException(status_code=404, detail="Export not found")

    mime = (
        "application/vnd.apache.parquet"
        if fmt == "parquet"
        else "application/vnd.apache.arrow.file"
    )
    return FileResponse(out_path, filename=out_path.name, media_type=mime)


@router.get("/databases/{db_id}/export/parquet")
def export_db_parquet(db_id: str):
    """Build (if needed) and download the database as a Parquet file."""
    return _build_and_serve_export(db_id, "parquet", None, parquet_export_path(db_id))


@router.get("/databases/{db_id}/export/arrow")
def export_db_arrow(db_id: str):
    """Build (if needed) and download the database as an Arrow IPC file."""
    return _build_and_serve_export(db_id, "arrow", None, arrow_export_path(db_id))


@router.get("/databases/{db_id}/tables/{table_name}/export/parquet")
def export_table_parquet(db_id: str, table_name: str):
    """Build (if needed) and download a table as a Parquet file."""
    return _build_and_serve_export(
        db_id, "parquet", table_name, parquet_export_path(db_id, table_name)
    )


@router.get("/databases/{db_id}/tables/{table_name}/export/arrow")
def export_table_arrow(db_id: str, table_name: str):
    """Build (if needed) and download a table as an Arrow IPC file."""
    return _build_and_serve_export(
        db_id, "arrow", table_name, arrow_export_path(db_id, table_name)
    )
