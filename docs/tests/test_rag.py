"""
Tests for RAG components
"""

import pytest
import tempfile
import os

from app.services.rag import (
    ChromaVectorStore,
    DocumentChunker,
    get_embedding_service,
    DocumentLoader,
)
from app.services.document_service import DocumentService


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    import shutil

    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def vector_store(temp_dir):
    """Create vector store instance for tests"""
    store = ChromaVectorStore(
        persist_dir=os.path.join(temp_dir, "chroma"), collection_name="test_collection"
    )
    return store


@pytest.fixture
def document_service(vector_store):
    """Create document service instance for tests"""
    return DocumentService(vector_store=vector_store)


@pytest.mark.asyncio
async def test_document_loader_txt(temp_dir):
    """Test loading TXT document"""
    # Create test file
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("This is a test document.\nIt has multiple lines.\n")

    filename, pages = await DocumentLoader.load_document(test_file)

    assert filename == "test.txt"
    assert len(pages) == 1
    assert "test document" in pages[0]["content"]
    assert pages[0]["type"] == "txt"


@pytest.mark.asyncio
async def test_document_loader_md(temp_dir):
    """Test loading MD document"""
    # Create test file
    test_file = os.path.join(temp_dir, "test.md")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("# Test Document\n\nThis is markdown content.")

    filename, pages = await DocumentLoader.load_document(test_file)

    assert filename == "test.md"
    assert len(pages) == 1
    assert "markdown" in pages[0]["content"]


@pytest.mark.asyncio
async def test_document_chunker():
    """Test document chunking"""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)

    text = "This is a test document. " * 10  # ~300 chars
    chunks = chunker.chunk_text(text)

    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_embedding_service():
    """Test embedding generation"""
    service = get_embedding_service()

    # Test single embedding
    embedding = service.embed_text("test text")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, (int, float)) for x in embedding)

    # Test batch embeddings
    embeddings = service.embed_texts(["text1", "text2"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == len(embeddings[1])


@pytest.mark.asyncio
async def test_vector_store_add_and_search(vector_store):
    """Test adding documents and searching"""
    await vector_store.initialize()

    # Add test document
    test_content = "This is a test document about artificial intelligence."
    embedding = get_embedding_service().embed_text(test_content)

    doc_id = await vector_store.add_document(
        collection_name="test_collection",
        document_id="test_doc_1",
        content=test_content,
        embedding=embedding,
        metadata={"source": "test"},
    )

    assert doc_id == "test_doc_1"

    # Search
    query_embedding = get_embedding_service().embed_text("artificial intelligence")
    results = await vector_store.search(
        collection_name="test_collection", query_embedding=query_embedding, top_k=1
    )

    assert len(results) > 0
    assert "artificial intelligence" in results[0].content.lower()


@pytest.mark.asyncio
async def test_document_service_upload(document_service, temp_dir):
    """Test document upload service"""
    # Create test file
    test_file = os.path.join(temp_dir, "test_upload.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("This is a test document for upload. " * 20)

    result = await document_service.upload_document(
        file_path=test_file, document_id="test_doc_upload"
    )

    assert result["status"] == "uploaded"
    assert result["document_id"] == "test_doc_upload"
    assert result["chunks_created"] > 0


@pytest.mark.asyncio
async def test_document_service_stats(document_service):
    """Test document service stats"""
    stats = await document_service.get_stats()

    assert "total_chunks" in stats
    assert "embedding_model" in stats
    assert "chunk_size" in stats
    assert isinstance(stats["total_chunks"], int)


@pytest.mark.asyncio
async def test_document_service_search(document_service, temp_dir):
    """Test document search"""
    # Upload a test document first
    test_file = os.path.join(temp_dir, "test_search.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("This document is about machine learning and neural networks.")

    await document_service.upload_document(
        file_path=test_file, document_id="test_search_doc"
    )

    # Search
    results = await document_service.search_documents(query="machine learning", top_k=5)

    assert len(results) > 0
    assert any("machine learning" in r["content"].lower() for r in results)


def test_document_loader_validation():
    """Test file validation"""
    # Test supported format
    assert DocumentLoader.is_supported("test.pdf")
    assert DocumentLoader.is_supported("test.txt")
    assert DocumentLoader.is_supported("test.md")
    assert DocumentLoader.is_supported("test.docx")

    # Test unsupported format
    assert not DocumentLoader.is_supported("test.jpg")
    assert not DocumentLoader.is_supported("test.exe")
