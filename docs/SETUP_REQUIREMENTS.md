# Backend Setup Requirements Analysis

## Executive Summary

Your DurgasAI backend can run in **minimal mode** with just Ollama (local LLM) or can be fully configured with multiple AI providers. Most services are **optional** and gracefully degrade when API keys are missing.

---

## Configuration Categories

### 🔴 **REQUIRED** (Backend won't work without these)

1. **Server Configuration** ✅ (Already configured)

   - `host`: "0.0.0.0" (default)
   - `port`: 8000 (default)
   - `environment`: "development" or "production"
   - `debug`: true/false

2. **Security Keys** ⚠️ (Must change for production)

   - `jwt_secret_key`: Currently "your-super-secret-jwt-key-change-in-production"
   - `api_key`: Currently "your-api-key-for-extension"
   - **Action Required**: Generate secure random keys for production

3. **At Least ONE LLM Provider** ✅ (Ollama works out of the box)
   - Default: Ollama (local, no API key needed)
   - Requires: Ollama installed and running on `http://localhost:11434`

---

### 🟡 **OPTIONAL BUT RECOMMENDED** (For full functionality)

#### **LLM Providers** (Choose based on your needs)

| Provider        | API Key Required  | Use Case                | Cost                | Setup Difficulty      |
| --------------- | ----------------- | ----------------------- | ------------------- | --------------------- |
| **Ollama**      | ❌ No             | Local inference, free   | Free                | Easy (install Ollama) |
| **Groq**        | ✅ Yes            | Ultra-fast inference    | Pay-per-use         | Easy                  |
| **Gemini**      | ✅ Yes            | Google's models, vision | Free tier available | Easy                  |
| **HuggingFace** | ✅ Yes (optional) | Open models, multimodal | Free tier           | Easy                  |
| **AI21**        | ✅ Yes            | Jamba models            | Pay-per-use         | Easy                  |
| **Cerebras**    | ✅ Yes            | High-performance        | Pay-per-use         | Easy                  |
| **NVIDIA**      | ✅ Yes            | Enterprise models       | Pay-per-use         | Easy                  |

#### **Database & Storage**

- **SQLite**: ✅ Default (no setup needed)
- **ChromaDB**: ✅ Default (creates `./data/chroma` automatically)
- **Redis**: ❌ Optional (for caching, set `use_redis: false` if not using)

#### **Embeddings**

- **Local**: ✅ Default (uses sentence-transformers, no API key)
- **HuggingFace**: Optional (requires API key)
- **Gemini**: Optional (requires API key)

---

### 🟢 **OPTIONAL** (Nice to have)

- **Redis**: For caching and session storage (set `use_redis: false` to disable)
- **Additional LLM Providers**: Only needed if you want specific models
- **Council Agent**: Multi-model orchestration (works with any configured providers)

---

## Minimum Setup (Get Started Fast)

### What You Need

1. ✅ Python 3.10+ (already have)
2. ✅ Dependencies installed (`pip install -r requirements.txt`)
3. ✅ Config file (`config/config.json` - already created)
4. ✅ Ollama installed and running (for local LLM)

### What to Configure

1. **Security Keys** (in `config/config.json`):

   ```json
   "security": {
     "jwt_secret_key": "generate-random-32-char-string",
     "api_key": "generate-random-api-key"
   }
   ```

2. **Ollama** (if using local LLM):
   - Install: <https://ollama.ai>
   - Run: `ollama serve` (or start as service)
   - Verify: `curl http://localhost:11434/api/tags`

### Result

- ✅ Backend runs on port 8000
- ✅ Chat API works with Ollama
- ✅ Health check works
- ✅ All core features functional

---

## Full Setup (All Features Enabled)

### Step-by-Step API Key Acquisition

#### 1. **Google Gemini** (Recommended - Free tier available)

- **Get Key**: <https://makersuite.google.com/app/apikey>
- **Free Tier**: 60 requests/minute
- **Use Cases**: Chat, vision, embeddings, image generation
- **Config**: `llm.providers.gemini.api_key`

#### 2. **Groq** (Recommended - Very fast, free tier)

- **Get Key**: <https://console.groq.com/keys>
- **Free Tier**: Generous limits
- **Use Cases**: Ultra-fast chat, council agent
- **Config**: `llm.providers.groq.api_key`

#### 3. **HuggingFace** (Recommended - Free tier)

- **Get Key**: <https://huggingface.co/settings/tokens>
- **Free Tier**: Limited but available
- **Use Cases**: Open models, multimodal (text-to-image, etc.)
- **Config**: `llm.providers.huggingface.api_key`

#### 4. **AI21 Labs** (Optional)

- **Get Key**: <https://studio.ai21.com/account/api-keys>
- **Use Cases**: Jamba models, NLP tasks
- **Config**: `llm.providers.ai21.api_key`

#### 5. **Cerebras** (Optional)

- **Get Key**: <https://www.cerebras.ai/api-keys>
- **Use Cases**: High-performance inference
- **Config**: `llm.providers.cerebras.api_key`

#### 7. **NVIDIA** (Optional)

- **Get Key**: <https://build.nvidia.com/>
- **Use Cases**: Enterprise models, video generation
- **Config**: `llm.providers.nvidia.api_key`

#### 8. **AWS Bedrock** (Optional - More complex)

- **Requirements**: AWS account, Bedrock access enabled
- **Get Keys**: AWS IAM console
- **Use Cases**: Claude models via AWS
- **Config**: `llm.providers.bedrock.access_key`, `secret_key`, `region`

---

## Configuration Priority

### For Development

1. **Ollama** (local, free) - ✅ Already configured
2. **Groq** (fast, free tier) - Recommended
3. **Gemini** (free tier) - Recommended
4. **HuggingFace** (free tier) - For multimodal

### For Production

1. **At least 2-3 providers** for redundancy
2. **Groq** for speed
3. **Gemini** for reliability
4. **HuggingFace** for multimodal features

---

## Current Configuration Status

### ✅ Already Configured (Working)

- Server settings (host, port, debug)
- Database (SQLite)
- ChromaDB (local storage)
- Ollama (default LLM provider)
- Local embeddings
- Security keys (⚠️ need to change for production)

### ❌ Not Configured (Set to `null`)

- All cloud LLM provider API keys
- Redis (disabled by default)

---

## Security Checklist

### ⚠️ **MUST CHANGE BEFORE PRODUCTION:**

1. **JWT Secret Key**:

   ```python
   import secrets
   secrets.token_urlsafe(32)  # Generate secure key
   ```

2. **API Key**:

   ```python
   secrets.token_urlsafe(24)  # Generate secure key
   ```

3. **CORS Origins**: Update to your actual frontend URLs

4. **Environment**: Set to `"production"` in production config

---

## Service Dependencies

### What Works Without API Keys

- ✅ Server startup
- ✅ Health checks
- ✅ Ollama (local)
- ✅ Local embeddings
- ✅ Database operations
- ✅ Basic API endpoints

### What Requires API Keys

- ❌ Cloud LLM providers (Gemini, Groq, etc.)
- ❌ Multimodal features (text-to-image, etc.)
- ❌ Cloud embeddings
- ❌ Specific provider features

### Graceful Degradation

- Services log warnings when API keys are missing
- Backend continues to run
- Only endpoints using missing providers fail
- Default provider (Ollama) works without keys

---

## Next Steps

See `SETUP_TASKS.md` for detailed step-by-step setup instructions broken into smaller tasks.
