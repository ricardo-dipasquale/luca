"""
Data schemas for the Orchestrator Agent.

This module defines the structured data models used throughout the orchestration workflow,
including conversation contexts, intent classification, memory management, and agent coordination.
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from gapanalyzer.schemas import StudentContext

class StudentIntent(str, Enum):
    """Types of student intents that can be identified."""
    THEORETICAL_QUESTION = "theoretical_question"      # Asking about concepts, definitions
    PRACTICAL_GENERAL = "practical_general"            # General practical questions not tied to specific KG exercise
    PRACTICAL_SPECIFIC = "practical_specific"          # Help with specific exercise/practice mapped in KG  
    EXPLORATION = "exploration"                         # Exploring related topics
    GREETING = "greeting"                               # Initial greetings/chat
    GOODBYE = "goodbye"                                 # Ending conversation
    OFF_TOPIC = "off_topic"                            # Not education-related


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    timestamp: datetime = Field(default_factory=datetime.now)
    role: Literal["student", "assistant"] = Field(description="Who sent this message")
    content: str = Field(description="The message content")
    intent: Optional[StudentIntent] = Field(default=None, description="Classified intent for student messages")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata about this turn")


class EducationalContext(BaseModel):
    """Current educational context from the conversation."""
    current_subject: Optional[str] = Field(default=None, description="Current subject being discussed")
    current_practice: Optional[int] = Field(default=None, description="Current practice number if any")
    current_exercise: Optional[str] = Field(default=None, description="Current exercise identifier if any")
    topics_discussed: List[str] = Field(default=[], description="Topics covered in conversation")
    difficulty_level: Optional[str] = Field(default=None, description="Assessed difficulty level")
    learning_objectives: List[str] = Field(default=[], description="Identified learning objectives")


class ConversationMemory(BaseModel):
    """Persistent memory for the conversation."""
    conversation_history: List[ConversationTurn] = Field(default=[], description="All conversation turns")
    educational_context: EducationalContext = Field(default_factory=EducationalContext)
    student_profile: Dict[str, Any] = Field(default={}, description="Inferred student characteristics")
    session_metadata: Dict[str, Any] = Field(default={}, description="Session-level metadata")
    
    def add_turn(self, role: str, content: str, intent: Optional[StudentIntent] = None, **metadata):
        """Add a new conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content, 
            intent=intent,
            metadata=metadata
        )
        self.conversation_history.append(turn)
        
    def get_recent_history(self, max_turns: int = 10) -> List[ConversationTurn]:
        """Get the most recent conversation turns."""
        return self.conversation_history[-max_turns:]
        
    def get_student_messages(self, max_messages: int = 5) -> List[str]:
        """Get recent student messages for context."""
        student_turns = [turn for turn in self.conversation_history if turn.role == "student"]
        return [turn.content for turn in student_turns[-max_messages:]]


class ConversationContext(BaseModel):
    """Complete context for orchestrator processing."""
    session_id: str = Field(description="Unique session identifier")
    current_message: str = Field(description="The student's current message")
    memory: ConversationMemory = Field(default_factory=ConversationMemory)
    agent_state: Dict[str, Any] = Field(default={}, description="Internal agent state")
    user_id: Optional[str] = Field(default=None, description="Unique user identifier")
    educational_subject: Optional[str] = Field(default=None, description="Current educational subject")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "current_message": "No entiendo por qué mi consulta SQL no funciona",
                "memory": {
                    "conversation_history": [
                        {
                            "role": "student",
                            "content": "Hola, estoy trabajando en la práctica 2",
                            "intent": "greeting"
                        }
                    ],
                    "educational_context": {
                        "current_subject": "Bases de Datos Relacionales",
                        "current_practice": 2,
                        "topics_discussed": ["SQL", "JOINs"]
                    }
                }
            }
        }


class IntentClassificationResult(BaseModel):
    """Result of intent classification."""
    predicted_intent: StudentIntent = Field(description="The predicted intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the prediction")
    reasoning: str = Field(description="Explanation of why this intent was chosen")
    requires_context: bool = Field(default=False, description="Whether additional context is needed")
    suggested_actions: List[str] = Field(default=[], description="Suggested actions based on intent")


class AgentRoutingDecision(BaseModel):
    """Decision about which agent to route to."""
    target_agent: Literal["gap_analyzer", "direct_response", "knowledge_retrieval"] = Field(
        description="Which agent or approach to use"
    )
    routing_reasoning: str = Field(description="Why this routing was chosen")
    agent_parameters: Dict[str, Any] = Field(default={}, description="Parameters to pass to the target agent")
    priority: Literal["high", "medium", "low"] = Field(default="medium", description="Processing priority")


class ResponseSynthesis(BaseModel):
    """Synthesized response from multiple sources."""
    primary_content: str = Field(description="Main response content")
    supporting_information: List[str] = Field(default=[], description="Additional supporting info")
    next_steps: List[str] = Field(default=[], description="Suggested next steps for the student")
    educational_guidance: Optional[str] = Field(default=None, description="Pedagogical guidance")
    confidence_level: float = Field(ge=0.0, le=1.0, description="Confidence in the response")


class EducationalSession(BaseModel):
    """Complete educational session state."""
    session_id: str = Field(description="Session identifier")
    student_id: Optional[str] = Field(default=None, description="Student identifier if available")
    start_time: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    conversation_memory: ConversationMemory = Field(default_factory=ConversationMemory)
    session_goals: List[str] = Field(default=[], description="Educational goals for this session")
    completed_objectives: List[str] = Field(default=[], description="Objectives achieved")
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()


class OrchestratorResponse(BaseModel):
    """Final response from the orchestrator agent."""
    status: Literal['success', 'needs_clarification', 'error'] = Field(default='success')
    message: str = Field(description="Primary response message to the student")
    educational_guidance: Optional[str] = Field(default=None, description="Educational guidance and next steps")
    intent_classification: Optional[IntentClassificationResult] = Field(default=None)
    routing_decision: Optional[AgentRoutingDecision] = Field(default=None)
    response_synthesis: Optional[ResponseSynthesis] = Field(default=None)
    conversation_context: Optional[ConversationContext] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Entiendo tu dificultad con la consulta SQL. Basándome en tu pregunta, parece que hay algunos gaps en tu comprensión de JOINs...",
                "educational_guidance": "Te sugiero revisar los conceptos de álgebra relacional antes de continuar con ejercicios más complejos.",
                "intent_classification": {
                    "predicted_intent": "gap_analysis",
                    "confidence": 0.85,
                    "reasoning": "El estudiante expresa dificultad específica con código"
                }
            }
        }


class WorkflowState(BaseModel):
    """State object for the orchestrator LangGraph workflow."""
    # Input
    conversation_context: Optional[ConversationContext] = None
    
    # Processing stages
    intent_result: Optional[IntentClassificationResult] = None
    agent_responses: Dict[str, Any] = Field(default={}, description="Responses from intent handlers")
    gap_analysis_result: Optional[Dict[str, Any]] = Field(default=None, description="Structured gap analysis results")
    
    # Synthesis
    response_synthesis: Optional[ResponseSynthesis] = None
    
    # Output
    final_response: Optional[OrchestratorResponse] = None
    
    # Control
    error_message: Optional[str] = None
    needs_clarification: bool = False
    retry_count: int = 0
    max_retries: int = 3
    
    student_context: StudentContext=None

    class Config:
        arbitrary_types_allowed = True


# Utility schemas for agent integration
class GapAnalysisRequest(BaseModel):
    """Request format for GapAnalyzer integration."""
    student_question: str
    practice_number: Optional[int] = None
    exercise_code: Optional[str] = None  # e.g., "1.d"
    conversation_context: List[str] = Field(default=[])
    subject_context: Optional[str] = None


class KnowledgeRetrievalRequest(BaseModel):
    """Request format for knowledge retrieval."""
    query: str
    subject_filter: Optional[str] = None
    topic_filter: Optional[str] = None
    retrieval_type: Literal["theoretical", "practical", "examples"] = "theoretical"