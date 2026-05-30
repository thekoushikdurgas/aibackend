"""
Models module - Pydantic schemas and database models
"""

from .schemas import (
    ChatRequest,
    ChatResponse,
    AgentRequest,
    AgentResponse,
    PageData,
    RAGIngestRequest,
    RAGSearchRequest,
    RAGSearchResponse,
    TokenRequest,
    TokenResponse,
    HealthResponse,
    BenchmarkRequest,
    BenchmarkResult,
    CompareBenchmarkRequest,
    ComparativeBenchmarkResult,
    StressTestRequest,
    StressTestResult,
    BenchmarkHistoryItem,
    ProviderStats,
    ModelComparison,
    PerformanceTrend,
    LeaderboardEntry,
)

# Import database models
from .metrics import BenchmarkRun, ProviderMetric, LatencyHistory, ErrorLog, Base

# Import conversation models
from .conversation import Conversation, Message, MessageRole
from .claude_code_session import ClaudeCodeSessionModel

# Import DurgasOS desktop persistence
from .durgasos_desktop import (
    TodoTaskModel,
    TodoWorkspaceModel,
    WorkflowDefinitionModel,
    WorkflowRunModel,
    WidgetLayoutModel,
)

# Import Road Rash models
from .roadrash import (
    RoadRashFriendModel,
    RoadRashLeaderboardModel,
    RoadRashProfileModel,
)

# Import Sudoku models
from .sudoku import (
    SudokuLeaderboardModel,
    SudokuProfileModel,
)

# Import Pokemon models
from .pokemon import (
    PokemonLeaderboardModel,
    PokemonProfileModel,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "AgentRequest",
    "AgentResponse",
    "PageData",
    "RAGIngestRequest",
    "RAGSearchRequest",
    "RAGSearchResponse",
    "TokenRequest",
    "TokenResponse",
    "HealthResponse",
    "BenchmarkRequest",
    "BenchmarkResult",
    "CompareBenchmarkRequest",
    "ComparativeBenchmarkResult",
    "StressTestRequest",
    "StressTestResult",
    "BenchmarkHistoryItem",
    "ProviderStats",
    "ModelComparison",
    "PerformanceTrend",
    "LeaderboardEntry",
    "BenchmarkRun",
    "ProviderMetric",
    "LatencyHistory",
    "ErrorLog",
    "Base",
    "Conversation",
    "Message",
    "MessageRole",
    "ClaudeCodeSessionModel",
    "WorkflowDefinitionModel",
    "WorkflowRunModel",
    "WidgetLayoutModel",
    "TodoWorkspaceModel",
    "TodoTaskModel",
    "RoadRashLeaderboardModel",
    "RoadRashProfileModel",
    "RoadRashFriendModel",
    "SudokuLeaderboardModel",
    "SudokuProfileModel",
    "PokemonLeaderboardModel",
    "PokemonProfileModel",
]
