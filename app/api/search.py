"""Elasticsearch-style Durgas Search REST API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from app.services.search_service import engine

router = APIRouter(prefix="/search", tags=["durgas-search"])


def _json_error(exc: Exception, status_code: int = 404) -> HTTPException:
    return HTTPException(status_code=status_code, detail=str(exc))


@router.get("")
@router.get("/")
def root_info() -> dict[str, Any]:
    return engine.root_info()


@router.get("/_cluster/health")
def cluster_health() -> dict[str, Any]:
    return engine.cluster_health()


@router.get("/_cluster/state")
def cluster_state() -> dict[str, Any]:
    return engine.cluster_state()


@router.get("/_nodes")
def nodes() -> dict[str, Any]:
    return engine.nodes()


@router.get("/_nodes/stats")
def nodes_stats() -> dict[str, Any]:
    return engine.nodes_stats()


@router.post("/_bulk")
async def bulk(request: Request) -> dict[str, Any]:
    body = (await request.body()).decode("utf-8")
    return engine.bulk(body)


@router.put("/_snapshot/{repository}")
async def put_repository(repository: str, request: Request) -> dict[str, Any]:
    body = await _json_body(request)
    return engine.put_repository(repository, body)


@router.get("/_snapshot/{repository}")
def get_repository(repository: str) -> dict[str, Any]:
    try:
        return engine.get_repository(repository)
    except KeyError as exc:
        raise _json_error(exc) from exc


@router.put("/_snapshot/{repository}/{snapshot}")
async def create_snapshot(
    repository: str, snapshot: str, request: Request, wait_for_completion: bool = False
) -> dict[str, Any]:
    del wait_for_completion
    try:
        return engine.create_snapshot(repository, snapshot, await _json_body(request))
    except KeyError as exc:
        raise _json_error(exc) from exc


@router.get("/_snapshot/{repository}/{snapshot}")
def get_snapshot(repository: str, snapshot: str) -> dict[str, Any]:
    try:
        return engine.get_snapshots(repository, snapshot)
    except KeyError as exc:
        raise _json_error(exc) from exc


@router.put("/{index}")
async def create_index(index: str, request: Request) -> dict[str, Any]:
    return engine.create_index(index, await _json_body(request))


@router.delete("/{index}")
def delete_index(index: str) -> dict[str, Any]:
    return engine.delete_index(index)


@router.post("/{index}/_doc")
async def index_document_auto(
    index: str, request: Request, response: Response
) -> dict[str, Any]:
    response.status_code = 201
    return engine.put_doc(index, await _json_body(request))


@router.put("/{index}/_doc/{doc_id}")
async def put_document(
    index: str, doc_id: str, request: Request, response: Response
) -> dict[str, Any]:
    response.status_code = 201
    return engine.put_doc(index, await _json_body(request), doc_id)


@router.post("/{index}/_doc/{doc_id}")
async def post_document(index: str, doc_id: str, request: Request) -> dict[str, Any]:
    return engine.put_doc(index, await _json_body(request), doc_id)


@router.post("/{index}/_update/{doc_id}")
async def update_document(index: str, doc_id: str, request: Request) -> dict[str, Any]:
    try:
        return engine.update_doc(index, doc_id, await _json_body(request))
    except KeyError as exc:
        raise _json_error(exc) from exc


@router.delete("/{index}/_doc/{doc_id}")
def delete_document(index: str, doc_id: str) -> dict[str, Any]:
    try:
        return engine.delete_doc(index, doc_id)
    except KeyError as exc:
        raise _json_error(exc) from exc


@router.post("/{index}/_search")
async def search(index: str, request: Request) -> dict[str, Any]:
    try:
        return engine.search(index, await _json_body(request))
    except KeyError as exc:
        raise _json_error(exc) from exc


async def _json_body(request: Request) -> dict[str, Any]:
    if not (await request.body()):
        return {}
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON body: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="JSON object body required")
    return data
