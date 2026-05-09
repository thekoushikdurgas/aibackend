#!/usr/bin/env python3
"""Test the council endpoint directly"""
import asyncio
from app.agents import AgentRouter
from app.models.schemas import PageData, AgentType

async def main():
    print("=" * 60)
    print("TESTING COUNCIL ENDPOINT")
    print("=" * 60)
    
    # Create sample page data
    page_data = PageData(
        url="https://example.com",
        title="Example Website",
        domain="example.com",
        html="<html><body><h1>Example</h1><p>This is a test page.</p></body></html>",
        body_html="<body><h1>Example</h1><p>This is a test page.</p></body>",
        head_html="<head><title>Example</title></head>",
        meta=[],
        structure={},
        images=[],
        videos=[],
        semantic={},
        timestamp="2025-12-18T00:00:00Z"
    )
    
    query = "What is this page about?"
    
    try:
        print(f"\n[INFO] Testing council analysis with query: '{query}'")
        print("-" * 60)
        
        response = await AgentRouter.route(
            agent_type=AgentType.COUNCIL,
            page_data=page_data,
            query=query,
            options={}
        )
        
        print(f"\n[SUCCESS] Council response received!")
        print(f"Agent Type: {response.agent_type}")
        print(f"\nAnalysis: {response.analysis}")
        print(f"\nSummary: {response.summary}")
        if response.metadata:
            print(f"\nMetadata: {response.metadata}")
        
    except Exception as e:
        print(f"\n[ERROR] Council test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
