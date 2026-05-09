"""
Groq Model Registry and Intelligent Model Selection
Central registry for all Groq models with metadata and selection logic
"""

from typing import Dict, List, Optional, Any

# Complete registry of all Groq models with metadata
GROQ_MODELS: Dict[str, Dict[str, Any]] = {
    # ========== Speed Tier Models ==========
    "llama-3.1-8b-instant": {
        "category": "chat",
        "context_window": 131072,
        "capabilities": ["chat", "fast_inference"],
        "speed_tier": "fast",
        "use_cases": ["quick_responses", "simple_queries", "low_latency"],
        "deprecated": False,
    },
    "llama-3.2-1b-preview": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "fast_inference"],
        "speed_tier": "fast",
        "use_cases": ["quick_responses", "simple_queries"],
        "deprecated": False,
    },
    "llama-3.2-3b-preview": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "fast_inference"],
        "speed_tier": "fast",
        "use_cases": ["quick_responses", "simple_queries"],
        "deprecated": False,
    },
    # ========== Standard Chat Models ==========
    "llama3-8b-8192": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "text_generation"],
        "deprecated": False,
    },
    "llama3-70b-8192": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose", "high_quality"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "complex_queries"],
        "deprecated": False,
    },
    "llama-3.1-70b-versatile": {
        "category": "chat",
        "context_window": 131072,
        "capabilities": ["chat", "general_purpose", "long_context"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "long_context", "document_analysis"],
        "deprecated": False,
    },
    "llama-3.3-70b-versatile": {
        "category": "chat",
        "context_window": 131072,
        "capabilities": ["chat", "general_purpose", "long_context", "high_quality"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "long_context", "complex_analysis"],
        "deprecated": False,
    },
    # ========== Vision Models ==========
    "llama-3.2-11b-vision-preview": {
        "category": "vision",
        "context_window": 8192,
        "capabilities": ["vision", "multimodal", "chat", "image_analysis"],
        "speed_tier": "medium",
        "use_cases": ["image_analysis", "visual_qa", "multimodal_chat"],
        "deprecated": False,
    },
    "llama-3.2-90b-vision-preview": {
        "category": "vision",
        "context_window": 8192,
        "capabilities": [
            "vision",
            "multimodal",
            "chat",
            "image_analysis",
            "high_quality",
        ],
        "speed_tier": "slow",
        "use_cases": ["complex_image_analysis", "detailed_visual_qa"],
        "deprecated": False,
    },
    # ========== Reasoning Models ==========
    "deepseek-r1-distill-llama-70b": {
        "category": "reasoning",
        "context_window": 8192,
        "capabilities": [
            "reasoning",
            "math",
            "code",
            "chain_of_thought",
            "problem_solving",
        ],
        "speed_tier": "medium",
        "use_cases": ["complex_reasoning", "mathematical_problems", "logical_analysis"],
        "deprecated": False,
    },
    "qwen-qwq-32b": {
        "category": "reasoning",
        "context_window": 8192,
        "capabilities": ["reasoning", "math", "problem_solving"],
        "speed_tier": "medium",
        "use_cases": ["mathematical_reasoning", "quantitative_analysis"],
        "deprecated": False,
    },
    # ========== Specialized Models ==========
    "qwen-2.5-coder-32b": {
        "category": "coding",
        "context_window": 8192,
        "capabilities": ["code", "programming", "code_generation", "code_analysis"],
        "speed_tier": "medium",
        "use_cases": ["code_generation", "code_explanation", "debugging"],
        "deprecated": False,
    },
    "moonshotai/kimi-k2-instruct": {
        "category": "chat",
        "context_window": 131072,
        "capabilities": ["chat", "long_context", "document_analysis"],
        "speed_tier": "medium",
        "use_cases": ["long_context_chat", "document_qa", "extended_conversations"],
        "deprecated": False,
    },
    # ========== OpenAI OSS Models ==========
    "openai/gpt-oss-20b": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "text_generation"],
        "deprecated": False,
    },
    "openai/gpt-oss-120b": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose", "high_quality"],
        "speed_tier": "slow",
        "use_cases": ["high_quality_chat", "complex_queries"],
        "deprecated": False,
    },
    # ========== Qwen Models ==========
    "qwen/qwen3-32b": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "multilingual"],
        "deprecated": False,
    },
    "qwen-2.5-32b": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "general_purpose"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "multilingual"],
        "deprecated": False,
    },
    # ========== LLaMA 4 Models ==========
    "meta-llama/llama-4-scout-17b-16e-instruct": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "instruction_following"],
        "speed_tier": "medium",
        "use_cases": ["instruction_following", "task_completion"],
        "deprecated": False,
    },
    "meta-llama/llama-4-maverick-17b-128e-instruct": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "instruction_following", "extended_context"],
        "speed_tier": "medium",
        "use_cases": ["instruction_following", "complex_tasks"],
        "deprecated": False,
    },
    # ========== Safety/Guard Models ==========
    "meta-llama/llama-guard-4-12b": {
        "category": "safety",
        "context_window": 8192,
        "capabilities": ["safety", "content_moderation", "classification"],
        "speed_tier": "fast",
        "use_cases": ["content_safety", "moderation", "safety_checking"],
        "deprecated": False,
    },
    "meta-llama/llama-prompt-guard-2-22m": {
        "category": "safety",
        "context_window": 8192,
        "capabilities": ["safety", "prompt_injection_detection"],
        "speed_tier": "fast",
        "use_cases": ["prompt_injection_detection", "security"],
        "deprecated": False,
    },
    "meta-llama/llama-prompt-guard-2-86m": {
        "category": "safety",
        "context_window": 8192,
        "capabilities": ["safety", "prompt_injection_detection", "higher_accuracy"],
        "speed_tier": "fast",
        "use_cases": ["prompt_injection_detection", "security"],
        "deprecated": False,
    },
    # ========== Other Models ==========
    "mixtral-8x7b-32768": {
        "category": "chat",
        "context_window": 32768,
        "capabilities": ["chat", "general_purpose", "long_context"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "long_context"],
        "deprecated": False,
    },
    "gemma2-9b-it": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "instruction_following"],
        "speed_tier": "medium",
        "use_cases": ["general_chat", "instruction_following"],
        "deprecated": False,
    },
    # ========== Deprecated Models ==========
    "llama2-70b-4096": {
        "category": "chat",
        "context_window": 4096,
        "capabilities": ["chat", "general_purpose"],
        "speed_tier": "medium",
        "use_cases": ["general_chat"],
        "deprecated": True,
    },
    "gemma-7b-it": {
        "category": "chat",
        "context_window": 8192,
        "capabilities": ["chat", "instruction_following"],
        "speed_tier": "medium",
        "use_cases": ["general_chat"],
        "deprecated": True,
    },
    "llama-guard-3-8b": {
        "category": "safety",
        "context_window": 8192,
        "capabilities": ["safety", "content_moderation"],
        "speed_tier": "fast",
        "use_cases": ["content_safety"],
        "deprecated": True,
    },
}


class GroqModelSelector:
    """Intelligent model selection based on task requirements"""

    @staticmethod
    def select_model(
        task_type: str,
        complexity: str = "medium",
        requirements: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Select optimal model for task.

        Args:
            task_type: Type of task - "speed", "reasoning", "vision", "coding", "long_context", "safety"
            complexity: Task complexity - "low", "medium", "high"
            requirements: Additional requirements dict (e.g., {"needs_vision": True})

        Returns:
            Recommended model name
        """
        requirements = requirements or {}

        # Vision tasks
        if task_type == "vision" or requirements.get("needs_vision"):
            if complexity == "high":
                return "llama-3.2-90b-vision-preview"
            return "llama-3.2-11b-vision-preview"

        # Safety/moderation tasks
        if task_type == "safety":
            if requirements.get("check_type") == "prompt_injection":
                return "meta-llama/llama-prompt-guard-2-86m"
            return "meta-llama/llama-guard-4-12b"

        # Reasoning tasks
        if task_type == "reasoning":
            if complexity == "high":
                return "deepseek-r1-distill-llama-70b"
            return "qwen-qwq-32b"

        # Coding tasks
        if task_type == "coding":
            return "qwen-2.5-coder-32b"

        # Long context tasks
        if task_type == "long_context" or requirements.get("long_context"):
            if complexity == "high":
                return "llama-3.3-70b-versatile"
            return "llama-3.1-8b-instant"  # Fast with long context

        # Speed-optimized tasks
        if task_type == "speed":
            return "llama-3.1-8b-instant"

        # Default: balanced model
        if complexity == "high":
            return "llama-3.3-70b-versatile"
        elif complexity == "low":
            return "llama-3.1-8b-instant"
        else:
            return "llama-3.1-70b-versatile"

    @staticmethod
    def get_model_info(model: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific model"""
        return GROQ_MODELS.get(model)

    @staticmethod
    def list_models_by_category(category: Optional[str] = None) -> List[str]:
        """List models, optionally filtered by category"""
        if category:
            return [
                model_id
                for model_id, info in GROQ_MODELS.items()
                if info.get("category") == category
                and not info.get("deprecated", False)
            ]
        return [
            model_id
            for model_id, info in GROQ_MODELS.items()
            if not info.get("deprecated", False)
        ]

    @staticmethod
    def get_alternatives(model: str, task_type: Optional[str] = None) -> List[str]:
        """Get alternative models for a given model or task type"""
        if task_type:
            # Get models suitable for this task type
            if task_type == "vision":
                return ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
            elif task_type == "reasoning":
                return ["deepseek-r1-distill-llama-70b", "qwen-qwq-32b"]
            elif task_type == "coding":
                return ["qwen-2.5-coder-32b"]
            elif task_type == "speed":
                return [
                    "llama-3.1-8b-instant",
                    "llama-3.2-1b-preview",
                    "llama-3.2-3b-preview",
                ]

        # Get models in same category
        model_info = GROQ_MODELS.get(model)
        if model_info:
            category = model_info.get("category")
            alternatives = [
                m
                for m in GROQ_MODELS.keys()
                if GROQ_MODELS[m].get("category") == category
                and m != model
                and not GROQ_MODELS[m].get("deprecated", False)
            ]
            return alternatives[:3]  # Return top 3 alternatives

        return []
