"""
Council policy and run options for anti-hallucination modes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, cast

from app.config import settings


class CouncilPolicy(str, Enum):
    """How strictly the council must ground answers in retrieved evidence."""

    OPEN = "open"  # Legacy: no claim verification (mark as unverified in UI)
    GROUNDED = "grounded"  # RAG + citations; claims checked against retrieved chunks
    VERIFIED = "verified"  # Stricter thresholds; abstain if coverage below floor


@dataclass
class CouncilRunOptions:
    """Per-request options for Council v2."""

    policy: CouncilPolicy = CouncilPolicy.OPEN
    min_confidence: float = 0.5
    allow_web_tool: bool = False
    min_rag_similarity: float = 0.25
    verified_min_similarity: float = 0.45
    schema_version: str = "2.0.0"

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CouncilRunOptions":
        d = data or {}
        default_pol = (
            str(getattr(settings, "council_default_policy", "open")).strip().lower()
        )
        policy_raw = (
            str(d.get("council_policy") or d.get("policy") or default_pol)
            .strip()
            .lower()
        )
        try:
            policy = CouncilPolicy(policy_raw)
        except ValueError:
            policy = CouncilPolicy.OPEN
        return cls(
            policy=policy,
            min_confidence=float(d.get("min_confidence", 0.5)),
            allow_web_tool=bool(d.get("allow_web_tool", False)),
            min_rag_similarity=float(d.get("min_rag_similarity", 0.25)),
            verified_min_similarity=float(
                cast(
                    Any,
                    d.get("verified_min_similarity", d.get("min_rag_similarity", 0.45)),
                )
            ),
            schema_version=str(d.get("schema_version", "2.0.0")),
        )

    def effective_verify_threshold(self) -> float:
        if self.policy == CouncilPolicy.VERIFIED:
            return max(self.min_confidence, self.verified_min_similarity)
        if self.policy == CouncilPolicy.GROUNDED:
            return max(self.min_confidence, self.min_rag_similarity)
        return 0.0


def parse_council_options(options: Optional[Dict[str, Any]]) -> CouncilRunOptions:
    """Merge options dict with defaults (used by agents.analyze and council.run)."""
    return CouncilRunOptions.from_dict(options or {})
