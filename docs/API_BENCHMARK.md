# Benchmark API Documentation

## Overview

The Benchmark API provides endpoints for testing and comparing LLM provider performance. It supports single provider benchmarks, comparative analysis across multiple providers, and stress testing under concurrent load.

## Endpoints

### POST `/benchmark/single`

Run a benchmark test for a single provider.

**Request Body:**

```json
{
  "provider": "fireworks",
  "model": "accounts/fireworks/models/llama-v3-70b-instruct",
  "prompt": "Explain the importance of low latency LLMs",
  "temperature": 0.5,
  "max_tokens": 1024,
  "streaming": false,
  "top_p": 1.0,
  "stop_sequences": null
}
```

**Response:**

```json
{
  "run_id": "benchmark_20251219_2304_abc123",
  "provider": "fireworks",
  "model": "accounts/fireworks/models/llama-v3-70b-instruct",
  "ttft": 0.234,
  "total_time": 2.456,
  "tokens_generated": 512,
  "tokens_per_second": 208.5,
  "success": true,
  "error": null,
  "response_preview": "Low latency LLMs are crucial..."
}
```

### POST `/benchmark/compare`

Compare multiple providers with the same prompt.

**Request Body:**

```json
{
  "providers": ["fireworks", "groq", "nvidia", "deepinfra"],
  "prompt": "Explain the importance of low latency LLMs",
  "model": null,
  "temperature": 0.5,
  "max_tokens": 1024,
  "streaming": false
}
```

**Response:**

```json
{
  "run_id": "benchmark_20251219_2304_abc123",
  "prompt": "Explain the importance of low latency LLMs",
  "results": [
    {
      "provider": "groq",
      "model": "llama-3.3-70b-versatile",
      "ttft": 0.123,
      "total_time": 1.456,
      "tokens_per_second": 351.2,
      "success": true
    },
    {
      "provider": "fireworks",
      "model": "accounts/fireworks/models/llama-v3-70b-instruct",
      "ttft": 0.234,
      "total_time": 2.456,
      "tokens_per_second": 208.5,
      "success": true
    }
  ],
  "fastest_provider": "groq",
  "highest_throughput": "groq",
  "rankings": {
    "groq": 1,
    "fireworks": 2,
    "nvidia": 3,
    "deepinfra": 4
  }
}
```

### POST `/benchmark/stress`

Run a stress test with concurrent requests.

**Request Body:**

```json
{
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "prompt": "Explain the importance of low latency LLMs",
  "concurrent_requests": 10,
  "duration_seconds": 60,
  "temperature": 0.5,
  "max_tokens": 1024
}
```

**Response:**

```json
{
  "run_id": "benchmark_20251219_2304_abc123",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "total_requests": 450,
  "successful_requests": 445,
  "failed_requests": 5,
  "avg_response_time": 1.234,
  "min_response_time": 0.987,
  "max_response_time": 2.456,
  "requests_per_second": 7.5,
  "error_rate": 1.11,
  "errors": [...]
}
```

### GET `/benchmark/run/{run_id}`

Get detailed information about a specific benchmark run.

**Response:**

```json
{
  "id": "benchmark_20251219_2304_abc123",
  "run_type": "compare",
  "prompt": "Explain the importance of low latency LLMs",
  "status": "completed",
  "created_at": "2025-12-19T23:04:00Z",
  "completed_at": "2025-12-19T23:04:15Z",
  "results": [...]
}
```

### GET `/benchmark/history`

List recent benchmark runs.

**Query Parameters:**

- `limit` (int, default=50): Maximum number of runs to return
- `provider` (string, optional): Filter by provider name

**Response:**

```json
[
  {
    "id": "benchmark_20251219_2304_abc123",
    "run_type": "compare",
    "prompt": "Explain the importance...",
    "status": "completed",
    "created_at": "2025-12-19T23:04:00Z",
    "completed_at": "2025-12-19T23:04:15Z"
  }
]
```

## Metrics Endpoints

### GET `/metrics/providers`

Get aggregated metrics for all providers.

**Query Parameters:**

- `days` (int, default=7): Number of days to look back

**Response:**

```json
[
  {
    "provider": "groq",
    "total_runs": 150,
    "success_rate": 98.5,
    "avg_tokens_per_second": 350.2,
    "avg_ttft": 0.123,
    "total_tokens": 76800
  }
]
```

### GET `/metrics/provider/{provider_name}`

Get detailed metrics for a specific provider.

**Query Parameters:**

- `days` (int, default=7): Number of days to look back
- `model` (string, optional): Filter by model name

### GET `/metrics/models/{model_name}/comparison`

Compare the same model across different providers.

**Response:**

```json
{
  "model_name": "llama-3-70b-instruct",
  "providers": [
    {
      "provider": "fireworks",
      "avg_tokens_per_second": 208.5,
      "avg_ttft": 0.234
    }
  ],
  "best_provider": "fireworks",
  "fastest_provider": "groq"
}
```

### GET `/metrics/trends`

Get performance trends over time.

**Query Parameters:**

- `provider` (string, optional): Filter by provider
- `metric` (string, default="tokens_per_second"): Metric to track
- `period` (string, default="7d"): Time period (1d, 7d, 30d, 90d)
- `model` (string, optional): Filter by model

### GET `/metrics/leaderboard`

Get performance leaderboard.

**Query Parameters:**

- `metric` (string, default="tokens_per_second"): Metric to rank by
- `model_filter` (string, optional): Filter by model
- `days` (int, default=7): Number of days to look back

### GET `/metrics/export`

Export metrics data.

**Query Parameters:**

- `format` (string, default="json"): Export format (json, csv)
- `provider` (string, optional): Filter by provider
- `days` (int, default=30): Number of days to export

## Supported Providers

All endpoints support the following providers:

- `ollama` - Local inference
- `huggingface` - Hugging Face Inference API
- `gemini` - Google Gemini
- `ai21` - AI21 Labs
- `cerebras` - Cerebras
- `groq` - Groq (ultra-fast)
- `nvidia` - NVIDIA AI
- `openrouter` - OpenRouter
- `fireworks` - Fireworks AI
- `deepinfra` - Deep Infra
- `anyscale` - Anyscale
- `lepton` - Lepton AI
- `octoai` - OctoAI
- `together` - Together AI
- `mistral` - Mistral AI
- `perplexity` - Perplexity AI

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Internal server error

Error responses include a `detail` field with error information:

```json
{
  "detail": "Provider 'invalid' not found. Available: groq, fireworks, ..."
}
```
