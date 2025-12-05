"""
Agents package for AI customer service system.

Provides:
- Base agent classes
- Classifier for routing
- Specialist agents (Airtime, Data, Power, etc.)
- Research and retrieval agents
- Multi-agent coordination

Import concrete agents directly from their modules when needed, e.g.:

    from agents.classifier_v2 import ClassifierAgent
    from agents.retrieval import EnhancedRetriever
    from agents.multi_agent import MultiAgentCoordinator
"""

# Core agents
from agents.base_agent import BaseBusinessAgent
from agents.classifier import ClassifierAgent

# Research and retrieval
from agents.retrieval import (
    Chunk,
    RetrievalResult,
    ContextualChunker,
    HybridRetriever,
    CrossEncoderReranker,
    EnhancedRetriever,
)

# Multi-agent coordination
from agents.multi_agent import (
    ResearchStrategy,
    ResearchTask,
    ResearchFinding,
    SynthesizedResult,
    ResearchAgent,
    MultiAgentCoordinator,
    build_default_coordinator,
)

__all__ = [
    # Base
    "BaseBusinessAgent",
    "ClassifierAgent",
    # Retrieval
    "Chunk",
    "RetrievalResult",
    "ContextualChunker",
    "HybridRetriever",
    "CrossEncoderReranker",
    "EnhancedRetriever",
    # Multi-agent
    "ResearchStrategy",
    "ResearchTask",
    "ResearchFinding",
    "SynthesizedResult",
    "ResearchAgent",
    "MultiAgentCoordinator",
    "build_default_coordinator",
]
