# Quick Start Guide - Backend Setup

## 🚀 Get Running in 5 Minutes

### Step 1: Generate Security Keys (2 min)

```python
import secrets
print("JWT Key:", secrets.token_urlsafe(32))
print("API Key:", secrets.token_urlsafe(24))
```

Update `config/config.json` → `security` section with these keys.

### Step 2: Install Ollama (3 min)

1. Download: https://ollama.ai/download
2. Install and start: `ollama serve`
3. Pull model: `ollama pull llama3`

### Step 3: Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

✅ **Done!** Backend is running with Ollama (local, free, no API keys needed)

---

## 📋 What You Need (Priority Order)

### 🔴 **REQUIRED** (Backend won't work without):

1. ✅ Python 3.10+ (you have this)
2. ✅ Dependencies installed (already done)
3. ⚠️ **Security keys** (generate now - see Step 1 above)
4. ✅ Ollama (install - see Step 2 above)

### 🟡 **RECOMMENDED** (For full features):

- **Gemini API Key**: https://makersuite.google.com/app/apikey (free tier)
- **Groq API Key**: https://console.groq.com/keys (free tier, very fast)
- **HuggingFace Token**: https://huggingface.co/settings/tokens (free tier)

### 🟢 **OPTIONAL** (As needed):

- AI21, Alibaba, Cerebras, NVIDIA, AWS Bedrock, Vertex AI

---

## 📝 Current Status

### ✅ Already Working:

- Server configuration
- Database (SQLite)
- ChromaDB (vector storage)
- Ollama provider (default)
- Local embeddings

### ⚠️ Needs Your Action:

- **Security keys** (must change from defaults)
- **API keys** (optional, for cloud providers)

---

## 🎯 Quick Tasks

1. **Generate security keys** → Update `config/config.json`
2. **Install Ollama** → `ollama pull llama3`
3. **Start backend** → `uvicorn app.main:app --reload`
4. **Test** → Visit http://localhost:8000/docs

**Time**: ~5 minutes for basic setup

---

## 📚 Detailed Guides

- **Full Requirements**: See `SETUP_REQUIREMENTS.md`
- **Step-by-Step Tasks**: See `SETUP_TASKS.md`
- **Configuration Reference**: See `config/config.example.json`

---

## 🔑 API Key Quick Links

| Provider    | URL                                      | Free Tier |
| ----------- | ---------------------------------------- | --------- |
| Gemini      | https://makersuite.google.com/app/apikey | ✅ Yes    |
| Groq        | https://console.groq.com/keys            | ✅ Yes    |
| HuggingFace | https://huggingface.co/settings/tokens   | ✅ Yes    |
| AI21        | https://studio.ai21.com/account/api-keys | ❌ No     |
| Alibaba     | https://dashscope.console.aliyun.com/    | ❌ No     |

---

## ⚡ Minimum vs Full Setup

### Minimum (5 min):

- Security keys ✅
- Ollama ✅
- **Result**: Backend works, chat with local models

### Full (30 min):

- Minimum setup ✅
- Gemini API key ✅
- Groq API key ✅
- HuggingFace token ✅
- **Result**: All features, multiple providers, multimodal

---

## 🆘 Troubleshooting

**Backend won't start?**

- Check Python version: `python --version` (need 3.10+)
- Check dependencies: `pip install -r requirements.txt`
- Check config: `config/config.json` exists and is valid JSON

**Ollama not working?**

- Check Ollama running: `curl http://localhost:11434/api/tags`
- Check model: `ollama list` (should see llama3)

**API keys not working?**

- Check logs for warnings
- Verify key format (no extra spaces)
- Test in Swagger UI: http://localhost:8000/docs

---

## 📞 Next Steps

1. ✅ Complete minimum setup (5 min)
2. 🟡 Add recommended API keys (20 min)
3. 🟢 Test all features (10 min)
4. 🚀 Deploy to production (when ready)

**Total time to full setup: ~35 minutes**
