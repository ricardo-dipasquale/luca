"""
Orchestrator Agent - Educational Conversation Manager

This package contains the orchestrator agent responsible for managing the complete
educational conversation experience. It handles:

- Intent classification of student questions
- Memory and conversation state management  
- Routing to specialized agents (like GapAnalyzer)
- Synthesis of responses from multiple sources
- Educational guidance and next-step recommendations

The orchestrator serves as the main entry point for students and coordinates
all interactions within the educational AI ecosystem.
"""

from .agent import OrchestratorAgent
from .schemas import (
    ConversationContext,
    StudentIntent,
    OrchestratorResponse,
    EducationalSession
)

__all__ = [
    'OrchestratorAgent',
    'ConversationContext', 
    'StudentIntent',
    'OrchestratorResponse',
    'EducationalSession'
]