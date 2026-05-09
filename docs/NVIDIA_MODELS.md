# NVIDIA AI Models Catalog

Complete catalog of all available NVIDIA AI models with capabilities, use cases, and specifications.

## Model Categories

### Chat Models (50+ models)

#### NVIDIA Models

- **nvidia/nemotron-4-340b-instruct** - Flagship 340B instruction model
  - Context: 131K tokens
  - Best for: High-quality general purpose tasks
- **nvidia/llama-3.1-nemotron-ultra-253b-v1** - Ultra-large 253B model
  - Context: 131K tokens
  - Best for: Complex reasoning, long context
- **nvidia/llama-3.3-nemotron-super-49b-v1** - Super 49B model (default)
  - Context: 131K tokens
  - Best for: Balanced quality and speed
- **nvidia/llama-3.3-nemotron-super-49b-v1.5** - Updated 49B model
  - Context: 131K tokens
  - Best for: Latest improvements
- **nv-mistralai/mistral-nemo-12b-instruct** - NVIDIA-optimized Mistral
  - Context: 32K tokens
  - Best for: Fast inference

#### Meta Models

- **meta/llama2-70b** - LLaMA 2 base
- **meta/llama3-8b** - LLaMA 3 8B base
- **meta/llama3-8b-instruct** - LLaMA 3 8B instruction
- **meta/llama3-70b** - LLaMA 3 70B base
- **meta/llama3-70b-instruct** - LLaMA 3 70B instruction
- **meta/llama-3.1-405b-instruct** - Largest 405B model (131K context)
- **meta/llama-3.2-1b-instruct** - Ultra-lightweight 1B
- **meta/llama-3.2-3b-instruct** - Lightweight 3B
- **meta/llama-3.3-70b-instruct** - Latest 70B model
- **meta/llama-4-scout-17b-16e-instruct** - Scout with 16 experts
- **meta/llama-4-maverick-17b-128e-instruct** - Maverick with 128 experts
- **meta/codellama-70b** - Code generation model

#### Google Models

- **google/gemma-2b** - Lightweight 2B model
- **google/gemma-7b** - 7B model
- **google/gemma-2-9b-it** - Gemma 2 9B instruction
- **google/gemma-3-27b-it** - Gemma 3 27B instruction
- **google/codegemma-7b** - Code generation

#### Microsoft Models

- **microsoft/phi-3-mini-128k-instruct** - Phi-3 mini (128K context)
- **microsoft/phi-3.5-moe-instruct** - Phi-3.5 MoE
- **microsoft/phi-4-multimodal-instruct** - Phi-4 vision model

#### Mistral Models

- **mistralai/mistral-7b-instruct-v0.2** - Mistral 7B v0.2
- **mistralai/mistral-large** - Mistral large
- **mistralai/mixtral-8x22b-instruct-v0.1** - Mixtral 8x22B MoE

#### DeepSeek Models

- **deepseek-ai/deepseek-r1** - Reasoning model for complex problems

#### OpenAI Models

- **openai/gpt-oss-120b** - Open-source 120B GPT
- **openai/gpt-oss-20b** - Open-source 20B GPT

#### Qwen Models

- **qwen/qwen3-235b-a22b** - Qwen 3 235B with 22B active

#### Snowflake Models

- **snowflake/arctic** - Snowflake Arctic instruction model

#### Moonshot Models

- **moonshotai/kimi-k2-instruct** - Long context (131K tokens)

### Vision Models

- **meta/llama-3.2-11b-vision-instruct** - 11B vision model
  - Context: 128K tokens
  - Best for: Fast image analysis
- **meta/llama-3.2-90b-vision-instruct** - 90B vision model (default)
  - Context: 128K tokens
  - Best for: High-quality image understanding
- **microsoft/phi-4-multimodal-instruct** - Phi-4 multimodal
  - Context: 131K tokens
  - Best for: Efficient multimodal tasks

### Embedding Models

- **nvidia/nv-embedqa-e5-v5** - Q&A optimized (default)
  - Dimensions: 768 (configurable: 256, 512, 768, 1024)
  - Best for: Semantic search, RAG
- **nvidia/nv-embed-v2** - General-purpose embeddings
  - Dimensions: 768 (configurable)
  - Best for: General embedding tasks

## Model Capabilities Matrix

| Model                | Chat | Vision | Code | Reasoning | Long Context |
| -------------------- | ---- | ------ | ---- | --------- | ------------ |
| nemotron-4-340b      | ✅   | ❌     | ❌   | ❌        | ✅ (131K)    |
| llama-3.1-ultra-253b | ✅   | ❌     | ❌   | ❌        | ✅ (131K)    |
| llama-3.3-super-49b  | ✅   | ❌     | ❌   | ❌        | ✅ (131K)    |
| llama-3.2-90b-vision | ✅   | ✅     | ❌   | ❌        | ✅ (128K)    |
| deepseek-r1          | ✅   | ❌     | ❌   | ✅        | ✅ (64K)     |
| codellama-70b        | ✅   | ❌     | ✅   | ❌        | ✅ (16K)     |
| phi-4-multimodal     | ✅   | ✅     | ❌   | ❌        | ✅ (131K)    |

## Use Case Recommendations

### General Chat

- **Best**: `nvidia/llama-3.3-nemotron-super-49b-v1`
- **Alternative**: `nvidia/llama-3.1-nemotron-ultra-253b-v1` (higher quality)

### Complex Reasoning

- **Best**: `deepseek-ai/deepseek-r1`
- **Alternative**: `nvidia/nemotron-4-340b-instruct`

### Code Generation

- **Best**: `meta/codellama-70b`
- **Alternative**: `google/codegemma-7b` (faster)

### Image Analysis

- **Best**: `meta/llama-3.2-90b-vision-instruct`
- **Alternative**: `meta/llama-3.2-11b-vision-instruct` (faster)

### Long Context (100K+ tokens)

- **Best**: `moonshotai/kimi-k2-instruct`
- **Alternative**: `meta/llama-3.1-405b-instruct`

### Embeddings

- **Best**: `nvidia/nv-embedqa-e5-v5` (for Q&A)
- **Alternative**: `nvidia/nv-embed-v2` (general purpose)

## Pricing & Rate Limits

Refer to NVIDIA's official documentation for current pricing and rate limits:
[https://build.nvidia.com/explore/discover](https://build.nvidia.com/explore/discover)

## Model Availability

Model availability may vary by region and time. Use the `/api/v1/nvidia/chat/models` endpoint to get current available models.

## Migration Guide

### From OpenAI

1. Replace `gpt-4` → `nvidia/llama-3.3-nemotron-super-49b-v1`
2. Replace `gpt-4-vision` → `meta/llama-3.2-90b-vision-instruct`
3. Replace `text-embedding-ada-002` → `nvidia/nv-embedqa-e5-v5`

### From Anthropic

1. Replace `claude-3-opus` → `nvidia/nemotron-4-340b-instruct`
2. Replace `claude-3-sonnet` → `nvidia/llama-3.1-nemotron-ultra-253b-v1`

### From Cohere

1. Replace `command-r-plus` → `nvidia/llama-3.3-nemotron-super-49b-v1`
2. Replace `embed-english-v3.0` → `nvidia/nv-embedqa-e5-v5`
