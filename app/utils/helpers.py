"""
Helper utility functions
"""

import re
import uuid
import hashlib
from typing import Dict, Optional
from datetime import datetime, timezone

_PLACEHOLDER_API_KEY = re.compile(
    r"^(your_.*_key_here|generate_a_random.*|change[-_]in[-_]production.*)$",
    re.IGNORECASE,
)


def utc_now() -> datetime:
    """Naive UTC datetime, equivalent to historical datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4())[:8]
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}"
    return f"{timestamp}_{unique_id}"


def generate_hash(content: str) -> str:
    """Generate a hash of content for deduplication"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing dangerous content
    """
    if not text:
        return ""

    # Remove script tags and their content
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove style tags and their content
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length while preserving word boundaries
    """
    if not text or len(text) <= max_length:
        return text

    truncated = text[: max_length - len(suffix)]

    # Try to break at a word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:  # Only break at space if it's not too far back
        truncated = truncated[:last_space]

    return truncated + suffix


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def format_bytes(size: int) -> str:
    """Format bytes to human readable string"""
    n = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def calculate_reading_time(text: str, words_per_minute: int = 200) -> float:
    """Calculate estimated reading time in minutes"""
    word_count = len(text.split())
    return round(word_count / words_per_minute, 1)


def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    Extract simple keywords from text (basic implementation)
    For production, consider using NLP libraries
    """
    # Remove common stop words
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "been",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "he",
        "she",
        "him",
        "her",
        "his",
        "hers",
        "we",
        "us",
        "our",
        "you",
        "your",
    }

    # Extract words
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    # Count word frequency (excluding stop words)
    word_freq: Dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def is_usable_api_key(key: Optional[str]) -> bool:
    """True when a non-empty API key is set and not a template placeholder."""
    if not key or not str(key).strip():
        return False
    return _PLACEHOLDER_API_KEY.match(str(key).strip()) is None
