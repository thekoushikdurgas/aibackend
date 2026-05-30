"""Unit tests for library_service validation (no full app import)."""

from __future__ import annotations

import pytest
from graphql import GraphQLError

from app.services.library_service import (
    compute_statistics,
    validate_library_id,
    validate_rating,
)
from app.models.library import LibraryBookModel


def test_validate_rating_bounds():
    with pytest.raises(GraphQLError):
        validate_rating(0)
    with pytest.raises(GraphQLError):
        validate_rating(6)
    assert validate_rating(3) == 3.0


def test_validate_library_id_rejects_path_injection():
    with pytest.raises(GraphQLError):
        validate_library_id("../../evil")


def test_compute_statistics_empty():
    stats = compute_statistics([])
    assert stats["totalBooks"] == 0
    assert stats["readingEfficiency"] == 0.0


def test_compute_statistics_with_books():
    b = LibraryBookModel(
        id="b1",
        owner_id="o1",
        title="T",
        author="A",
        category="Sci",
        borrowing_status="borrowed",
        pdf_attached=False,
        pages_total=100,
        pages_read=50,
        rating=4.0,
    )
    stats = compute_statistics([b])
    assert stats["totalBooks"] == 1
    assert stats["borrowedBooks"] == 1
    assert stats["totalPagesRead"] == 50
