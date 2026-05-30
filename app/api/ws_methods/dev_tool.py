"""Dev AI toolbox WebSocket JSON-RPC handlers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.services.dev_tool.html_fetch import (
    FetchPageError,
    fetch_page_for_analysis,
    parse_page_assets,
)

logger = logging.getLogger(__name__)


async def handle_dev_tool_fetch_page(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch a public URL and return HTML, assets, and page metadata."""
    await require_auth(user, "dev_tool.fetch_page")
    url = (params.get("url") or "").strip()
    if not url:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "url is required")
    try:
        html = await fetch_page_for_analysis(url)
        parsed = parse_page_assets(html, url)
        return {
            "html": parsed["html"],
            "assets": parsed["assets"],
            "pageInfo": parsed["pageInfo"],
        }
    except FetchPageError as e:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, str(e)) from e
    except Exception as e:
        logger.exception("dev_tool.fetch_page failed")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to fetch page: {e}"
        ) from e


def get_methods() -> Dict[str, Any]:
    return {
        "dev_tool.fetch_page": handle_dev_tool_fetch_page,
    }
