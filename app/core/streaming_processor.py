"""
Streaming Response Processor with Buffering, Retry, and Token Counting
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any, Callable
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class StreamingProcessor:
    """
    Process and optimize streaming responses from AI models.
    Handles buffering, timeout protection, and retry logic.
    """

    def __init__(
        self,
        chunk_size: int = 50,
        buffer_time: float = 0.1,
        max_buffer_size: int = 1000,
    ):
        """
        Initialize streaming processor.

        Args:
            chunk_size: Minimum characters before flushing buffer
            buffer_time: Maximum time (seconds) to hold buffer before flushing
            max_buffer_size: Maximum buffer size before forced flush
        """
        self.chunk_size = chunk_size
        self.buffer_time = buffer_time
        self.max_buffer_size = max_buffer_size

    async def process_stream(
        self, stream: AsyncGenerator[str, None], filter_empty: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Process streaming response with buffering and optimization.

        Args:
            stream: Input stream from AI model
            filter_empty: Filter out empty chunks

        Yields:
            Processed chunks
        """
        buffer = ""
        last_flush = datetime.utcnow()

        try:
            async for chunk in stream:
                if filter_empty and not chunk.strip():
                    continue

                buffer += chunk
                now = datetime.utcnow()
                elapsed = (now - last_flush).total_seconds()

                # Flush if buffer is large enough, or timeout reached, or newline found
                should_flush = (
                    len(buffer) >= self.chunk_size
                    or elapsed >= self.buffer_time
                    or len(buffer) >= self.max_buffer_size
                    or "\n" in chunk
                )

                if should_flush and buffer:
                    yield buffer
                    buffer = ""
                    last_flush = now

            # Yield remaining buffer
            if buffer:
                yield buffer

        except Exception as e:
            logger.error(f"Error processing stream: {e}")
            # Yield any remaining buffer before raising
            if buffer:
                yield buffer
            raise

    async def stream_with_timeout(
        self, stream: AsyncGenerator[str, None], timeout: int = 60
    ) -> AsyncGenerator[str, None]:
        """
        Stream with timeout protection.

        Args:
            stream: Input stream
            timeout: Timeout in seconds

        Yields:
            Chunks from stream
        """
        try:
            async with asyncio.timeout(timeout):
                async for chunk in stream:
                    yield chunk
        except asyncio.TimeoutError:
            logger.error(f"Stream timeout after {timeout} seconds")
            yield "\n[Stream timeout - request took too long]"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

    async def stream_with_retry(
        self,
        stream_func: Callable[[], AsyncGenerator[str, None]],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Stream with automatic retry on failure.

        Args:
            stream_func: Function that returns async generator
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            exponential_backoff: Use exponential backoff for retries

        Yields:
            Chunks from stream
        """
        delay = retry_delay

        for attempt in range(max_retries):
            try:
                stream = stream_func()
                async for chunk in stream:
                    yield chunk
                return  # Success, exit
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Stream attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                    if exponential_backoff:
                        delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Stream failed after {max_retries} attempts: {e}")
                    raise


class TokenCounter:
    """
    Count tokens and track statistics in streaming responses.
    """

    def __init__(self):
        self.token_count = 0
        self.char_count = 0
        self.word_count = 0
        self.chunk_count = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def count_tokens_in_stream(
        self, stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """
        Count tokens while streaming.

        Args:
            stream: Input stream

        Yields:
            Chunks from stream
        """
        self.start_time = datetime.utcnow()

        try:
            async for chunk in stream:
                # Simple token counting (words)
                words = chunk.split()
                self.token_count += len(words)
                self.char_count += len(chunk)
                self.word_count += len([w for w in words if w.strip()])
                self.chunk_count += 1
                yield chunk
        finally:
            self.end_time = datetime.utcnow()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get token counting statistics.

        Returns:
            Dictionary with statistics
        """
        elapsed = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time and self.start_time
            else 0
        )

        return {
            "token_count": self.token_count,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "chunk_count": self.chunk_count,
            "elapsed_seconds": elapsed,
            "tokens_per_second": self.token_count / elapsed if elapsed > 0 else 0,
            "chars_per_second": self.char_count / elapsed if elapsed > 0 else 0,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.token_count = 0
        self.char_count = 0
        self.word_count = 0
        self.chunk_count = 0
        self.start_time = None
        self.end_time = None


class ResponseFormatter:
    """
    Format streaming responses for UI consumption.
    """

    @staticmethod
    async def format_markdown_stream(
        stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Format stream as markdown with metadata.

        Args:
            stream: Input text stream

        Yields:
            Formatted dicts with markdown content
        """
        async for chunk in stream:
            yield {
                "type": "chunk",
                "content": chunk,
                "timestamp": datetime.utcnow().isoformat(),
                "format": "markdown",
            }

    @staticmethod
    async def format_json_stream(
        stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Format stream as structured JSON objects.

        Args:
            stream: Input text stream

        Yields:
            Parsed JSON objects or text chunks
        """
        buffer = ""

        async for chunk in stream:
            buffer += chunk

            # Try to find complete JSON objects
            while "{" in buffer and "}" in buffer:
                start = buffer.find("{")
                # Find matching closing brace
                brace_count = 0
                end = -1
                for i in range(start, len(buffer)):
                    if buffer[i] == "{":
                        brace_count += 1
                    elif buffer[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break

                if end > start:
                    try:
                        json_str = buffer[start:end]
                        json_obj = json.loads(json_str)
                        yield json_obj
                        buffer = buffer[end:]
                    except json.JSONDecodeError:
                        # Not valid JSON, break and wait for more
                        break
                else:
                    break

        # Yield remaining as text
        if buffer.strip():
            yield {"type": "text", "content": buffer}

    @staticmethod
    async def format_jsonrpc_stream(
        stream: AsyncGenerator[str, None], request_id: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Format stream as JSON-RPC 2.0 compatible responses.

        Args:
            stream: Input text stream
            request_id: JSON-RPC request ID (None for notifications)

        Yields:
            JSON-RPC 2.0 formatted responses
        """
        full_content = ""
        chunk_index = 0

        async for chunk in stream:
            full_content += chunk
            chunk_index += 1

            yield {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "type": "chunk",
                    "content": chunk,
                    "index": chunk_index,
                    "full_content": full_content,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

        # Final completion message
        yield {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "type": "complete",
                "full_content": full_content,
                "total_chunks": chunk_index,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }


class ContentFilter:
    """
    Filter and sanitize streaming content.
    """

    def __init__(self, blocked_patterns: Optional[list] = None):
        """
        Initialize content filter.

        Args:
            blocked_patterns: List of patterns to redact (default: common sensitive patterns)
        """
        self.blocked_patterns = blocked_patterns or [
            "password",
            "api_key",
            "secret",
            "token",
            "credential",
        ]

    async def filter_sensitive_content(
        self, stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """
        Remove sensitive information from stream.

        Args:
            stream: Input stream

        Yields:
            Filtered chunks
        """
        async for chunk in stream:
            filtered = chunk
            for pattern in self.blocked_patterns:
                if pattern.lower() in chunk.lower():
                    filtered = filtered.replace(pattern, "[REDACTED]")
            yield filtered

    @staticmethod
    async def escape_html(
        stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """
        Escape HTML special characters.

        Args:
            stream: Input stream

        Yields:
            HTML-escaped chunks
        """
        import html

        async for chunk in stream:
            yield html.escape(chunk)
