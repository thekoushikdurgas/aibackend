"""
Council Agent - Multi-model deliberation using LLM Council approach
"""

import logging
from typing import Any, Dict, Optional

from app.models.schemas import PageData
from app.services.council import run_full_council
from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class CouncilAgent(BaseAgent):
    """
    Multi-model deliberation agent using LLM Council approach.
    Uses multiple AI models to provide collaborative, peer-reviewed responses.
    """

    agent_type = "council"
    description = "Multi-model deliberation with peer review and synthesis"

    def get_system_prompt(self) -> str:
        return """You are part of a council of AI models that collaboratively answer questions.
Your responses will be evaluated by other models, and a chairman will synthesize the final answer.
Provide clear, accurate, and well-reasoned responses."""

    async def analyze(
        self,
        page_data: PageData,
        query: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Analyze using multi-model council approach.

        Args:
            page_data: Page data from extension
            query: User's question/query
            options: Additional options (can specify council_models, chairman_model)

        Returns:
            AgentResponse with council results
        """
        options = options or {}

        # Get query - use provided query or generate from page
        if not query:
            query = f"Analyze this web page: {page_data.url}"
            if page_data.title:
                query += f" - {page_data.title}"

        try:
            # Extract optional model selection from options
            council_models = options.get("council_models")
            chairman_model = options.get("chairman_model")
            council_options = {
                k: options[k]
                for k in (
                    "council_policy",
                    "policy",
                    "min_confidence",
                    "allow_web_tool",
                    "min_rag_similarity",
                    "verified_min_similarity",
                    "schema_version",
                )
                if k in options and options[k] is not None
            }

            # Run the 3-stage council process
            stage1_results, stage2_results, stage3_result, metadata = (
                await run_full_council(
                    query=query,
                    page_data=page_data,
                    council_models=council_models,
                    chairman_model=chairman_model,
                    council_options=council_options or None,
                )
            )

            # Check if we got a valid response
            if not stage3_result or stage3_result.get("model") == "error":
                error_msg = (
                    stage3_result.get("response", "Unknown error")
                    if stage3_result
                    else "No response"
                )

                # Provide helpful message about insufficient models
                if len(stage1_results) < 3:
                    models_attempted = (
                        metadata.get("models_used", []) if metadata else []
                    )
                    error_msg = (
                        f"Council needs at least 3 models, but only {len(stage1_results)} responded. "
                        f"Models attempted: {', '.join(models_attempted) if models_attempted else 'unknown'}. "
                        f"This may be due to API rate limits or provider issues. "
                        f"Try waiting a minute and sending your message again."
                    )

                return AgentResponse(
                    agent_type=self.agent_type,
                    analysis={
                        "url": page_data.url,
                        "error": error_msg,
                        "stage1_count": len(stage1_results),
                        "stage2_count": len(stage2_results),
                        "models_attempted": (
                            metadata.get("models_used", []) if metadata else []
                        ),
                    },
                    summary=f"Council analysis failed: {error_msg}",
                    success=False,
                    error=error_msg,
                )

            # Extract final response
            final_response = stage3_result.get("response", "")

            # Build analysis dict
            analysis = {
                "url": page_data.url,
                "title": page_data.title,
                "query": query,
                "final_response": final_response,
                "council_v2": (metadata or {}).get("council_v2"),
                "stage1_responses": [
                    {
                        "model": r["model"],
                        "response": (
                            r["response"][:500] + "..."
                            if len(r["response"]) > 500
                            else r["response"]
                        ),
                    }
                    for r in stage1_results
                ],
                "stage2_rankings": [
                    {"model": r["model"], "parsed_ranking": r.get("parsed_ranking", [])}
                    for r in stage2_results
                ],
                "models_used": metadata.get("models_used", []),
                "chairman": metadata.get("chairman", "unknown"),
                "aggregate_rankings": metadata.get("aggregate_rankings", []),
            }

            # Build summary from final response (truncate if needed)
            summary = final_response[:500]
            if len(final_response) > 500:
                summary += "..."

            # Extract recommendations from aggregate rankings
            recommendations = []
            if metadata.get("aggregate_rankings"):
                top_models = metadata["aggregate_rankings"][:3]
                recommendations.append(
                    f"Top ranked models: {', '.join([m['model'] for m in top_models])}"
                )

            # Build comprehensive metadata
            council_metadata = {
                "stage1_count": len(stage1_results),
                "stage2_count": len(stage2_results),
                "models_used": metadata.get("models_used", []),
                "chairman": metadata.get("chairman", "unknown"),
                "aggregate_rankings": metadata.get("aggregate_rankings", []),
                "label_to_model": metadata.get("label_to_model", {}),
                "council_v2": (metadata or {}).get("council_v2"),
                # Include full stage data for detailed inspection
                "stage1_full": stage1_results,
                "stage2_full": stage2_results,
                "stage3_full": stage3_result,
            }

            return AgentResponse(
                agent_type=self.agent_type,
                analysis=analysis,
                summary=summary,
                recommendations=recommendations,
                metadata=council_metadata,
                success=True,
            )

        except Exception as e:
            logger.error(f"Council analysis failed: {e}", exc_info=True)
            return AgentResponse(
                agent_type=self.agent_type,
                analysis={"url": page_data.url, "error": str(e)},
                summary=f"Council analysis failed: {str(e)}",
                success=False,
                error=str(e),
            )
