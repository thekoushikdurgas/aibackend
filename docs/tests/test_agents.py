"""
Agent tests for DurgasAI Backend
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.base import BaseAgent, AgentConfig, AgentResponse
from app.agents.page_analyzer import PageAnalyzerAgent
from app.agents.content_extractor import ContentExtractorAgent
from app.agents.seo_agent import SEOAgent
from app.agents.image_analyzer import ImageAnalyzerAgent
from app.agents.research_agent import ResearchAgent
from app.agents.router import AgentRouter
from app.models.schemas import PageData, AgentType


@pytest.fixture
def sample_page_data():
    """Sample page data for testing"""
    return PageData(
        url="https://example.com/test",
        title="Test Page",
        domain="example.com",
        html="""
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="A test page description">
            </head>
            <body>
                <header>
                    <nav>Navigation</nav>
                </header>
                <main>
                    <h1>Main Heading</h1>
                    <p>Test paragraph content.</p>
                    <img src="test.jpg" alt="Test image">
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        """,
        meta=[{"name": "description", "content": "A test page description"}],
        structure={
            "totalElements": 10,
            "links": 5,
            "images": 1
        },
        semantic={
            "header": True,
            "nav": True,
            "main": True,
            "footer": True
        },
        images=[
            {"src": "test.jpg", "alt": "Test image", "has_alt": True}
        ]
    )


class TestAgentRouter:
    """Tests for AgentRouter"""
    
    def test_list_agents(self):
        """Test listing available agents"""
        agents = AgentRouter.list_agents()
        assert len(agents) == 5
        assert "page_analyzer" in agents
        assert "seo" in agents
    
    def test_get_agent(self):
        """Test getting agent by type"""
        agent = AgentRouter.get_agent(AgentType.PAGE_ANALYZER)
        assert isinstance(agent, PageAnalyzerAgent)
    
    def test_detect_agent_type_seo(self):
        """Test auto-detection of SEO agent"""
        agent_type = AgentRouter._detect_agent_type("Check SEO issues")
        assert agent_type == AgentType.SEO
    
    def test_detect_agent_type_images(self):
        """Test auto-detection of image agent"""
        agent_type = AgentRouter._detect_agent_type("Analyze images on this page")
        assert agent_type == AgentType.IMAGE_ANALYZER
    
    def test_detect_agent_type_extract(self):
        """Test auto-detection of content extractor"""
        agent_type = AgentRouter._detect_agent_type("Extract contact information")
        assert agent_type == AgentType.CONTENT_EXTRACTOR
    
    def test_detect_agent_type_default(self):
        """Test default to research agent"""
        agent_type = AgentRouter._detect_agent_type("What is this page about?")
        assert agent_type == AgentType.RESEARCH


class TestPageAnalyzerAgent:
    """Tests for PageAnalyzerAgent"""
    
    def test_system_prompt(self):
        """Test agent has system prompt"""
        agent = PageAnalyzerAgent()
        assert agent.get_system_prompt()
        assert "structure" in agent.get_system_prompt().lower()
    
    def test_agent_type(self):
        """Test agent type is correct"""
        agent = PageAnalyzerAgent()
        assert agent.agent_type == "page_analyzer"


class TestSEOAgent:
    """Tests for SEOAgent"""
    
    def test_system_prompt(self):
        """Test agent has SEO-focused prompt"""
        agent = SEOAgent()
        prompt = agent.get_system_prompt()
        assert "seo" in prompt.lower()
        assert "title" in prompt.lower()
    
    def test_agent_type(self):
        """Test agent type is correct"""
        agent = SEOAgent()
        assert agent.agent_type == "seo"


class TestImageAnalyzerAgent:
    """Tests for ImageAnalyzerAgent"""
    
    def test_system_prompt(self):
        """Test agent has image-focused prompt"""
        agent = ImageAnalyzerAgent()
        prompt = agent.get_system_prompt()
        assert "image" in prompt.lower()
        assert "alt" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_no_images(self, sample_page_data):
        """Test analysis with no images"""
        sample_page_data.images = []
        agent = ImageAnalyzerAgent()
        
        # Mock LLM call
        with patch.object(agent, '_call_llm', new_callable=AsyncMock) as mock_llm:
            response = await agent.analyze(sample_page_data)
            assert response.agent_type == "image_analyzer"
            assert "No images found" in response.summary


class TestContentExtractorAgent:
    """Tests for ContentExtractorAgent"""
    
    def test_system_prompt(self):
        """Test agent has extraction-focused prompt"""
        agent = ContentExtractorAgent()
        prompt = agent.get_system_prompt()
        assert "extract" in prompt.lower()
        assert "entity" in prompt.lower()


class TestResearchAgent:
    """Tests for ResearchAgent"""
    
    def test_system_prompt(self):
        """Test agent has research-focused prompt"""
        agent = ResearchAgent()
        prompt = agent.get_system_prompt()
        assert "research" in prompt.lower() or "summar" in prompt.lower()


class TestAgentResponse:
    """Tests for AgentResponse dataclass"""
    
    def test_response_creation(self):
        """Test creating agent response"""
        response = AgentResponse(
            agent_type="test",
            analysis={"key": "value"},
            summary="Test summary",
            recommendations=["Rec 1", "Rec 2"]
        )
        assert response.agent_type == "test"
        assert response.summary == "Test summary"
        assert len(response.recommendations) == 2
        assert response.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
