"""
Prompt templates for council stages
"""

from typing import List, Dict, Any


def build_stage1_prompt(query: str, page_context: str = "") -> str:
    """
    Build the prompt for Stage 1 (initial responses).

    Args:
        query: User's question/query
        page_context: Optional page context from extension

    Returns:
        Formatted prompt string
    """
    prompt_parts = []

    if page_context:
        prompt_parts.append(f"Context about the web page:\n{page_context}\n")

    prompt_parts.append(f"User Question: {query}")
    prompt_parts.append(
        "\nPlease provide a clear, accurate, and helpful answer to this question."
    )

    if page_context:
        prompt_parts.append("Use the provided page context to inform your response.")

    return "\n".join(prompt_parts)


def format_sources_for_prompt(sources: List[Dict[str, Any]]) -> str:
    """
    sources: list of dicts with keys content, optional metadata (url, title), optional id
    Renders as [S1], [S2], ... for inline citations in stage 1.
    """
    if not sources:
        return "(No source passages were retrieved. You must answer with UNKNOWN and explain that evidence is missing.)"
    parts = []
    for i, s in enumerate(sources, 1):
        meta = s.get("metadata") or {}
        title = (meta.get("title") or "").strip()
        url = (meta.get("url") or "").strip()
        head = f"[S{i}]"
        if title or url:
            head += f" {title} — {url}" if title and url else f" {title or url}"
        content = (s.get("content") or "")[:4000]
        parts.append(f"{head}\n{content}")
    return "\n\n".join(parts)


def build_stage1_grounded_prompt(
    query: str,
    sources_block: str,
    page_context: str = "",
    strict: bool = False,
) -> str:
    """
    Stage 1 with mandatory citations [S#] from sources_block.
    If strict (verified mode), prohibit unsourced factual assertions.
    """
    extra = ""
    if page_context:
        extra = f"\n\nAdditional page summary:\n{page_context}\n"
    rules = [
        "You must ground every factual statement in the SOURCE PASSAGES below.",
        "After each sentence or clause that states a fact, add an inline citation like [S2] matching the source index.",
        "If the sources do not contain enough information, reply with a short paragraph that begins with UNKNOWN: and explain what is missing.",
        "Do not invent citations; only use [S1]..[SN] for the provided passages.",
    ]
    if strict:
        rules.append(
            "VERIFIED mode: if you are not 100% sure a fact appears in a cited passage, do not state it; say you lack verified evidence."
        )
    return f"""You are a careful research assistant. Answer the user's question using ONLY the SOURCE PASSAGES.
{extra}
User Question: {query}

Rules:
- {' '.join(rules)}

SOURCE PASSAGES:
{sources_block}

Now answer the question following the rules above."""


def build_stage2_verified_overlap_prompt(
    user_query: str,
    responses_text: str,
    verification_stats: str,
    page_context: str = "",
) -> str:
    """
    Stage 2: rank by evidence-backed content; verification_stats summarizes SUPPORTED claim ratios per response.
    """
    context_part = (
        f"\n\nContext about the web page:\n{page_context}" if page_context else ""
    )
    return f"""You are evaluating responses that were checked against retrieved evidence.

Question: {user_query}{context_part}

Verification summary (higher supported/total is better, but also consider whether citations match the user question):
{verification_stats}

Here are the anonymized responses from Stage 1:

{responses_text}

Your task:
1. Briefly discuss each response, prioritizing how well supported the factual content is.
2. At the end, provide FINAL RANKING: as before (best to worst: Response A, etc.).

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Numbered list: "1. Response X" per line, only the label.
"""


def build_stage3_chairman_verified_prompt(
    user_query: str,
    stage1_text: str,
    stage2_text: str,
    verification_ledger: str,
    page_context: str = "",
    citation_only: bool = True,
) -> str:
    context_part = (
        f"\n\nContext about the web page:\n{page_context}" if page_context else ""
    )
    rule = (
        "You may ONLY restate information that is marked SUPPORTED in the ledger, and you must keep [S#] citations inline."
        if citation_only
        else "Prefer SUPPORTED claims; if you mention anything else, prefix with 'Unverified:'."
    )
    return f"""You are the Chairman. Produce the final user-facing answer.

Original Question: {user_query}{context_part}

{rule}

STAGE 1 (full):
{stage1_text}

STAGE 2 (rankings):
{stage2_text}

VERIFICATION LEDGER (per extracted claim):
{verification_ledger}

If there are no SUPPORTED claims, reply with exactly one paragraph starting with: This question could not be verified against available sources. Then briefly list what is missing. Do not fabricate details."""


def build_stage2_ranking_prompt(
    user_query: str, responses_text: str, page_context: str = ""
) -> str:
    """
    Build the prompt for Stage 2 (peer review and ranking).

    Args:
        user_query: Original user question
        responses_text: Anonymized responses from Stage 1
        page_context: Optional page context

    Returns:
        Formatted ranking prompt
    """
    context_part = ""
    if page_context:
        context_part = f"\n\nContext about the web page:\n{page_context}"

    prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}{context_part}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    return prompt


def build_stage3_chairman_prompt(
    user_query: str, stage1_text: str, stage2_text: str, page_context: str = ""
) -> str:
    """
    Build the prompt for Stage 3 (chairman synthesis).

    Args:
        user_query: Original user question
        stage1_text: All Stage 1 responses with model names
        stage2_text: All Stage 2 rankings and evaluations
        page_context: Optional page context

    Returns:
        Formatted chairman prompt
    """
    context_part = ""
    if page_context:
        context_part = f"\n\nContext about the web page:\n{page_context}"

    prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}{context_part}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- The specific context of the web page (if provided)

Provide a clear, well-reasoned final answer that represents the council's collective wisdom. Be concise but thorough, and prioritize accuracy and helpfulness."""

    return prompt
