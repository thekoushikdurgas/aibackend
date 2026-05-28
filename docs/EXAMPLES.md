# WebSocket API Examples

## Table of Contents

1. [Basic Connection](#basic-connection)
2. [Chat Completions](#chat-completions)
3. [Streaming Responses](#streaming-responses)
4. [File Uploads](#file-uploads)
5. [Agent Analysis](#agent-analysis)
6. [Vision Analysis](#vision-analysis)
7. [RAG Operations](#rag-operations)
8. [Error Handling](#error-handling)

## Basic Connection

### JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/gateway');

ws.onopen = () => {
  console.log('Connected');

  // Send health check
  ws.send(
    JSON.stringify({
      jsonrpc: '2.0',
      id: '1',
      method: 'system.health',
      params: {},
    })
  );
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Response:', response);
};
```

### Python

```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://localhost:8000/ws/gateway') as ws:
        # Receive connection confirmation
        response = await ws.recv()
        print(json.loads(response))

        # Send request
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "system.health",
            "params": {}
        }
        await ws.send(json.dumps(request))

        # Receive response
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(connect())
```

## Chat Completions

### Simple Chat

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'chat-1',
  method: 'chat.completions',
  params: {
    message: 'What is the capital of France?',
    provider: 'groq',
    model: 'llama-3.1-70b',
    temperature: 0.7,
    max_tokens: 100,
  },
};

ws.send(JSON.stringify(request));
```

### Chat with Conversation History

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'chat-2',
  method: 'chat.completions',
  params: {
    message: 'What did I just ask?',
    provider: 'groq',
    conversation_id: 'conv-123', // Reuse same ID for history
    stream: false,
  },
};

ws.send(JSON.stringify(request));
```

### Chat with RAG

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'chat-3',
  method: 'chat.completions',
  params: {
    message: 'What is machine learning?',
    provider: 'groq',
    use_rag: true, // Enable RAG context retrieval
    stream: false,
  },
};

ws.send(JSON.stringify(request));
```

## Streaming Responses

### Handle Streaming Chat

```javascript
let fullResponse = '';

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);

  if (response.result) {
    switch (response.result.type) {
      case 'start':
        console.log(`Started: ${response.result.provider}/${response.result.model}`);
        break;

      case 'chunk':
        process.stdout.write(response.result.content);
        fullResponse += response.result.content;
        break;

      case 'done':
        console.log('\n\nComplete!');
        console.log('Full response:', fullResponse);
        console.log('Usage:', response.result.usage);
        break;

      case 'error':
        console.error('Streaming error:', response.result.error);
        break;
    }
  }
};

// Send streaming request
ws.send(
  JSON.stringify({
    jsonrpc: '2.0',
    id: 'stream-1',
    method: 'chat.completions',
    params: {
      message: 'Write a short story',
      provider: 'groq',
      stream: true, // Enable streaming
    },
  })
);
```

## File Uploads

### Image Analysis

```javascript
// Read file and convert to base64
const fileInput = document.getElementById('imageInput');
const file = fileInput.files[0];

const reader = new FileReader();
reader.onload = () => {
  const base64 = reader.result.split(',')[1]; // Remove data URL prefix

  const request = {
    jsonrpc: '2.0',
    id: 'vision-1',
    method: 'vision.analyze',
    params: {
      image: {
        data: base64,
        mime_type: file.type,
      },
      prompt: 'What objects are in this image?',
    },
  };

  ws.send(JSON.stringify(request));
};

reader.readAsDataURL(file);
```

### Audio Transcription

```javascript
const audioFile = document.getElementById('audioInput').files[0];
const reader = new FileReader();

reader.onload = () => {
  const base64 = reader.result.split(',')[1];

  const request = {
    jsonrpc: '2.0',
    id: 'transcribe-1',
    method: 'multimodal.speech_to_text',
    params: {
      audio: {
        data: base64,
        mime_type: audioFile.type,
      },
      language: 'en',
    },
  };

  ws.send(JSON.stringify(request));
};

reader.readAsDataURL(audioFile);
```

## Agent Analysis

### SEO Analysis

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'seo-1',
  method: 'agents.analyze',
  params: {
    agent_type: 'seo',
    page_data: {
      url: 'https://example.com',
      title: 'Example Page',
      html: document.documentElement.outerHTML,
      meta: [{ name: 'description', content: '...' }],
    },
    query: 'Analyze SEO',
    options: {
      target_keyword: 'example',
    },
  },
};

ws.send(JSON.stringify(request));
```

### Auto Agent Selection

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'auto-1',
  method: 'agents.auto_analyze',
  params: {
    page_data: {
      url: window.location.href,
      html: document.documentElement.outerHTML,
    },
    query: 'What can be improved on this page?',
  },
};

ws.send(JSON.stringify(request));
```

### Batch Analysis

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'batch-1',
  method: 'agents.batch_analyze',
  params: {
    page_data: {
      url: 'https://example.com',
      html: '<html>...</html>',
    },
    agent_types: ['seo', 'page_analyzer', 'image_analyzer'],
    query: 'Comprehensive analysis',
  },
};

ws.send(JSON.stringify(request));
```

## Vision Analysis

### NVIDIA Vision

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'nvidia-vision-1',
  method: 'vision.nvidia',
  params: {
    prompt: 'Describe this image in detail',
    image: {
      data: base64ImageData,
      mime_type: 'image/png',
    },
    model: 'nvidia/llama-v1-7b',
    max_tokens: 500,
    temperature: 0.7,
  },
};

ws.send(JSON.stringify(request));
```

## RAG Operations

### Query RAG

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'rag-query-1',
  method: 'rag.query',
  params: {
    query: 'What is the main topic?',
    k: 5,
    max_context_length: 4000,
  },
};

ws.send(JSON.stringify(request));
```

### Ingest Document

```javascript
const request = {
  jsonrpc: '2.0',
  id: 'rag-ingest-1',
  method: 'rag.ingest',
  params: {
    text: 'Long document content here...',
    document_id: 'doc-123',
    metadata: {
      title: 'Document Title',
      source: 'https://example.com/doc',
      author: 'John Doe',
    },
  },
};

ws.send(JSON.stringify(request));
```

## Error Handling

### Comprehensive Error Handling

```javascript
ws.onmessage = (event) => {
  try {
    const response = JSON.parse(event.data);

    if (response.error) {
      handleError(response.error);
    } else if (response.result) {
      handleSuccess(response.result);
    }
  } catch (e) {
    console.error('Parse error:', e);
  }
};

function handleError(error) {
  switch (error.code) {
    case -32700:
      console.error('Parse error:', error.message);
      break;

    case -32601:
      console.error('Method not found:', error.message);
      break;

    case -32602:
      console.error('Invalid params:', error.data);
      break;

    case -32001:
      console.error('Authentication failed:', error.message);
      // Re-authenticate
      authenticate();
      break;

    case -32005:
      console.error('Provider error:', error.message);
      // Try different provider
      break;

    default:
      console.error('Error:', error);
  }
}

function handleSuccess(result) {
  if (result.type === 'chunk') {
    process.stdout.write(result.content);
  } else {
    console.log('Result:', result);
  }
}
```

### Retry Logic

```javascript
async function sendWithRetry(request, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      ws.send(JSON.stringify(request));

      // Wait for response with timeout
      const response = await waitForResponse(request.id, 5000);

      if (response.error && response.error.code === -32006) {
        // Service unavailable - retry
        await sleep(1000 * (i + 1)); // Exponential backoff
        continue;
      }

      return response;
    } catch (e) {
      if (i === maxRetries - 1) throw e;
      await sleep(1000 * (i + 1));
    }
  }
}

function waitForResponse(requestId, timeout) {
  return new Promise((resolve, reject) => {
    const handler = (event) => {
      const response = JSON.parse(event.data);
      if (response.id === requestId) {
        ws.removeEventListener('message', handler);
        clearTimeout(timer);
        resolve(response);
      }
    };

    ws.addEventListener('message', handler);

    const timer = setTimeout(() => {
      ws.removeEventListener('message', handler);
      reject(new Error('Timeout'));
    }, timeout);
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```

## Complete Example: Chat Application

```javascript
class WebSocketChat {
  constructor(url, token) {
    this.url = url;
    this.token = token;
    this.ws = null;
    this.requestId = 0;
    this.pendingRequests = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`${this.url}?token=${this.token}`);

      this.ws.onopen = () => {
        console.log('Connected');
        resolve();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('Disconnected');
        // Implement reconnection logic
        setTimeout(() => this.connect(), 1000);
      };
    });
  }

  handleMessage(event) {
    const response = JSON.parse(event.data);

    // Handle connection confirmation
    if (response.result && response.result.type === 'connected') {
      console.log('Connection confirmed:', response.result.connection_id);
      return;
    }

    // Handle ping/pong
    if (event.data === 'pong') {
      return;
    }

    // Handle responses
    if (response.id && this.pendingRequests.has(response.id)) {
      const { resolve, reject } = this.pendingRequests.get(response.id);
      this.pendingRequests.delete(response.id);

      if (response.error) {
        reject(response.error);
      } else {
        resolve(response.result);
      }
    }
  }

  send(method, params) {
    return new Promise((resolve, reject) => {
      const id = `req-${++this.requestId}`;
      const request = {
        jsonrpc: '2.0',
        id: id,
        method: method,
        params: params,
      };

      this.pendingRequests.set(id, { resolve, reject });
      this.ws.send(JSON.stringify(request));
    });
  }

  async chat(message, options = {}) {
    return this.send('chat.completions', {
      message,
      provider: options.provider || 'groq',
      stream: options.stream || false,
      ...options,
    });
  }

  keepAlive() {
    setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000); // Every 30 seconds
  }
}

// Usage
const chat = new WebSocketChat('ws://localhost:8000/ws/gateway', 'your-token');
await chat.connect();
chat.keepAlive();

// Send message
const response = await chat.chat('Hello!', { stream: false });
console.log(response.message);
```
