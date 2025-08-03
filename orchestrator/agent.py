"""
Orchestrator Agent - Educational Conversation Manager

This agent serves as the main coordinator for all educational interactions,
managing conversation state, routing to specialized agents, and synthesizing
responses for optimal student learning experiences.
"""

import os
import json
import logging
from collections.abc import AsyncIterable
from typing import Any, Dict, Optional, List
from uuid import uuid4
from datetime import datetime

from tools.observability import create_observed_llm
from .workflow import OrchestratorWorkflow
from .schemas import (
    ConversationContext,
    ConversationMemory,
    EducationalContext,
    EducationalSession,
    OrchestratorResponse,
    StudentIntent
)


logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Educational Conversation Orchestrator Agent.
    
    This agent manages the complete educational conversation experience by:
    1. Managing conversation memory and educational context
    2. Classifying student intents and routing to appropriate agents
    3. Coordinating responses from multiple specialized agents
    4. Synthesizing coherent, educational responses
    5. Providing pedagogical guidance and next-step recommendations
    
    The agent uses a sophisticated LangGraph workflow that handles
    multi-turn conversations with memory persistence and intelligent
    routing to specialized educational agents like GapAnalyzer.
    """

    SYSTEM_INSTRUCTION = (
        'Eres un coordinador de conversaciones trabajando para un tutor educativo universitario. '
        'Tu función es gestionar conversaciones educativas completas, clasificar '
        'las intenciones de los estudiantes, coordinar con agentes especializados, '
        'y sintetizar respuestas educativamente valiosas. '
        'Mantenés el contexto de la conversación, identificás oportunidades de aprendizaje, '
        'y proporcionás orientación pedagógica personalizada basada en las necesidades del estudiante.'
    )

    def __init__(self):
        """Initialize the Orchestrator agent with workflow and session management."""
        try:
            self.llm = create_observed_llm()
            self.workflow = OrchestratorWorkflow()
            self.active_sessions: Dict[str, EducationalSession] = {}
            logger.info("Orchestrator agent initialized successfully with Langfuse observability")
        except Exception as e:
            logger.error(f"Failed to initialize Orchestrator agent: {e}")
            raise

    def get_or_create_session(self, session_id: str, student_id: Optional[str] = None) -> EducationalSession:
        """
        Get existing session or create new one, loading memory from Neo4j if available.
        
        Args:
            session_id: Unique session identifier
            student_id: Optional student identifier
            
        Returns:
            Educational session with conversation memory (loaded from Neo4j if exists)
        """
        if session_id not in self.active_sessions:
            # Try to load existing memory from Neo4j checkpointer
            conversation_memory = self._load_conversation_memory(session_id)
            
            self.active_sessions[session_id] = EducationalSession(
                session_id=session_id,
                student_id=student_id,
                conversation_memory=conversation_memory
            )
            
            if conversation_memory.conversation_history:
                logger.info(f"Loaded existing session with {len(conversation_memory.conversation_history)} messages: {session_id}")
            else:
                logger.info(f"Created new educational session: {session_id}")
        else:
            self.active_sessions[session_id].update_activity()
            logger.info(f"Retrieved existing session: {session_id}")
            
        return self.active_sessions[session_id]
    
    def _load_conversation_memory(self, session_id: str) -> ConversationMemory:
        """
        Load conversation memory from Neo4j checkpointer.
        
        Args:
            session_id: Session identifier to load memory for
            
        Returns:
            ConversationMemory loaded from Neo4j, or empty if not found
        """
        try:
            # Access the checkpointer from workflow
            checkpointer = self.workflow.checkpointer
            
            if not checkpointer:
                logger.debug(f"No checkpointer available, creating empty memory for session: {session_id}")
                return ConversationMemory(educational_context=EducationalContext())
            
            # Try to load the latest checkpoint for this thread
            config = {"configurable": {"thread_id": session_id}}
            checkpoint = checkpointer.get(config)
            
            if checkpoint and hasattr(checkpoint, 'channel_values'):
                channel_values = checkpoint.channel_values
                if 'conversation_context' in channel_values:
                    stored_context = channel_values['conversation_context']
                    if hasattr(stored_context, 'memory') and hasattr(stored_context.memory, 'conversation_history'):
                        memory = stored_context.memory
                        if memory.conversation_history:
                            logger.info(f"Loaded conversation memory with {len(memory.conversation_history)} messages for session: {session_id}")
                            return memory
            
            logger.debug(f"No existing memory found for session: {session_id}")
            return ConversationMemory(educational_context=EducationalContext())
            
        except Exception as e:
            logger.warning(f"Failed to load conversation memory from Neo4j for session {session_id}: {e}")
            return ConversationMemory(educational_context=EducationalContext())

    def parse_student_input(self, query: str, session_id: str, student_id: Optional[str] = None) -> ConversationContext:
        """
        Parse student input and create conversation context.
        
        Accepts either:
        1. A JSON string containing structured conversation data
        2. A plain text message (creates context with session memory)
        3. A ConversationContext object directly (for testing)
        
        Args:
            query: Student message or structured JSON input
            session_id: Session identifier for memory management
            student_id: Optional student identifier
            
        Returns:
            ConversationContext with all necessary information
        """
        try:
            # Handle direct ConversationContext object (for testing)
            if isinstance(query, ConversationContext):
                logger.info("Received ConversationContext object directly")
                return query
            
            # Get or create session
            session = self.get_or_create_session(session_id, student_id)
            
            # Parse input
            if isinstance(query, str):
                query = query.strip()
                
                # Check if it's JSON structured input
                if query.startswith('{') and query.endswith('}'):
                    try:
                        parsed_data = json.loads(query)
                        logger.info("Parsed structured JSON input for ConversationContext")
                        
                        # Create context from parsed data
                        context = ConversationContext(
                            session_id=session_id,
                            current_message=parsed_data.get("current_message", ""),
                            memory=session.conversation_memory
                        )
                        
                        # Update memory if additional context provided
                        if "educational_context" in parsed_data:
                            edu_ctx = parsed_data["educational_context"]
                            context.memory.educational_context.current_subject = edu_ctx.get("current_subject")
                            context.memory.educational_context.current_practice = edu_ctx.get("current_practice")
                            
                        return context
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON input: {e}. Treating as plain text.")
                    except Exception as e:
                        logger.error(f"Error creating ConversationContext from JSON: {e}")
                
                # Handle plain text input
                logger.info("Creating context for plain text input")
                return ConversationContext(
                    session_id=session_id,
                    current_message=query,
                    memory=session.conversation_memory
                )
            
            # Handle unexpected input types
            logger.error(f"Unexpected input type: {type(query)}. Converting to string.")
            return ConversationContext(
                session_id=session_id,
                current_message=str(query),
                memory=session.conversation_memory
            )
            
        except Exception as e:
            logger.error(f"Critical error parsing student input: {e}")
            # Return safe default context
            return ConversationContext(
                session_id=session_id,
                current_message="Error al procesar la entrada del estudiante",
                memory=ConversationMemory()
            )

    def format_orchestrator_response(self, result: OrchestratorResponse) -> str:
        """
        Format the orchestrator response into a human-readable message.
        
        Args:
            result: Complete orchestrator response
            
        Returns:
            Formatted response string for the student
        """
        try:
            response_parts = []
            
            # Main message
            response_parts.append(result.message)
            
            # Add educational guidance if present (integrated in main response)
            if result.educational_guidance:
                response_parts.append("")
                response_parts.append(result.educational_guidance)
            
            # Add intent information for debugging (optional)
            if result.intent_classification and logger.isEnabledFor(logging.DEBUG):
                response_parts.append("")
                response_parts.append(f"*[Intención detectada: {result.intent_classification.predicted_intent.value}]*")
            
            return "\\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return f"Error al formatear la respuesta: {str(e)}"

    async def stream(self, query: str, session_id: str, student_id: Optional[str] = None, educational_subject: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Stream the orchestration process to provide real-time feedback.
        
        Args:
            query: Student message or structured JSON input
            session_id: Session identifier for conversation continuity
            student_id: Optional student identifier
            educational_subject: Optional subject to inject into educational context
            config: Optional LangGraph config (for callbacks, etc.)
            
        Yields:
            Progress updates during orchestration with structured responses
        """
        try:
            # Step 1: Parse input and show progress
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Analizando tu mensaje y recuperando contexto de conversación...',
            }
            
            conversation_context = self.parse_student_input(query, session_id, student_id)
            
            # Inject educational subject if provided
            if educational_subject:
                conversation_context.memory.educational_context.current_subject = educational_subject
                logger.info(f"Injected educational subject: {educational_subject} for session {session_id}")
            
            # Step 2: Intent classification
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Clasificando tu intención y determinando la mejor forma de ayudarte...',
            }
            
            # Step 3: Agent routing
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Coordinando con agentes especializados...',
            }
            
            # Step 4: Processing
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Procesando tu consulta y generando respuesta personalizada...',
            }
            
            # Step 5: Synthesis
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Sintetizando información y preparando orientación educativa...',
            }
            
            # Run the actual orchestration with optional config
            result = await self.workflow.run_conversation(conversation_context, session_id, config)
            
            # Step 6: Final result
            yield self.get_final_response(result)
            
        except Exception as e:
            logger.error(f"Error in streaming orchestration: {e}")
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error durante el procesamiento: {str(e)}. Por favor, intenta reformular tu pregunta.',
            }

    def get_final_response(self, result: OrchestratorResponse) -> Dict[str, Any]:
        """
        Generate the final response based on orchestration result.
        
        Args:
            result: Complete orchestrator response
            
        Returns:
            Final response dictionary for the A2A framework
        """
        try:
            status = 'completed' if result.status == 'success' else 'error'
            
            formatted_message = self.format_orchestrator_response(result)
            
            # Determine if user input is required
            require_input = (
                result.status == 'needs_clarification' or 
                (result.intent_classification and result.intent_classification.requires_context)
            )
            
            return {
                'is_task_complete': True,
                'require_user_input': require_input,
                'content': formatted_message,
                'structured_response': {
                    'status': result.status,
                    'intent': result.intent_classification.predicted_intent.value if result.intent_classification else None,
                    'routing_agent': result.routing_decision.target_agent if result.routing_decision else None,
                    'educational_context': {
                        'subject': result.conversation_context.memory.educational_context.current_subject if result.conversation_context else None,
                        'practice': result.conversation_context.memory.educational_context.current_practice if result.conversation_context else None,
                        'topics': result.conversation_context.memory.educational_context.topics_discussed if result.conversation_context else []
                    },
                    'detailed_response': result
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error al generar la respuesta final: {str(e)}',
            }

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of educational session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with session summary information
        """
        try:
            if session_id not in self.active_sessions:
                return {"error": "Session not found"}
            
            session = self.active_sessions[session_id]
            memory = session.conversation_memory
            
            return {
                "session_id": session_id,
                "start_time": session.start_time.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "message_count": len(memory.conversation_history),
                "educational_context": {
                    "current_subject": memory.educational_context.current_subject,
                    "current_practice": memory.educational_context.current_practice,
                    "topics_discussed": memory.educational_context.topics_discussed,
                    "learning_objectives": memory.educational_context.learning_objectives
                },
                "session_goals": session.session_goals,
                "completed_objectives": session.completed_objectives,
                "recent_intents": [
                    turn.intent.value if turn.intent else "unknown" 
                    for turn in memory.get_recent_history(5) 
                    if turn.role == "student"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return {"error": str(e)}

    def cleanup_inactive_sessions(self, max_inactive_hours: int = 24):
        """
        Clean up inactive sessions to manage memory.
        
        Args:
            max_inactive_hours: Maximum hours before considering session inactive
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=max_inactive_hours)
            inactive_sessions = [
                session_id for session_id, session in self.active_sessions.items()
                if session.last_activity < cutoff_time
            ]
            
            for session_id in inactive_sessions:
                del self.active_sessions[session_id]
                logger.info(f"Cleaned up inactive session: {session_id}")
                
            if inactive_sessions:
                logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")

    def get_agent_response(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get agent response (compatibility method for A2A framework).
        
        This method is kept for compatibility with the existing A2A executor pattern.
        """
        return {
            'is_task_complete': True,
            'require_user_input': False,
            'content': 'Orquestación completada. Consulta el resultado anterior.',
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain', 'application/json']