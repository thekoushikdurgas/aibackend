"""
JSON-RPC methods for Council v2 (anti-hallucination) runs.
"""

import logging
from typing import Any, Dict, Optional

from app.models.schemas import PageData
from app.services.council import run_full_council
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)

COUNCIL_RUN_SCHEMA_V2 = "2.0.0"


async def handle_council_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    council.run — same core pipeline as agents.analyze (council) with explicit v2 options.

    Params: query, page_data, council_models?, chairman_model?,
    council_policy|policy, min_confidence, allow_web_tool, min_rag_similarity, verified_min_similarity, schema_version
    """
    query = (params or {}).get("query")
    if not query or not str(query).strip():
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: query",
        )
    page_dict = (params or {}).get("page_data")
    if not page_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing required parameter: page_data",
        )
    try:
        page_data = PageData(**page_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            f"Invalid page_data: {e}",
        ) from e

    council_options = {
        "policy": params.get("council_policy") or params.get("policy"),
        "min_confidence": params.get("min_confidence"),
        "allow_web_tool": params.get("allow_web_tool"),
        "min_rag_similarity": params.get("min_rag_similarity"),
        "verified_min_similarity": params.get("verified_min_similarity"),
        "schema_version": params.get("schema_version", COUNCIL_RUN_SCHEMA_V2),
    }
    council_options = {k: v for k, v in council_options.items() if v is not None}

    try:
        s1, s2, s3, meta = await run_full_council(
            query=str(query),
            page_data=page_data,
            council_models=params.get("council_models"),
            chairman_model=params.get("chairman_model"),
            council_options=council_options,
        )
    except Exception as e:
        logger.error("council.run failed: %s", e, exc_info=True)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR,
            f"council.run failed: {e!s}",
        ) from e

    return {
        "schema_version": COUNCIL_RUN_SCHEMA_V2,
        "stage1": s1,
        "stage2": s2,
        "stage3": s3,
        "metadata": meta,
    }


def get_methods() -> Dict[str, Any]:
    return {
        "council.run": handle_council_run,
    }
