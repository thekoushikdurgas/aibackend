"""
Ranking parsing utilities for council responses
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order (e.g., ["Response A", "Response B"])
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r"\d+\.\s*Response [A-Z]", ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                labels: List[str] = []
                for m in numbered_matches:
                    hit = re.search(r"Response [A-Z]", m)
                    if hit:
                        labels.append(hit.group())
                return labels

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r"Response [A-Z]", ranking_section)
            if matches:
                return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r"Response [A-Z]", ranking_text)
    if matches:
        logger.warning(
            "Could not find FINAL RANKING section, using fallback extraction"
        )
        return matches

    logger.warning(f"Could not parse ranking from text: {ranking_text[:200]}...")
    return []


def extract_final_ranking_section(text: str) -> str:
    """
    Extract just the FINAL RANKING section from a model's response.

    Args:
        text: The full response text

    Returns:
        The ranking section text, or empty string if not found
    """
    if "FINAL RANKING:" in text:
        parts = text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1].strip()
            # Take up to the next major section or end of text
            # Stop at double newline or common section headers
            lines = ranking_section.split("\n")
            result_lines = []
            for line in lines:
                # Stop if we hit another major section
                if any(
                    header in line.upper()
                    for header in ["EVALUATION:", "ANALYSIS:", "CONCLUSION:"]
                ):
                    break
                result_lines.append(line)
            return "\n".join(result_lines).strip()

    return ""
