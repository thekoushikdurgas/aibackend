"""
Base LLM Provider interface
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    """Response from LLM provider"""

    text: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass
class LLMConfig:
    """Configuration for LLM generation"""

    model: Optional[str] = None  # None means use provider's default model
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    stop_sequences: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    safety_settings: Optional[List[Dict[str, Any]]] = None
    response_mime_type: Optional[str] = None
    frequency_penalty: Optional[float] = None  # Range: 0-2, reduces repetition
    presence_penalty: Optional[float] = None  # Range: 0-2, encourages new topics


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    All providers must implement these methods.
    """

    provider_name: str = "base"
    default_model: str  # set by each concrete provider in __init__

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user's input prompt
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous messages in the conversation

        Returns:
            LLMResponse with the generated text
        """
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response from the LLM.

        Implementations are async generators (``async def`` with ``yield``);
        callers use ``async for chunk in provider.stream(...):``.

        Args:
            prompt: The user's input prompt
            config: Generation configuration
            context: Optional context to include
            conversation_history: Previous messages in the conversation

        Yields:
            Text chunks as they are generated
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models for this provider.

        Returns:
            List of model names/identifiers
        """
        pass

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build message list for chat-style APIs.

        Args:
            prompt: The user's current prompt
            context: Optional context to include in system message
            conversation_history: Previous conversation messages
            system_prompt: Optional custom system prompt

        Returns:
            List of message dictionaries
        """
        messages: List[Dict[str, Any]] = []

        # Build system message
        system_parts = []
        if system_prompt:
            system_parts.append(system_prompt)
        else:
            system_parts.append(
                "You are DurgasAI, a helpful AI assistant specialized in "
                "web page analysis, content extraction, and SEO optimization. "
                "Provide clear, accurate, and helpful responses."
            )

        if context:
            system_parts.append(f"\n\nContext:\n{context}")

        messages.append({"role": "system", "content": "\n".join(system_parts)})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append(
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                )

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages
