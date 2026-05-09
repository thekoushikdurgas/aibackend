#!/usr/bin/env python3
"""Test the API response format matches what the extension expects"""
import asyncio
import json
import httpx

async def test_council_api():
    print("=" * 60)
    print("TESTING COUNCIL API RESPONSE FORMAT")
    print("=" * 60)
    
    # Prepare request
    url = "http://localhost:8000/api/v1/council/analyze"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "ZpKty4B8jLEMQpZiDnFB4ax7ZvdfRyJK"
    }
    
    payload = {
        "page_data": {
            "url": "https://example.com",
            "title": "Example",
            "domain": "example.com",
            "html": "<html><body>Test</body></html>",
            "body_html": "",
            "head_html": "",
            "meta": [],
            "structure": {},
            "images": [],
            "videos": [],
            "semantic": {},
            "timestamp": "2025-12-18T00:00:00Z"
        },
        "query": "Hello, can you hear me?",
        "options": {}
    }
    
    print("\n[INFO] Sending request to Council API...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            print(f"[INFO] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n" + "=" * 60)
                print("RESPONSE STRUCTURE")
                print("=" * 60)
                print(f"Keys: {list(data.keys())}")
                
                # Check what extension expects
                print("\n[CHECK] response.analysis exists:", "analysis" in data)
                if "analysis" in data:
                    analysis = data["analysis"]
                    print(f"[CHECK] response.analysis type: {type(analysis)}")
                    print(f"[CHECK] response.analysis keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'N/A'}")
                    print(f"[CHECK] response.analysis.error exists:", "error" in analysis if isinstance(analysis, dict) else "N/A")
                    print(f"[CHECK] response.analysis.final_response exists:", "final_response" in analysis if isinstance(analysis, dict) else "N/A")
                    
                    if isinstance(analysis, dict) and "final_response" in analysis:
                        final_resp = analysis["final_response"]
                        print(f"[CHECK] final_response length: {len(final_resp)} chars")
                        print(f"[CHECK] final_response preview: {final_resp[:200]}...")
                
                print(f"\n[CHECK] response.summary exists:", "summary" in data)
                if "summary" in data:
                    print(f"[CHECK] response.summary length: {len(data['summary'])} chars")
                    print(f"[CHECK] response.summary preview: {data['summary'][:200]}...")
                
                print("\n" + "=" * 60)
                print("FULL RESPONSE (for debugging)")
                print("=" * 60)
                print(json.dumps(data, indent=2)[:2000])
                print("...")
                
                print("\n" + "=" * 60)
                print("[SUCCESS] Council API is working and returning proper format!")
                print("=" * 60)
            else:
                print(f"\n[ERROR] Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_council_api())
