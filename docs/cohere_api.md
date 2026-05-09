# Cohere API Integration Documentation

## Overview

The Cohere API integration provides enterprise-grade LLM capabilities with advanced RAG (Retrieval-Augmented Generation) features, including web search connectors, semantic embeddings, text classification, and document reranking.

## Configuration

Add your Cohere API key to `config/config.json`:

```json
{
  "llm": {
    "providers": {
      "cohere": {
        "api_key": "YOUR_API_KEY",
        "base_url": "https://api.cohere.ai/v1",
        "model": "command-r-plus",
        "embed_model": "embed-english-v3.0",
        "rerank_model": "rerank-english-v3.0",
        "classify_model": "embed-english-v3.0"
      }
    }
  }
}
```

## API Endpoints

### Chat (via LLM Provider)

Cohere chat is available through the main chat endpoint using the `cohere` provider.

**Endpoint:** `POST /api/v1/chat`

**Request:**

```json
{
  "message": "What is artificial intelligence?",
  "provider": "cohere",
  "model": "command-r-plus",
  "temperature": 0.7,
  "max_tokens": 2048,
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?"
    }
  ]
}
```

**Response:**

```json
{
  "message": "Artificial intelligence (AI) is...",
  "provider": "cohere",
  "model": "command-r-plus",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350
  },
  "finish_reason": "COMPLETE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Features:**

- Automatic web search via RAG connectors
- Citations and source documents
- Conversation history support
- Streaming support via `/api/v1/chat/stream`

### Summarize

**Endpoint:** `POST /api/v1/cohere/summarize`

**Request:**

```json
{
  "text": "Long text to summarize...",
  "model": "command",
  "length": "medium",
  "format": "paragraph",
  "extractiveness": "medium",
  "temperature": 0.3
}
```

**Response:**

```json
{
  "summary": "Summary text...",
  "id": "summary-id",
  "meta": {
    "api_version": { "version": "1" },
    "tokens": { "input_tokens": 500, "output_tokens": 100 }
  }
}
```

### Embeddings

**Endpoint:** `POST /api/v1/cohere/embed`

**Request:**

```json
{
  "texts": ["text1", "text2", "text3"],
  "model": "embed-english-v3.0",
  "input_type": "search_document",
  "truncate": "END"
}
```

**Response:**

```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "id": "embed-id",
  "texts": ["text1", "text2", "text3"],
  "meta": {}
}
```

**Input Types:**

- `search_document`: For documents in a search index
- `search_query`: For search queries
- `classification`: For classification tasks
- `clustering`: For clustering tasks
- `semantic_similarity`: For similarity tasks

### Classification

**Endpoint:** `POST /api/v1/cohere/classify`

**Request:**

```json
{
  "inputs": ["Confirm your email address", "hey i need u to send some $"],
  "model": "embed-english-v3.0",
  "examples": [
    { "text": "Dermatologists don't like her!", "label": "Spam" },
    { "text": "Your parcel will be delivered today", "label": "Not spam" }
  ],
  "truncate": "END"
}
```

**Response:**

```json
{
  "classifications": [
    {
      "input": "Confirm your email address",
      "prediction": "Not spam",
      "confidence": 0.95,
      "labels": { "Spam": 0.05, "Not spam": 0.95 }
    }
  ],
  "id": "classify-id",
  "meta": {}
}
```

### Reranking

**Endpoint:** `POST /api/v1/cohere/rerank`

**Request:**

```json
{
  "query": "What is the capital of the United States?",
  "documents": [
    "Carson City is the capital of Nevada",
    "Washington, D.C. is the capital of the United States",
    "The capital of the Northern Mariana Islands is Saipan"
  ],
  "model": "rerank-english-v3.0",
  "top_n": 3,
  "return_documents": true
}
```

**Response:**

```json
{
  "results": [
    {
      "index": 1,
      "relevance_score": 0.95,
      "document": "Washington, D.C. is the capital of the United States"
    },
    {
      "index": 0,
      "relevance_score": 0.6,
      "document": "Carson City is the capital of Nevada"
    }
  ],
  "id": "rerank-id",
  "meta": {}
}
```

### Connectors

**List Connectors:**

- `GET /api/v1/cohere/connectors`

**Get Connector:**

- `GET /api/v1/cohere/connectors/{connector_id}`

**Create Connector:**

- `POST /api/v1/cohere/connectors`

```json
{
  "name": "Custom Connector",
  "url": "https://connector.example.com/search",
  "description": "Custom data source connector"
}
```

**Delete Connector:**

- `DELETE /api/v1/cohere/connectors/{connector_id}`

### Embed Jobs (Async)

**Create Embed Job:**

- `POST /api/v1/cohere/embed-jobs`

```json
{
  "model": "embed-english-v3.0",
  "dataset_id": "my-dataset",
  "input_type": "search_document"
}
```

**List Embed Jobs:**

- `GET /api/v1/cohere/embed-jobs`

**Get Embed Job Status:**

- `GET /api/v1/cohere/embed-jobs/{job_id}`

**Cancel Embed Job:**

- `POST /api/v1/cohere/embed-jobs/{job_id}/cancel`

### Datasets

**List Datasets:**

- `GET /api/v1/cohere/datasets`

**Get Dataset:**

- `GET /api/v1/cohere/datasets/{dataset_id}`

**Get Dataset Usage:**

- `GET /api/v1/cohere/datasets/usage`

**Delete Dataset:**

- `DELETE /api/v1/cohere/datasets/{dataset_id}`

### Fine-tuning

**List Fine-tuned Models:**

- `GET /api/v1/cohere/finetuning/models`

**Get Fine-tuned Model:**

- `GET /api/v1/cohere/finetuning/models/{model_id}`

**Get Training Events:**

- `GET /api/v1/cohere/finetuning/models/{model_id}/events`

**Get Training Metrics:**

- `GET /api/v1/cohere/finetuning/models/{model_id}/metrics`

### Tokenization

**Tokenize:**

- `POST /api/v1/cohere/tokenize`

```json
{
  "text": "tokenize me! :D",
  "model": "command"
}
```

**Detokenize:**

- `POST /api/v1/cohere/detokenize`

```json
{
  "tokens": [8466, 5169, 2594, 8, 2792, 43],
  "model": "command"
}
```

## Use Cases

### 1. Chat with Web Search

Use Cohere's built-in web search connector for real-time information:

```python
# Via chat endpoint
POST /api/v1/chat
{
  "message": "What happened in AI news today?",
  "provider": "cohere",
  "model": "command-r-plus"
}
```

The response includes:

- Citations from web sources
- Source documents with URLs
- Search queries used

### 2. Enhanced RAG with Reranking

Improve search results by reranking:

```python
# In your RAG retriever
from app.services.rag.retriever import RAGRetriever

retriever = RAGRetriever()
results = await retriever.retrieve_with_reranking(
    query="machine learning",
    k=10,
    rerank_top_n=5
)
```

### 3. Content Classification

Classify user-generated content:

```python
POST /api/v1/cohere/classify
{
  "inputs": ["user comment text"],
  "examples": [
    {"text": "positive example", "label": "Positive"},
    {"text": "negative example", "label": "Negative"}
  ]
}
```

### 4. Semantic Search

Use Cohere embeddings for semantic search:

```python
POST /api/v1/cohere/embed
{
  "texts": ["document text"],
  "input_type": "search_document"
}
```

## Models

### Chat Models

- `command`: General-purpose chat
- `command-r`: Enhanced reasoning
- `command-r-plus`: Best performance
- `command-light`: Faster, lighter
- `command-a`: Alternative variant

### Embedding Models

- `embed-english-v3.0`: Latest English embeddings
- `embed-english-light-v3.0`: Lightweight English
- `embed-multilingual-v3.0`: Multilingual support
- `embed-v4.0`: Latest version

### Reranking Models

- `rerank-english-v3.0`: Latest English reranking
- `rerank-multilingual-v3.0`: Multilingual reranking

## Rate Limits

Cohere API has rate limits based on your plan:

- Trial: 20 requests per endpoint per month
- Production: Varies by plan

Check response headers:

- `x-trial-endpoint-call-limit`: Trial limit
- `x-trial-endpoint-call-remaining`: Remaining calls
- `x-endpoint-monthly-call-limit`: Monthly limit

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (invalid API key)
- `403`: Forbidden (insufficient permissions)
- `429`: Rate limit exceeded
- `500`: Server error

Error response format:

```json
{
  "detail": "Error message"
}
```

## Best Practices

1. **Use appropriate input types** for embeddings (search_document vs search_query)
2. **Batch requests** when possible (up to 96 texts per request)
3. **Cache embeddings** for frequently accessed documents
4. **Use reranking** to improve search result quality
5. **Monitor usage** via response headers and database metrics
6. **Handle rate limits** with exponential backoff

## Integration Examples

### Python Client Example

```python
import httpx

async def cohere_chat(message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chat",
            json={
                "message": message,
                "provider": "cohere",
                "model": "command-r-plus"
            }
        )
        return response.json()
```

### JavaScript Example

```javascript
async function cohereChat(message) {
  const response = await fetch('http://localhost:8000/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      provider: 'cohere',
      model: 'command-r-plus',
    }),
  });
  return await response.json();
}
```

## Database Models

Usage is tracked in the database:

- `cohere_usage`: Tracks API calls, tokens, and success rates
- `cohere_connector_logs`: Tracks connector usage and performance

## Support

For more information:

- Cohere API Docs: https://docs.cohere.com/reference/about
- Cohere Models: https://docs.cohere.com/docs/models
