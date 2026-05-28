"""Unit tests for RAG claim verifier heuristics."""

from unittest.mock import MagicMock

from app.services.council.verifier import verify_claim_rag, ClaimStatus


def test_verify_unsupported_empty_hits():
    r = MagicMock()
    r.retrieve = MagicMock(return_value=[])
    v = verify_claim_rag("something factual", r, 0.5)
    assert v.status == ClaimStatus.UNSUPPORTED


def test_verify_supported_with_strong_match():
    r = MagicMock()
    r.retrieve = MagicMock(
        return_value=[
            {
                "content": "The speed of light in vacuum is approximately 299792458 meters per second.",
                "metadata": {"url": "https://example.com", "title": "Physics"},
                "id": "c1",
                "score": 0.9,
            }
        ]
    )
    v = verify_claim_rag(
        "The speed of light in vacuum is about 299792458 meters per second", r, 0.3
    )
    assert v.status == ClaimStatus.SUPPORTED
    assert v.confidence > 0.3
