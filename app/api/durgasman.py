"""
Durgasman API Studio Proxy and AI Helper Routes
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, WebSocket
import asyncio
import websockets

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/durgasman", tags=["Durgasman"])


class ProxyRequest(BaseModel):
    method: str
    url: str
    headers: Dict[str, str] = {}
    body: Optional[str] = None


@router.post("/proxy")
async def durgasman_proxy(req: ProxyRequest) -> Dict[str, Any]:
    """
    Proxy HTTP request to external server.
    Bypasses CORS restrictions on the frontend client.
    """
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {k: v for k, v in req.headers.items()}
            # Remove content-length as httpx will recalculate it
            if "content-length" in [k.lower() for k in headers]:
                headers = {
                    k: v for k, v in headers.items() if k.lower() != "content-length"
                }

            content = req.body.encode("utf-8") if req.body else None

            response = await client.request(
                method=req.method, url=req.url, headers=headers, content=content
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Format response size
            raw_content = response.content
            size_kb = len(raw_content) / 1024
            if size_kb >= 0.1:
                size_str = f"{size_kb:.2f} KB"
            else:
                size_str = f"{len(raw_content)} B"

            # Parse headers into dictionary
            res_headers = dict(response.headers)

            # Try to decode content
            try:
                data = response.json()
            except Exception:
                try:
                    data = response.text
                except Exception:
                    data = raw_content.decode("utf-8", errors="ignore")

            return {
                "status": response.status_code,
                "statusText": response.reason_phrase,
                "time": elapsed_ms,
                "size": size_str,
                "headers": res_headers,
                "data": data,
                "error": None,
            }

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Proxy request error to {req.url}: {e}")
        return {
            "status": 0,
            "statusText": "Error",
            "time": elapsed_ms,
            "size": "0 B",
            "headers": {},
            "data": None,
            "error": str(e),
        }


@router.post("/chat")
async def durgasman_chat(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Chat with Gemini using the server's key or custom header key.
    Supports thinking config and search grounding.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    prompt = req_body.get("prompt", "")
    history = req_body.get("history", [])
    options = req_body.get("options", {})

    thinking = options.get("thinking", False)
    search = options.get("search", False)

    # thinking configuration is supported on gemini-2.5-pro
    model = "gemini-2.5-pro" if thinking else "gemini-2.5-flash"

    contents = []
    for msg in history:
        role = msg.get("role", "user")
        text = msg.get("text", "")
        contents.append({"role": role, "parts": [{"text": text}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload: Dict[str, Any] = {"contents": contents, "generationConfig": {}}

    if thinking:
        payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 32768}

    if search:
        payload["tools"] = [{"googleSearch": {}}]

    payload["systemInstruction"] = {
        "parts": [
            {
                "text": (
                    "You are Durgasman AI Assistant, an expert in APIs, "
                    "networking, and software development. Provide concise "
                    "and accurate technical help."
                )
            }
        ]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            candidates = res_data.get("candidates", [])
            text = "No response generated."
            grounding_urls = []

            if candidates:
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")

                grounding_metadata = candidate.get("groundingMetadata", {})
                grounding_chunks = grounding_metadata.get("groundingChunks", [])
                for chunk in grounding_chunks:
                    uri = chunk.get("web", {}).get("uri")
                    if uri:
                        grounding_urls.append(uri)

            return {"text": text, "groundingUrls": grounding_urls}

        except Exception as e:
            logger.error(f"Gemini chat API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def durgasman_analyze(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Analyze an API response and request parameters.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    api_request = req_body.get("request", {})
    api_response = req_body.get("response", {})

    prompt = (
        f"Analyze this API response.\n"
        f"Request: {api_request.get('method')} {api_request.get('url')}\n"
        f"Response Status: {api_response.get('status')} {api_response.get('statusText')}\n"
        f"Response Body: {json.dumps(api_response.get('data') or api_response.get('error'))}\n\n"
        f"Explain what this response means, identify potential issues, and suggest next steps or fixes if needed."
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are a senior backend engineer and API expert. "
                        "Provide a concise, professional analysis of API responses. "
                        "Use markdown formatting."
                    )
                }
            ]
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            candidates = res_data.get("candidates", [])
            text = "Failed to analyze response."
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "Failed to analyze response.")

            return {"text": text}

        except Exception as e:
            logger.error(f"Gemini response analysis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-docs")
async def durgasman_generate_docs(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate Markdown API documentation for a request collection.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    collection = req_body.get("collection", {})
    requests_summary = []
    for r in collection.get("requests", []):
        requests_summary.append(
            {
                "name": r.get("name"),
                "method": r.get("method"),
                "url": r.get("url"),
            }
        )

    prompt = (
        f'Generate professional technical documentation for the following API collection named "{collection.get("name")}".\n'
        f"Requests included: {json.dumps(requests_summary)}.\n"
        f"Provide a markdown summary, detailed endpoint breakdowns, and authentication requirements."
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are an expert Technical Writer. Generate clean, "
                        "well-formatted Markdown documentation."
                    )
                }
            ]
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            candidates = res_data.get("candidates", [])
            text = "Failed to generate documentation."
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "Failed to generate documentation.")

            return {"text": text}

        except Exception as e:
            logger.error(f"Gemini docs generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-request")
async def durgasman_generate_request(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate an API request JSON from a prompt prompt.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    prompt = req_body.get("prompt", "")
    schema_hint = req_body.get("schemaHint")

    contents = (
        f'Generate a valid JSON object for a web API request based on this description: "{prompt}".\n'
        f'{f"Additionally, the user expects the response to follow these requirements: {schema_hint}." if schema_hint else ""}\n'
        f"Response MUST be a single JSON object matching the requested schema."
    )

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "method": {"type": "STRING"},
            "url": {"type": "STRING"},
            "params": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "key": {"type": "STRING"},
                        "value": {"type": "STRING"},
                        "enabled": {"type": "BOOLEAN"},
                    },
                },
            },
            "headers": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "key": {"type": "STRING"},
                        "value": {"type": "STRING"},
                        "enabled": {"type": "BOOLEAN"},
                    },
                },
            },
            "body": {"type": "STRING"},
            "responseSchema": {"type": "STRING"},
        },
        "required": ["name", "method", "url"],
    }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": contents}]}],
        "systemInstruction": {
            "parts": [
                {
                    "text": "You are a senior backend developer. Generate a valid API request in JSON format."
                }
            ]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            candidates = res_data.get("candidates", [])
            text = None
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text")

            if text:
                parsed_json = json.loads(text)
                return {"request": parsed_json}
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse request from Gemini response",
                )

        except Exception as e:
            logger.error(f"Gemini generate request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
async def durgasman_speak(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate audio speech (TTS) from text using Gemini.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    text = req_body.get("text", "")
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
            },
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            candidates = res_data.get("candidates", [])
            base64_audio = None
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    for part in parts:
                        inline_data = part.get("inlineData", {})
                        if inline_data and inline_data.get("data"):
                            base64_audio = inline_data.get("data")
                            break

            return {"audio": base64_audio}

        except Exception as e:
            logger.error(f"Gemini speak (TTS) error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-image")
async def durgasman_generate_image(
    req_body: Dict[str, Any], x_gemini_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Generate an image using Imagen on Google AI.
    """
    api_key = x_gemini_api_key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on the backend.",
        )

    prompt = req_body.get("prompt", "")
    aspect_ratio = req_body.get("aspectRatio", "1:1")

    payload = {
        "prompt": prompt,
        "numberOfImages": 1,
        "outputMimeType": "image/jpeg",
        "aspectRatio": aspect_ratio,
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:generateImages?key={api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()

            generated_images = res_data.get("generatedImages", [])
            base64_image = None
            if generated_images:
                image_bytes = generated_images[0].get("image", {}).get("imageBytes")
                if image_bytes:
                    base64_image = f"data:image/jpeg;base64,{image_bytes}"

            return {"image": base64_image}

        except Exception as e:
            logger.error(f"Gemini generate-image error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/live-ws")
async def live_ws_proxy(websocket: WebSocket, key: Optional[str] = None):
    """
    Proxy the Multimodal Live API WebSocket connection to Google's live server.
    """
    api_key = key or settings.gemini_api_key
    if not api_key or any(
        p in api_key.lower() for p in ["placeholder", "your-api-key"]
    ):
        await websocket.close(code=4000, reason="Gemini API Key is not configured.")
        return

    await websocket.accept()
    google_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"

    try:
        async with websockets.connect(google_url) as google_ws:

            async def client_to_google():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await google_ws.send(data)
                except Exception:
                    pass

            async def google_to_client():
                try:
                    while True:
                        data = await google_ws.recv()
                        await websocket.send_text(data)
                except Exception:
                    pass

            # Run both forwarding tasks concurrently until one closes
            await asyncio.gather(client_to_google(), google_to_client())

    except Exception as e:
        logger.error(f"Durgasman WebSocket Live proxy error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
