"""NLP method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.nlp.ai21_nlp import AI21NLPService
from app.services.nlp.deepgram_text import DeepgramTextService
from app.services.nlp.summarization import SummarizationService


async def handle_nlp_process(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    task = (params.get("task") or "summarize").lower()
    text = params.get("text")
    if not text:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing text")

    if task in {"summarize", "hf_summarize"}:
        return await SummarizationService().summarize(
            text=text,
            max_length=params.get("max_length"),
            min_length=params.get("min_length"),
        )
    if task in {"ai21_summarize", "ai21"}:
        return await AI21NLPService().summarize(text=text, focus=params.get("focus"))
    if task in {"grammar", "grammar_check"}:
        return await AI21NLPService().grammar_check(text=text)
    if task in {"improve", "improve_text"}:
        return await AI21NLPService().improve_text(
            text=text, improvement_types=params.get("improvement_types")
        )
    if task in {"deepgram_summarize", "deepgram"}:
        return await DeepgramTextService().summarize(
            text=text,
            language=params.get("language", "en"),
            max_length=params.get("max_length"),
        )
    raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, f"Unsupported task: {task}")


def get_methods() -> Dict[str, Any]:
    return {"nlp.process": handle_nlp_process}
