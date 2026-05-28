"""
Council Service - Multi-model deliberation system
"""

from .orchestrator import CouncilOrchestrator, run_full_council
from .model_selector import ModelSelector, select_council_models, select_chairman_model
from .parser import parse_ranking_from_text, extract_final_ranking_section
from .policy import CouncilPolicy, CouncilRunOptions, parse_council_options
from .prompts import (
    build_stage2_ranking_prompt,
    build_stage3_chairman_prompt,
    build_stage1_prompt,
)

__all__ = [
    "CouncilOrchestrator",
    "CouncilPolicy",
    "CouncilRunOptions",
    "parse_council_options",
    "run_full_council",
    "ModelSelector",
    "select_council_models",
    "select_chairman_model",
    "parse_ranking_from_text",
    "extract_final_ranking_section",
    "build_stage2_ranking_prompt",
    "build_stage3_chairman_prompt",
    "build_stage1_prompt",
]
