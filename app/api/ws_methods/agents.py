"""
Agent method handlers
"""

import logging
from typing import Dict, Any, Optional

from app.models.schemas import AgentType, PageData
from app.agents import AgentRouter
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_agents_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.list method"""
    agents = []
    for agent_type in AgentType:
        agents.append(
            {
                "type": agent_type.value,
                "description": _get_agent_description(agent_type),
            }
        )

    return {"agents": agents}


async def handle_agents_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.{agent_type}.analyze method"""
    agent_type_str = params.get("agent_type")
    if not agent_type_str:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: agent_type"
        )

    try:
        agent_type = AgentType(agent_type_str)
    except ValueError:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid agent_type: {agent_type_str}"
        )

    # Parse page_data
    page_data_dict = params.get("page_data")
    if not page_data_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: page_data"
        )

    try:
        page_data = PageData(**page_data_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid page_data: {str(e)}"
        )

    query = params.get("query")
    options = params.get("options")

    try:
        response = await AgentRouter.route(
            agent_type=agent_type, page_data=page_data, query=query, options=options
        )

        return {
            "agent_type": response.agent_type,
            "analysis": response.analysis,
            "summary": response.summary,
            "recommendations": response.recommendations,
            "metadata": response.metadata,
            "timestamp": (
                response.timestamp.isoformat()
                if hasattr(response.timestamp, "isoformat")
                else str(response.timestamp)
            ),
        }
    except ValueError as e:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, str(e))
    except Exception as e:
        logger.error(f"Agent analysis error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Agent analysis failed: {str(e)}"
        )


async def handle_agents_auto_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.auto_analyze method"""
    page_data_dict = params.get("page_data")
    if not page_data_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: page_data"
        )

    query = params.get("query")
    if not query:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: query"
        )

    try:
        page_data = PageData(**page_data_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid page_data: {str(e)}"
        )

    options = params.get("options")

    try:
        response = await AgentRouter.auto_route(
            query=query, page_data=page_data, options=options
        )

        return {
            "agent_type": response.agent_type,
            "analysis": response.analysis,
            "summary": response.summary,
            "recommendations": response.recommendations,
            "metadata": response.metadata,
            "timestamp": (
                response.timestamp.isoformat()
                if hasattr(response.timestamp, "isoformat")
                else str(response.timestamp)
            ),
        }
    except Exception as e:
        logger.error(f"Auto-analyze error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Auto-analyze failed: {str(e)}"
        )


async def handle_agents_batch_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.batch_analyze method"""
    page_data_dict = params.get("page_data")
    if not page_data_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: page_data"
        )

    agent_types_str = params.get("agent_types", [])
    if not agent_types_str:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: agent_types"
        )

    try:
        page_data = PageData(**page_data_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid page_data: {str(e)}"
        )

    try:
        agent_types = [AgentType(agent_type_str) for agent_type_str in agent_types_str]
    except ValueError as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid agent_type in list: {str(e)}"
        )

    query = params.get("query")

    results = {}
    errors = {}

    for agent_type in agent_types:
        try:
            response = await AgentRouter.route(
                agent_type=agent_type, page_data=page_data, query=query
            )
            results[agent_type.value] = {
                "summary": response.summary,
                "recommendations": response.recommendations,
                "metadata": response.metadata,
            }
        except Exception as e:
            logger.error(f"Batch analysis error for {agent_type}: {e}")
            errors[agent_type.value] = str(e)

    return {
        "results": results,
        "errors": errors,
        "success_count": len(results),
        "error_count": len(errors),
    }


async def handle_agents_quick_seo(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.quick_seo method"""
    page_data_dict = params.get("page_data")
    if not page_data_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: page_data"
        )

    try:
        page_data = PageData(**page_data_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid page_data: {str(e)}"
        )

    target_keyword = params.get("target_keyword")
    options = {"target_keyword": target_keyword} if target_keyword else {}

    try:
        response = await AgentRouter.route(
            agent_type=AgentType.SEO, page_data=page_data, options=options
        )

        metadata = response.metadata or {}

        return {
            "url": page_data.url,
            "seo_score": metadata.get("seo_score", 0),
            "title_score": metadata.get("title_score", 0),
            "meta_score": metadata.get("meta_score", 0),
            "heading_score": metadata.get("heading_score", 0),
            "image_score": metadata.get("image_score", 0),
            "summary": response.summary,
            "top_recommendations": (
                response.recommendations[:5] if response.recommendations else []
            ),
        }
    except Exception as e:
        logger.error(f"Quick SEO analysis error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"SEO analysis failed: {str(e)}"
        )


async def handle_agents_summarize(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle agents.summarize method"""
    page_data_dict = params.get("page_data")
    if not page_data_dict:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: page_data"
        )

    try:
        page_data = PageData(**page_data_dict)
    except Exception as e:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, f"Invalid page_data: {str(e)}"
        )

    max_length = params.get("max_length", 500)

    try:
        response = await AgentRouter.route(
            agent_type=AgentType.RESEARCH,
            page_data=page_data,
            query="Summarize this page content concisely.",
            options={"task": "summarize"},
        )

        summary = (
            response.summary[:max_length]
            if len(response.summary) > max_length
            else response.summary
        )

        return {
            "url": page_data.url,
            "title": page_data.title,
            "summary": summary,
            "key_points": (
                response.recommendations[:5] if response.recommendations else []
            ),
            "metadata": response.metadata,
        }
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Summarize failed: {str(e)}"
        )


def _get_agent_description(agent_type: AgentType) -> str:
    """Get description for agent type"""
    descriptions = {
        AgentType.PAGE_ANALYZER: "Deep page structure and organization analysis",
        AgentType.CONTENT_EXTRACTOR: "Extract structured data and entities from pages",
        AgentType.SEO: "SEO analysis and optimization recommendations",
        AgentType.IMAGE_ANALYZER: "Image analysis, optimization, and accessibility",
        AgentType.RESEARCH: "Content summarization, Q&A, and research insights",
        AgentType.COUNCIL: "Multi-model deliberation with peer review and synthesis",
        AgentType.WEBSITE_SCRAPER: "Comprehensive website analysis with smart scraping and AI insights",
    }
    return descriptions.get(agent_type, "Unknown agent")


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "agents.list": handle_agents_list,
        "agents.analyze": handle_agents_analyze,
        "agents.auto_analyze": handle_agents_auto_analyze,
        "agents.batch_analyze": handle_agents_batch_analyze,
        "agents.quick_seo": handle_agents_quick_seo,
        "agents.summarize": handle_agents_summarize,
    }
