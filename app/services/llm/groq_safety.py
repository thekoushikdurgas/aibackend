"""
Groq Safety Service
Uses Groq's safety/guard models for content moderation and prompt injection detection
"""

import logging
from typing import Dict, List, Optional, Any

from app.config import settings
from app.services.llm.groq import GroqProvider

logger = logging.getLogger(__name__)


class GroqSafetyService:
    """Service for content safety and moderation using Groq's guard models"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        guard_model: Optional[str] = None,
        prompt_guard_model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Groq safety service.

        Args:
            api_key: Groq API key
            guard_model: LLaMA Guard model (defaults to meta-llama/llama-guard-4-12b)
            prompt_guard_model: Prompt Guard model (defaults to meta-llama/llama-prompt-guard-2-86m)
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        self.guard_model = guard_model or settings.groq_safety_model
        self.prompt_guard_model = prompt_guard_model or settings.groq_prompt_guard_model
        self.base_url = base_url or settings.groq_base_url
        self.timeout = timeout

        # Initialize Groq provider
        self.groq_provider = GroqProvider(
            api_key=self.api_key,
            model=self.guard_model,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        if not self.api_key:
            logger.warning("Groq API key not configured")

    def _parse_guard_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLaMA Guard response format.

        Format: "safe" or "unsafe\nS1" or "unsafe\nS2" etc.

        Args:
            response_text: Raw response from guard model

        Returns:
            Parsed safety information
        """
        response_text = response_text.strip()

        if response_text.lower() == "safe":
            return {
                "safe": True,
                "categories": [],
                "classification": "safe",
                "risk_level": "none",
            }

        # Parse unsafe response
        lines = response_text.split("\n")
        classification = lines[0].strip()

        if classification.lower().startswith("unsafe"):
            # Extract categories (S1, S2, etc.)
            categories = []
            risk_level = "high"

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("S"):
                    categories.append(line)
                    # S1 is most severe
                    if line == "S1":
                        risk_level = "critical"
                    elif line == "S2" and risk_level != "critical":
                        risk_level = "high"
                    elif line in ["S3", "S4"] and risk_level not in [
                        "critical",
                        "high",
                    ]:
                        risk_level = "medium"

            return {
                "safe": False,
                "categories": categories,
                "classification": classification,
                "risk_level": risk_level,
            }

        # Unknown format
        return {
            "safe": True,  # Default to safe if unclear
            "categories": [],
            "classification": response_text,
            "risk_level": "unknown",
        }

    def _parse_prompt_guard_response(
        self, response_text: str, threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Parse Prompt Guard response format.

        Format: Risk score as float string (e.g., "0.9989147186279297")

        Args:
            response_text: Raw response from prompt guard model
            threshold: Risk threshold (default 0.5)

        Returns:
            Parsed prompt injection information
        """
        try:
            risk_score = float(response_text.strip())
            is_injection = risk_score >= threshold

            return {
                "risk_score": risk_score,
                "is_injection": is_injection,
                "threshold": threshold,
                "risk_level": (
                    "high"
                    if risk_score >= 0.8
                    else "medium" if risk_score >= threshold else "low"
                ),
            }
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse prompt guard response: {response_text}")
            return {
                "risk_score": 0.0,
                "is_injection": False,
                "threshold": threshold,
                "risk_level": "unknown",
            }

    async def check_content_safety(
        self, content: str, check_type: str = "user"
    ) -> Dict[str, Any]:
        """
        Check content safety using LLaMA Guard.

        Args:
            content: Content to check
            check_type: Type of content - "user" or "assistant"

        Returns:
            Dictionary with safety check results
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        # Build prompt for guard model
        # LLaMA Guard expects specific format
        if check_type == "user":
            prompt = f"User: {content}"
        else:
            prompt = f"Assistant: {content}"

        from app.services.llm.base import LLMConfig

        config = LLMConfig(
            model=self.guard_model,
            temperature=0.0,  # Deterministic for safety checks
            max_tokens=10,  # Guard models return short responses
        )

        try:
            response = await self.groq_provider.generate(prompt=prompt, config=config)

            parsed = self._parse_guard_response(response.text)

            return {
                "safe": parsed["safe"],
                "categories": parsed["categories"],
                "classification": parsed["classification"],
                "risk_level": parsed["risk_level"],
                "check_type": check_type,
                "raw_response": response.raw_response,
            }

        except Exception as e:
            logger.error(f"Content safety check error: {e}")
            raise Exception(f"Content safety check failed: {str(e)}")

    async def check_prompt_injection(
        self, prompt: str, model: Optional[str] = None, threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Check for prompt injection attacks using Prompt Guard.

        Args:
            prompt: Prompt to check
            model: Prompt guard model to use
            threshold: Risk score threshold (default 0.5)

        Returns:
            Dictionary with prompt injection check results
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        model = model or self.prompt_guard_model

        from app.services.llm.base import LLMConfig

        config = LLMConfig(
            model=model,
            temperature=0.0,  # Deterministic
            max_tokens=10,  # Returns just a score
        )

        try:
            response = await self.groq_provider.generate(prompt=prompt, config=config)

            parsed = self._parse_prompt_guard_response(response.text, threshold)

            return {
                "risk_score": parsed["risk_score"],
                "is_injection": parsed["is_injection"],
                "threshold": parsed["threshold"],
                "risk_level": parsed["risk_level"],
                "model": model,
                "raw_response": response.raw_response,
            }

        except Exception as e:
            logger.error(f"Prompt injection check error: {e}")
            raise Exception(f"Prompt injection check failed: {str(e)}")

    async def moderate_conversation(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Moderate an entire conversation, checking all messages.

        Args:
            messages: List of message dicts with "role" and "content" keys

        Returns:
            Dictionary with moderation results for each message
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        results = {
            "safe": True,
            "messages_checked": len(messages),
            "violations": [],
            "details": [],
        }

        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if not content:
                continue

            check_type = "user" if role == "user" else "assistant"

            try:
                safety_result = await self.check_content_safety(content, check_type)

                results["details"].append(
                    {
                        "message_index": i,
                        "role": role,
                        "safe": safety_result["safe"],
                        "classification": safety_result["classification"],
                        "categories": safety_result["categories"],
                    }
                )

                if not safety_result["safe"]:
                    results["safe"] = False
                    results["violations"].append(
                        {
                            "message_index": i,
                            "role": role,
                            "classification": safety_result["classification"],
                            "categories": safety_result["categories"],
                            "risk_level": safety_result["risk_level"],
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to check message {i}: {e}")
                results["details"].append(
                    {
                        "message_index": i,
                        "role": role,
                        "safe": None,  # Unknown
                        "error": str(e),
                    }
                )

        return results

    async def list_models(self) -> List[str]:
        """List available safety/guard models"""
        return [
            "meta-llama/llama-guard-4-12b",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
        ]
