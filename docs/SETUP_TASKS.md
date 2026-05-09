# Backend Setup Tasks - Step by Step

## Overview

This document breaks down the backend setup into smaller, manageable tasks. Complete them in order for a smooth setup experience.

---

## Phase 1: Basic Setup (Required - 15 minutes)

### Task 1.1: Verify Python Environment ✅

- [x] Python 3.10+ installed
- [x] Virtual environment created
- [x] Dependencies installed (`pip install -r requirements.txt`)

**Status**: Already done

---

### Task 1.2: Generate Security Keys ⚠️ **REQUIRED**

**What**: Generate secure random keys for JWT and API authentication

**Why**: Current keys are placeholders and must be changed

**How**:

```python
# Run in Python console:
import secrets

# Generate JWT secret key (32+ characters)
jwt_key = secrets.token_urlsafe(32)
print(f"JWT Secret Key: {jwt_key}")

# Generate API key (24+ characters)
api_key = secrets.token_urlsafe(24)
print(f"API Key: {api_key}")
```

**Action**:

1. Generate keys using above code
2. Update `config/config.json`:

   ```json
   "security": {
     "jwt_secret_key": "<generated-jwt-key>",
     "api_key": "<generated-api-key>"
   }
   ```

**Time**: 2 minutes

---

### Task 1.3: Install and Configure Ollama ✅

**What**: Set up local LLM provider (default, no API key needed)

**Why**: Required for basic chat functionality

**How**:

1. **Install Ollama**:

   - Windows: Download from <https://ollama.ai/download>
   - Or: `winget install Ollama.Ollama`

2. **Start Ollama**:

   ```bash
   ollama serve
   ```

   (Or install as Windows service)

3. **Pull default model**:

   ```bash
   ollama pull llama3
   ```

4. **Verify**:

   ```bash
   curl http://localhost:11434/api/tags
   ```

**Verify in config**: `config/config.json` should have:

```json
"llm": {
  "default_provider": "ollama",
  "providers": {
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama3"
    }
  }
}
```

**Time**: 5-10 minutes

---

### Task 1.4: Test Basic Backend Startup ✅

**What**: Verify backend starts and basic endpoints work

**How**:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Verify**:

1. Server starts without errors
2. Visit <http://localhost:8000/docs>
3. Test `/api/v1/health` endpoint
4. Test `/` root endpoint

**Time**: 2 minutes

**Status**: Should work now ✅

---

## Phase 2: Essential API Keys (Recommended - 20 minutes)

### Task 2.1: Get Google Gemini API Key 🟡

**Priority**: High (free tier, versatile)

**Steps**:

1. Go to: <https://makersuite.google.com/app/apikey>
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

**Update Config**:

```json
"llm": {
  "providers": {
    "gemini": {
      "api_key": "your-actual-gemini-api-key-here"
    }
  }
}
```

**Benefits**:

- Free tier: 60 requests/minute
- Chat, vision, embeddings, image generation
- Used by council agent

**Time**: 5 minutes

---

### Task 2.2: Get Groq API Key 🟡

**Priority**: High (very fast, free tier)

**Steps**:

1. Go to: <https://console.groq.com/>
2. Sign up/login
3. Navigate to API Keys
4. Create new key
5. Copy the key

**Update Config**:

```json
"llm": {
  "providers": {
    "groq": {
      "api_key": "your-actual-groq-api-key-here"
    }
  }
}
```

**Benefits**:

- Ultra-fast inference
- Free tier available
- Great for council agent

**Time**: 5 minutes

---

### Task 2.3: Get HuggingFace API Key 🟡

**Priority**: Medium (free tier, multimodal)

**Steps**:

1. Go to: <https://huggingface.co/>
2. Sign up/login
3. Go to Settings → Access Tokens
4. Create new token (read access)
5. Copy the token

**Update Config**:

```json
"llm": {
  "providers": {
    "huggingface": {
      "api_key": "hf_your-actual-token-here"
    }
  }
}
```

**Benefits**:

- Free tier available
- Text-to-image, image-to-text
- Open source models

**Time**: 5 minutes

---

### Task 2.4: Test API Keys Work

**What**: Verify configured API keys are accepted

**How**:

1. Restart backend: `uvicorn app.main:app --reload`
2. Check logs for warnings (should see no API key warnings for configured providers)
3. Test endpoints:
   - `/api/v1/chat` with `provider: "gemini"`
   - `/api/v1/chat` with `provider: "groq"`

**Time**: 3 minutes

---

## Phase 3: Optional Providers (As Needed)

### Task 3.1: AI21 Labs API Key 🟢

**When**: If you want Jamba models

**Steps**:

1. Go to: <https://studio.ai21.com/>
2. Sign up
3. Get API key from account settings

**Update**: `llm.providers.ai21.api_key`

**Time**: 5 minutes

---

### Task 3.2: Alibaba Cloud API Key 🟢

**When**: If you need multilingual/vision models

**Steps**:

1. Go to: <https://dashscope.console.aliyun.com/>
2. Sign up for Alibaba Cloud
3. Create API key in DashScope console

**Update**: `llm.providers.alibaba.api_key`

**Time**: 10 minutes

---

### Task 3.3: Cerebras API Key 🟢

**When**: If you need high-performance inference

**Steps**:

1. Go to: <https://www.cerebras.ai/>
2. Sign up
3. Get API key from dashboard

**Update**: `llm.providers.cerebras.api_key`

**Time**: 5 minutes

---

### Task 3.4: NVIDIA API Key 🟢

**When**: If you need NVIDIA models or video generation

**Steps**:

1. Go to: <https://build.nvidia.com/>
2. Sign up
3. Get API key

**Update**: `llm.providers.nvidia.api_key`

**Time**: 5 minutes

---

### Task 3.5: AWS Bedrock Setup 🟢

**When**: If you want AWS-hosted Claude models

**Steps**:

1. AWS account required
2. Enable Bedrock in AWS console
3. Create IAM user with Bedrock permissions
4. Get access key and secret key

**Update**:

```json
"llm": {
  "providers": {
    "bedrock": {
      "access_key": "your-aws-access-key",
      "secret_key": "your-aws-secret-key",
      "region": "us-west-2"
    }
  }
}
```

**Time**: 15-20 minutes

---

### Task 3.6: Google Vertex AI Setup 🟢

**When**: If you want GCP-hosted models

**Steps**:

1. GCP account required
2. Enable Vertex AI API
3. Create service account
4. Get project ID and API key

**Update**:

```json
"llm": {
  "providers": {
    "vertex": {
      "project_id": "your-gcp-project-id",
      "api_key": "your-vertex-api-key",
      "location": "us-central1"
    }
  }
}
```

**Time**: 15-20 minutes

---

## Phase 4: Optional Services

### Task 4.1: Redis Setup (Optional) 🟢

**When**: If you want caching and session storage

**Steps**:

1. Install Redis:

   - Windows: Use WSL or Docker
   - Or: Download from <https://redis.io/download>

2. Start Redis:

   ```bash
   redis-server
   ```

3. Update Config:

   ```json
   "redis": {
     "url": "redis://localhost:6379",
     "use_redis": true
   }
   ```

**Time**: 10 minutes

---

### Task 4.2: Configure CORS Origins 🟡

**What**: Update allowed origins for your frontend

**Why**: Security - only allow your actual frontend URLs

**Update**:

```json
"cors": {
  "origins": "chrome-extension://your-extension-id,http://localhost:3000,https://yourdomain.com"
}
```

**Time**: 2 minutes

---

### Task 4.3: Production Configuration 🟡

**What**: Create production-specific config

**Steps**:

1. Copy `config/config.example.json` to `config/config.prod.json`
2. Update:
   - `server.environment`: "production"
   - `server.debug`: false
   - `security.jwt_secret_key`: (use strong key)
   - `security.api_key`: (use strong key)
   - `cors.origins`: (only production URLs)
   - `logging.level`: "INFO"

**Time**: 5 minutes

---

## Phase 5: Testing & Validation

### Task 5.1: Test All Configured Providers

**What**: Verify each configured provider works

**How**:

1. Test each provider via `/api/v1/chat`:

   ```json
   {
     "message": "Hello",
     "provider": "ollama" // or gemini, groq, etc.
   }
   ```

2. Check logs for errors

**Time**: 10 minutes

---

### Task 5.2: Test Multimodal Features

**What**: If HuggingFace/Gemini configured, test:

- Text-to-image
- Image-to-text
- Speech-to-text
- Text-to-speech

**Time**: 10 minutes

---

### Task 5.3: Test Council Agent

**What**: If multiple providers configured, test council agent

**Endpoint**: `/api/v1/council/chat`

**Time**: 5 minutes

---

## Summary Checklist

### Minimum Setup (Backend Works)

- [x] Python environment
- [x] Dependencies installed
- [x] Config file created
- [ ] Security keys generated and updated
- [ ] Ollama installed and running
- [ ] Backend starts successfully

### Recommended Setup (Full Features)

- [ ] Gemini API key
- [ ] Groq API key
- [ ] HuggingFace API key
- [ ] CORS origins configured
- [ ] All providers tested

### Optional Setup (Advanced)

- [ ] Additional provider API keys
- [ ] Redis configured
- [ ] Production config created
- [ ] All features tested

---

## Quick Reference: Config File Structure

```json
{
  "server": {
    /* host, port, debug, environment */
  },
  "llm": {
    "default_provider": "ollama",
    "providers": {
      "ollama": {
        /* base_url, model */
      },
      "gemini": { "api_key": "..." },
      "groq": { "api_key": "..." },
      "huggingface": { "api_key": "..." }
      /* ... other providers ... */
    }
  },
  "security": {
    "jwt_secret_key": "generate-this",
    "api_key": "generate-this"
  },
  "cors": {
    "origins": "your-frontend-urls"
  }
}
```

---

## Time Estimates

- **Minimum Setup**: 15 minutes
- **Recommended Setup**: 35 minutes
- **Full Setup**: 1-2 hours (depending on optional providers)

---

## Need Help?

- Check logs: Backend logs show warnings for missing API keys
- Test endpoints: Use `/docs` Swagger UI to test
- Health check: `/api/v1/health` shows provider status
