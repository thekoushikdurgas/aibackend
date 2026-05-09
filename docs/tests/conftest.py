"""
Pytest configuration and fixtures
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio for async tests"""
    return "asyncio"


@pytest.fixture
def sample_html():
    """Sample HTML for testing"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Page Title</title>
        <meta name="description" content="This is a test page description">
        <meta property="og:title" content="OG Title">
    </head>
    <body>
        <header>
            <nav>
                <a href="/">Home</a>
                <a href="/about">About</a>
            </nav>
        </header>
        <main>
            <h1>Main Page Heading</h1>
            <article>
                <h2>Article Title</h2>
                <p>This is the article content with some <strong>important</strong> text.</p>
                <img src="image1.jpg" alt="First image">
                <img src="image2.jpg">
            </article>
        </main>
        <footer>
            <p>&copy; 2024 Test Company</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_page_data_dict(sample_html):
    """Sample page data dictionary"""
    return {
        "url": "https://example.com/test-page",
        "title": "Test Page Title",
        "domain": "example.com",
        "protocol": "https:",
        "pathname": "/test-page",
        "html": sample_html,
        "meta": [
            {"name": "description", "content": "This is a test page description"}
        ],
        "structure": {
            "totalElements": 15,
            "links": 2,
            "images": 2,
            "forms": 0
        },
        "semantic": {
            "header": True,
            "nav": True,
            "main": True,
            "footer": True
        },
        "images": [
            {"src": "image1.jpg", "alt": "First image", "has_alt": True},
            {"src": "image2.jpg", "alt": "", "has_alt": False}
        ]
    }
