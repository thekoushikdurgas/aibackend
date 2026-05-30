"""Local Durgas Search engine used by the FastAPI REST router.

This is intentionally small but Elasticsearch-shaped: indices contain documents,
bulk accepts NDJSON action/source pairs, search supports a simple match query,
and repository/snapshot calls are mocked for local development.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def public_base_url() -> str:
    """Return the advertised backend base URL for localhost/IP hosting."""

    explicit = os.environ.get("VSQL_PUBLIC_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    host = os.environ.get("VSQL_HOST", "127.0.0.1")
    port = os.environ.get("VSQL_PORT", "8000")
    return f"http://{host}:{port}"


def _tokenize(value: Any) -> set[str]:
    text = str(value).lower()
    out: set[str] = set()
    current: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            current.append(ch)
        elif current:
            out.add("".join(current))
            current.clear()
    if current:
        out.add("".join(current))
    return out


@dataclass
class SearchIndex:
    name: str
    mappings: dict[str, Any] = field(default_factory=dict)
    docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    fields: set[str] = field(default_factory=lambda: {"id"})

    def put_doc(self, doc_id: str, doc: dict[str, Any]) -> dict[str, Any]:
        stored = dict(doc)
        stored["id"] = doc_id
        for key, value in stored.items():
            if isinstance(value, str):
                self.fields.add(key)
        created = doc_id not in self.docs
        self.docs[doc_id] = stored
        return {
            "_index": self.name,
            "_id": doc_id,
            "result": "created" if created else "updated",
            "_source": stored,
        }

    def update_doc(self, doc_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        if doc_id not in self.docs:
            raise KeyError(f"document [{doc_id}] missing")
        doc = dict(self.docs[doc_id])
        doc.update(patch.get("doc", patch))
        return self.put_doc(doc_id, doc)

    def delete_doc(self, doc_id: str) -> bool:
        return self.docs.pop(doc_id, None) is not None

    def search(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        body = body or {}
        query = body.get("query") or {"match_all": {}}
        size = int(body.get("size", 10))
        hits = []
        if "match_all" in query:
            docs = [(doc_id, doc, 1.0) for doc_id, doc in self.docs.items()]
        else:
            match = query.get("match") if isinstance(query, dict) else None
            docs = []
            if isinstance(match, dict) and match:
                field, needle = next(iter(match.items()))
                terms = _tokenize(needle)
                for doc_id, doc in self.docs.items():
                    value = doc.get(field, "")
                    value_terms = _tokenize(value)
                    score = 0.0
                    for term in terms:
                        if term in value_terms:
                            score += 1.0
                        elif any(v.startswith(term) for v in value_terms):
                            score += 0.5
                    if score > 0:
                        docs.append((doc_id, doc, score))
        for doc_id, doc, score in sorted(docs, key=lambda item: item[2], reverse=True)[
            :size
        ]:
            hits.append(
                {
                    "_index": self.name,
                    "_id": doc_id,
                    "_score": score,
                    "_source": doc,
                }
            )
        return {
            "took": 1,
            "timed_out": False,
            "hits": {
                "total": {"value": len(hits), "relation": "eq"},
                "max_score": hits[0]["_score"] if hits else None,
                "hits": hits,
            },
        }

    def stats(self) -> dict[str, Any]:
        return {"doc_count": len(self.docs), "fields": sorted(self.fields)}


class SearchEngine:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.indices: dict[str, SearchIndex] = {}
        self.repositories: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}

    def root_info(self) -> dict[str, Any]:
        return {
            "name": "durgas-search-node-1",
            "cluster_name": "durgas-search-local",
            "base_url": public_base_url(),
            "version": {
                "number": "1.0.0-local",
                "build_type": "fastapi",
                "minimum_wire_compatibility_version": "1.0.0",
                "minimum_index_compatibility_version": "1.0.0",
            },
            "tagline": "You Know, for Video Search",
        }

    def create_index(
        self, name: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if name not in self.indices:
            self.indices[name] = SearchIndex(
                name=name, mappings=(body or {}).get("mappings", {})
            )
        return {"acknowledged": True, "index": name}

    def delete_index(self, name: str) -> dict[str, Any]:
        deleted = self.indices.pop(name, None) is not None
        return {"acknowledged": deleted}

    def get_index(self, name: str, *, create: bool = True) -> SearchIndex:
        if name not in self.indices:
            if not create:
                raise KeyError(f"index [{name}] missing")
            self.create_index(name)
        return self.indices[name]

    def put_doc(
        self, index: str, doc: dict[str, Any], doc_id: str | None = None
    ) -> dict[str, Any]:
        return self.get_index(index).put_doc(doc_id or str(uuid.uuid4()), doc)

    def update_doc(
        self, index: str, doc_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        result = self.get_index(index, create=False).update_doc(doc_id, body)
        return {"_index": index, "_id": doc_id, "result": result["result"]}

    def delete_doc(self, index: str, doc_id: str) -> dict[str, Any]:
        deleted = self.get_index(index, create=False).delete_doc(doc_id)
        return {
            "_index": index,
            "_id": doc_id,
            "result": "deleted" if deleted else "not_found",
        }

    def search(self, index: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get_index(index, create=False).search(body)

    def bulk(self, ndjson: str) -> dict[str, Any]:
        lines = [line for line in ndjson.splitlines() if line.strip()]
        items: list[dict[str, Any]] = []
        errors = False
        i = 0
        while i < len(lines):
            try:
                action = json.loads(lines[i])
                op, meta = next(iter(action.items()))
                if op in {"index", "create"}:
                    if i + 1 >= len(lines):
                        raise ValueError("missing source line")
                    source = json.loads(lines[i + 1])
                    index = meta.get("_index")
                    if not index:
                        raise ValueError("_index is required")
                    doc_id = meta.get("_id") or str(uuid.uuid4())
                    result = self.put_doc(index, source, doc_id)
                    items.append(
                        {op: {"_index": index, "_id": result["_id"], "status": 201}}
                    )
                    i += 2
                elif op == "update":
                    if i + 1 >= len(lines):
                        raise ValueError("missing update source line")
                    index = meta.get("_index")
                    doc_id = meta.get("_id")
                    if not index or not doc_id:
                        raise ValueError("_index and _id are required")
                    result = self.update_doc(index, doc_id, json.loads(lines[i + 1]))
                    items.append(
                        {
                            op: {
                                "_index": index,
                                "_id": doc_id,
                                "status": 200,
                                "result": result["result"],
                            }
                        }
                    )
                    i += 2
                elif op == "delete":
                    index = meta.get("_index")
                    doc_id = meta.get("_id")
                    if not index or not doc_id:
                        raise ValueError("_index and _id are required")
                    result = self.delete_doc(index, doc_id)
                    items.append(
                        {
                            op: {
                                "_index": index,
                                "_id": doc_id,
                                "status": 200,
                                "result": result["result"],
                            }
                        }
                    )
                    i += 1
                else:
                    raise ValueError(f"unsupported bulk op {op}")
            except Exception as exc:
                errors = True
                items.append({"error": {"status": 400, "reason": str(exc)}})
                i += 1
        return {"took": 1, "errors": errors, "items": items}

    def cluster_health(self) -> dict[str, Any]:
        shard_count = len(self.indices)
        return {
            "cluster_name": "durgas-search-local",
            "status": "green",
            "timed_out": False,
            "number_of_nodes": 1,
            "number_of_data_nodes": 1,
            "active_primary_shards": shard_count,
            "active_shards": shard_count,
            "relocating_shards": 0,
            "initializing_shards": 0,
            "unassigned_shards": 0,
            "active_shards_percent_as_number": 100.0,
        }

    def nodes(self) -> dict[str, Any]:
        return {
            "_nodes": {"total": 1, "successful": 1, "failed": 0},
            "cluster_name": "durgas-search-local",
            "nodes": {
                "node-1-id": {
                    "name": "node-1",
                    "host": os.environ.get("VSQL_HOST", "127.0.0.1"),
                    "ip": os.environ.get("VSQL_HOST", "127.0.0.1"),
                    "version": "1.0.0-local",
                    "roles": ["master", "data", "ingest"],
                    "http": {"publish_address": public_base_url()},
                }
            },
        }

    def nodes_stats(self) -> dict[str, Any]:
        doc_count = sum(len(index.docs) for index in self.indices.values())
        return {
            "_nodes": {"total": 1, "successful": 1, "failed": 0},
            "cluster_name": "durgas-search-local",
            "nodes": {
                "node-1-id": {
                    "timestamp": int(time.time() * 1000),
                    "name": "node-1",
                    "indices": {
                        "docs": {"count": doc_count, "deleted": 0},
                        "store": {"size_in_bytes": doc_count * 1024},
                    },
                    "process": {"open_file_descriptors": 0},
                }
            },
        }

    def cluster_state(self) -> dict[str, Any]:
        return {
            "cluster_name": "durgas-search-local",
            "metadata": {
                "indices": {
                    name: {"mappings": idx.mappings, "stats": idx.stats()}
                    for name, idx in self.indices.items()
                }
            },
            "routing_table": {
                "indices": {
                    name: {"shards": {"0": [{"state": "STARTED"}]}}
                    for name in self.indices
                }
            },
        }

    def put_repository(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        self.repositories[name] = config
        return {"acknowledged": True}

    def get_repository(self, name: str) -> dict[str, Any]:
        if name == "_all":
            return self.repositories
        if name not in self.repositories:
            raise KeyError(f"repository [{name}] missing")
        return {name: self.repositories[name]}

    def create_snapshot(
        self, repository: str, snapshot: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        if repository not in self.repositories:
            raise KeyError(f"repository [{repository}] missing")
        now = int(time.time() * 1000)
        info = {
            "snapshot": snapshot,
            "uuid": f"{snapshot}-{now}",
            "version": "1.0.0-local",
            "indices": list(self.indices.keys()),
            "state": "SUCCESS",
            "start_time_in_millis": now,
            "end_time_in_millis": now + 1,
            "duration_in_millis": 1,
            "failures": [],
            "shards": {
                "total": len(self.indices),
                "failed": 0,
                "successful": len(self.indices),
            },
            **config,
        }
        self.snapshots[f"{repository}:{snapshot}"] = info
        return {"snapshot": info}

    def get_snapshots(self, repository: str, snapshot: str) -> dict[str, Any]:
        if snapshot == "_all":
            snapshots = [
                value
                for key, value in self.snapshots.items()
                if key.startswith(f"{repository}:")
            ]
            return {"snapshots": snapshots}
        key = f"{repository}:{snapshot}"
        if key not in self.snapshots:
            raise KeyError(f"snapshot [{snapshot}] missing")
        return {"snapshots": [self.snapshots[key]]}


engine = SearchEngine()
