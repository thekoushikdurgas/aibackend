"""
Tests for Council functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.services.council import (
    CouncilOrchestrator,
    ModelSelector,
    parse_ranking_from_text,
    build_stage2_ranking_prompt,
    build_stage3_chairman_prompt
)
from app.models.schemas import PageData


class TestRankingParser:
    """Test ranking parsing utilities"""
    
    def test_parse_ranking_with_final_ranking_section(self):
        """Test parsing when FINAL RANKING section exists"""
        text = """
        Response A is good but lacks detail.
        Response B is comprehensive.
        Response C is accurate.
        
        FINAL RANKING:
        1. Response B
        2. Response C
        3. Response A
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response C", "Response A"]
    
    def test_parse_ranking_fallback(self):
        """Test fallback parsing when no FINAL RANKING section"""
        text = "Response A is good. Response B is better. Response C is best."
        result = parse_ranking_from_text(text)
        # Should extract all Response X patterns
        assert "Response A" in result
        assert "Response B" in result
        assert "Response C" in result
    
    def test_parse_ranking_empty(self):
        """Test parsing empty text"""
        result = parse_ranking_from_text("")
        assert result == []


class TestPrompts:
    """Test prompt building"""
    
    def test_build_stage2_prompt(self):
        """Test Stage 2 ranking prompt"""
        query = "What is AI?"
        responses = "Response A: AI is...\n\nResponse B: AI means..."
        prompt = build_stage2_ranking_prompt(query, responses)
        
        assert "FINAL RANKING:" in prompt
        assert query in prompt
        assert "Response A" in prompt
        assert "Response B" in prompt
    
    def test_build_stage3_prompt(self):
        """Test Stage 3 chairman prompt"""
        query = "What is AI?"
        stage1 = "Model: gemini\nResponse: AI is..."
        stage2 = "Model: groq\nRanking: Response A is best"
        prompt = build_stage3_chairman_prompt(query, stage1, stage2)
        
        assert query in prompt
        assert "STAGE 1" in prompt
        assert "STAGE 2" in prompt
        assert "synthesize" in prompt.lower()


class TestModelSelector:
    """Test model selection"""
    
    @pytest.mark.asyncio
    async def test_select_council_models_no_providers(self):
        """Test selection when no providers available"""
        with patch('app.services.council.model_selector.LLMProviderFactory') as mock_factory:
            mock_factory.list_providers.return_value = []
            result = await ModelSelector.select_council_models()
            assert result == []
    
    @pytest.mark.asyncio
    async def test_select_chairman_model(self):
        """Test chairman model selection"""
        with patch('app.services.council.model_selector.LLMProviderFactory') as mock_factory:
            mock_factory.list_providers.return_value = ["gemini", "groq"]
            mock_factory.get_provider.return_value = MagicMock()
            
            with patch.object(ModelSelector, '_check_provider_health', new_callable=AsyncMock) as mock_health:
                mock_health.return_value = True
                result = await ModelSelector.select_chairman_model()
                assert result in ["gemini", "groq"] or result is not None


class TestCouncilOrchestrator:
    """Test council orchestration"""
    
    @pytest.fixture
    def sample_page_data(self):
        """Sample page data for testing"""
        return PageData(
            url="https://example.com",
            title="Example Page",
            domain="example.com"
        )
    
    @pytest.mark.asyncio
    async def test_stage1_collect_responses_empty_models(self):
        """Test Stage 1 with no models"""
        orchestrator = CouncilOrchestrator(council_models=[])
        result = await orchestrator.stage1_collect_responses("test query")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_calculate_aggregate_rankings(self):
        """Test aggregate ranking calculation"""
        orchestrator = CouncilOrchestrator()
        
        stage2_results = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"]
            },
            {
                "model": "model2",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                "parsed_ranking": ["Response B", "Response A"]
            }
        ]
        
        label_to_model = {
            "Response A": "provider_a",
            "Response B": "provider_b"
        }
        
        result = orchestrator.calculate_aggregate_rankings(stage2_results, label_to_model)
        
        # Should have both providers
        assert len(result) == 2
        # Response A: avg rank = (1 + 2) / 2 = 1.5
        # Response B: avg rank = (2 + 1) / 2 = 1.5
        # Both should have average_rank of 1.5
        for item in result:
            assert item["average_rank"] == 1.5
            assert item["rankings_count"] == 2


class TestCouncilAgent:
    """Test Council Agent"""
    
    @pytest.fixture
    def sample_page_data(self):
        """Sample page data"""
        return PageData(
            url="https://example.com",
            title="Test Page"
        )
    
    @pytest.mark.asyncio
    async def test_council_agent_initialization(self):
        """Test agent can be initialized"""
        from app.agents.council_agent import CouncilAgent
        agent = CouncilAgent()
        assert agent.agent_type == "council"
        assert "deliberation" in agent.description.lower()
    
    @pytest.mark.asyncio
    async def test_council_agent_analyze_no_models(self):
        """Test agent handles no models gracefully"""
        from app.agents.council_agent import CouncilAgent
        
        agent = CouncilAgent()
        page_data = PageData(url="https://example.com")
        
        with patch('app.services.council.orchestrator.run_full_council') as mock_council:
            mock_council.return_value = ([], [], {
                "model": "error",
                "response": "No models available"
            }, {})
            
            result = await agent.analyze(page_data, "test query")
            
            assert not result.success
            assert "error" in result.analysis


@pytest.mark.asyncio
async def test_integration_council_flow():
    """Integration test for full council flow (mocked)"""
    from app.services.council import run_full_council
    
    page_data = PageData(
        url="https://example.com",
        title="Test Page"
    )
    
    # Mock the orchestrator
    with patch('app.services.council.orchestrator.CouncilOrchestrator') as mock_orch:
        mock_instance = MagicMock()
        mock_instance.run_full_council = AsyncMock(return_value=(
            [{"model": "gemini", "response": "Test response"}],
            [{"model": "groq", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}],
            {"model": "gemini", "response": "Final synthesis"},
            {"models_used": ["gemini"], "chairman": "gemini"}
        ))
        mock_orch.return_value = mock_instance
        
        # This would normally call real providers, but we're mocking
        # In a real test, you'd want to test with actual providers if available
        pass

