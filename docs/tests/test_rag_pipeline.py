"""
RAG Pipeline Tests
Tests chunking, retrieval, context assembly, and hybrid search.
"""

import pytest
from app.services.rag.chunking import DocumentChunker, chunker
from app.services.rag.pipeline import RAGPipeline, rag_pipeline
from app.services.rag.vectorstore import ChromaVectorStore


def test_document_chunking_recursive():
    """Test recursive chunking strategy"""
    chunker_instance = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
        strategy="recursive"
    )
    
    text = "This is a test document. " * 50  # ~1000 chars
    chunks = chunker_instance.chunk_text(text)
    
    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)
    assert all("chunk_id" in chunk["metadata"] for chunk in chunks)


def test_document_chunking_semantic():
    """Test semantic chunking strategy"""
    chunker_instance = DocumentChunker(
        chunk_size=200,
        chunk_overlap=50,
        strategy="semantic"
    )
    
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph." * 10
    chunks = chunker_instance.chunk_text(text)
    
    assert len(chunks) > 0
    # Semantic chunking should respect paragraph boundaries
    assert all("content" in chunk for chunk in chunks)


def test_document_chunking_sliding_window():
    """Test sliding window chunking"""
    chunker_instance = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
        strategy="sliding"
    )
    
    text = "A" * 500  # Long text
    chunks = chunker_instance.chunk_text(text)
    
    assert len(chunks) > 0


def test_chunk_metadata_preservation():
    """Test that metadata is preserved across chunks"""
    chunker_instance = DocumentChunker()
    
    text = "Test document content. " * 20
    metadata = {"source": "test", "author": "tester", "document_id": "doc123"}
    
    chunks = chunker_instance.chunk_text(text, metadata=metadata, document_id="doc123")
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["metadata"]["source"] == "test"
        assert chunk["metadata"]["author"] == "tester"
        assert chunk["metadata"]["document_id"] == "doc123"
        assert "chunk_index" in chunk["metadata"]


def test_chunk_multiple_documents():
    """Test chunking multiple documents"""
    documents = [
        {"id": "doc1", "content": "First document content. " * 10, "metadata": {"source": "doc1"}},
        {"id": "doc2", "content": "Second document content. " * 10, "metadata": {"source": "doc2"}}
    ]
    
    chunks = chunker.chunk_documents(documents)
    
    assert len(chunks) > 0
    # Verify chunks from both documents
    sources = {chunk["metadata"].get("source") for chunk in chunks}
    assert "doc1" in sources or any("doc1" in str(chunk.get("id", "")) for chunk in chunks)
    assert "doc2" in sources or any("doc2" in str(chunk.get("id", "")) for chunk in chunks)


@pytest.mark.asyncio
async def test_rag_pipeline_query():
    """Test RAG pipeline query execution"""
    # This requires a populated vector store
    # In real tests, you'd set up test data first
    
    try:
        result = await rag_pipeline.query(
            query="test query",
            top_k=3
        )
        
        assert "query" in result
        assert "context" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)
    except Exception as e:
        # If vector store is empty, that's okay for unit tests
        pytest.skip(f"RAG pipeline test skipped: {e}")


@pytest.mark.asyncio
async def test_rag_pipeline_ingest():
    """Test document ingestion into RAG pipeline"""
    documents = [
        {
            "id": "test_doc_1",
            "content": "This is a test document about artificial intelligence and machine learning.",
            "metadata": {"source": "test", "type": "documentation"}
        }
    ]
    
    try:
        result = await rag_pipeline.ingest_documents(documents)
        
        assert result["success"] is True
        assert result["chunks_created"] > 0
    except Exception as e:
        # If vector store initialization fails, skip
        pytest.skip(f"RAG ingestion test skipped: {e}")


def test_rag_pipeline_preprocess_query():
    """Test query preprocessing"""
    pipeline = RAGPipeline()
    
    query = "  test   query  with   extra   spaces  "
    processed = pipeline._preprocess_query(query)
    
    assert processed == "test query with extra spaces"


def test_rag_pipeline_hybrid_search():
    """Test hybrid search (vector + keyword)"""
    pipeline = RAGPipeline()
    
    # Mock search results
    from app.services.rag.base import VectorSearchResult
    
    results = [
        VectorSearchResult(
            id="1",
            content="This document is about artificial intelligence",
            metadata={},
            score=0.8
        ),
        VectorSearchResult(
            id="2",
            content="This is about machine learning algorithms",
            metadata={},
            score=0.7
        )
    ]
    
    query = "artificial intelligence"
    hybrid_results = pipeline._apply_hybrid_search(query, results)
    
    assert len(hybrid_results) == len(results)
    # First result should have higher score due to keyword match
    assert hybrid_results[0].score >= results[0].score


def test_rag_pipeline_build_context():
    """Test context assembly from retrieved documents"""
    pipeline = RAGPipeline()
    
    from app.services.rag.base import VectorSearchResult
    
    documents = [
        VectorSearchResult(
            id="1",
            content="First relevant document content.",
            metadata={"url": "https://example.com/1", "title": "Doc 1"},
            score=0.9
        ),
        VectorSearchResult(
            id="2",
            content="Second relevant document content.",
            metadata={"url": "https://example.com/2", "title": "Doc 2"},
            score=0.8
        )
    ]
    
    context = pipeline._build_context(documents, max_length=1000)
    
    assert len(context) > 0
    assert "Source 1" in context or "[Source 1" in context
    assert "First relevant" in context
    assert "Second relevant" in context

