"""Batch method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


async def handle_batch_process(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    from app.api.ws_gateway import gateway

    requests = params.get("requests") or []
    if not isinstance(requests, list) or not requests:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "requests must be a non-empty list"
        )

    results = []
    progress = []
    for idx, item in enumerate(requests):
        method = item.get("method")
        method_params = item.get("params", {})
        if method not in gateway.methods:
            results.append({"index": idx, "error": f"Method not found: {method}"})
            progress.append({"index": idx, "status": "failed"})
            continue
        try:
            handler = gateway.methods[method]
            result = await handler(
                method_params, user=user, connection_id=connection_id
            )
            results.append({"index": idx, "method": method, "result": result})
            progress.append({"index": idx, "status": "done"})
        except Exception as exc:
            results.append({"index": idx, "method": method, "error": str(exc)})
            progress.append({"index": idx, "status": "failed"})

    return {"results": results, "progress": progress, "count": len(results)}


def get_methods() -> Dict[str, Any]:
    return {"batch.process": handle_batch_process}
