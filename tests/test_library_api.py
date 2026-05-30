"""Library (AuraBook) API tests — auth, validation, owner isolation."""

from __future__ import annotations

import pytest

pytest.importorskip("slowapi")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.library import LibraryBookModel  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def _token(sub: str, email: str = "lib@test.local") -> str:
    import importlib

    auth = importlib.import_module("app.core.auth")
    token, _ = auth.issue_access_token(sub, email, 0)
    return token


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {_token('library-owner-a')}"}


@pytest.fixture
def other_auth_headers():
    return {"Authorization": f"Bearer {_token('library-owner-b')}"}


@pytest.fixture(autouse=True)
def _ensure_db():
    import asyncio

    asyncio.run(init_db())
    yield


def test_library_statistics_requires_auth(client):
    r = client.get("/api/library/statistics")
    assert r.status_code == 401


def test_library_statistics_ok(client, auth_headers):
    r = client.get("/api/library/statistics", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "totalBooks" in data
    assert "categoryDistribution" in data


def test_library_chat_requires_query(client, auth_headers):
    r = client.post(
        "/api/library/chat", json={"activeBookIds": []}, headers=auth_headers
    )
    assert r.status_code == 422 or r.status_code == 400


def test_library_chat_ok(client, auth_headers):
    r = client.post(
        "/api/library/chat",
        json={"query": "Summarize my library", "activeBookIds": [], "chatHistory": []},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sender"] == "gemma"
    assert "text" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_owner_isolation_books_seeded_per_owner():
    from app.services.library_service import seed_library_for_owner

    async with AsyncSessionLocal() as db:
        await seed_library_for_owner(db, "library-owner-a")
        await db.commit()
        rows_a = (
            (
                await db.execute(
                    select(LibraryBookModel).where(
                        LibraryBookModel.owner_id == "library-owner-a"
                    )
                )
            )
            .scalars()
            .all()
        )
        await seed_library_for_owner(db, "library-owner-b")
        await db.commit()
        rows_b = (
            (
                await db.execute(
                    select(LibraryBookModel).where(
                        LibraryBookModel.owner_id == "library-owner-b"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(rows_a) >= 3
    assert len(rows_b) >= 3
    assert all(r.owner_id == "library-owner-a" for r in rows_a)
    assert all(r.owner_id == "library-owner-b" for r in rows_b)


def test_schema_has_library_fields():
    pytest.importorskip("chromadb")
    from app.graphql.schema import schema

    result = schema.execute_sync(
        """
        query {
          __schema {
            queryType { fields { name } }
            mutationType { fields { name } }
          }
        }
        """
    )
    assert result.errors is None
    qnames = {f["name"] for f in result.data["__schema"]["queryType"]["fields"]}
    mnames = {f["name"] for f in result.data["__schema"]["mutationType"]["fields"]}
    assert "libraryBooks" in qnames
    assert "libraryBookUpsert" in mnames
