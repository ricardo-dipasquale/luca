"""
Orchestrator Agent Executor for A2A Framework Integration.

This module handles the A2A protocol integration for the orchestrator agent,
managing request/response lifecycle and agent card serving.
"""

import logging
from typing import Any, AsyncIterable, Dict

from .agent import OrchestratorAgent
from .schemas import ConversationContext, OrchestratorResponse


logger = logging.getLogger(__name__)


class OrchestratorAgentExecutor:
    """
    Executor class for Orchestrator Agent following A2A protocol patterns.
    
    This class handles:
    1. A2A request processing and validation
    2. Streaming response management
    3. Agent card serving
    4. Session management for educational conversations
    """
    
    def __init__(self):
        """Initialize the executor with orchestrator agent."""
        try:
            self.agent = OrchestratorAgent()
            logger.info("OrchestratorAgentExecutor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OrchestratorAgentExecutor: {e}")
            raise
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterable[Dict[str, Any]]:
        """
        Stream orchestrator responses following A2A protocol.
        
        Args:
            request: A2A request containing student message and context
            context: A2A context including session information
            
        Yields:
            A2A-compliant response chunks during orchestration
        """
        try:
            # Extract session information
            session_id = context.get('session_id', 'default_session')
            student_id = context.get('user_id')  # Optional student identifier
            educational_subject = context.get('educational_subject')  # Optional subject injection
            
            # Extract message from request
            user_message = request.get('message', '')
            if not user_message:
                yield {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': 'Por favor, enviá tu pregunta o consulta educativa.',
                }
                return
            
            # Extract config for LangGraph callbacks if provided
            langfuse_config = context.get('config')
            
            # Stream the orchestration process with subject injection
            async for chunk in self.agent.stream(user_message, session_id, student_id, educational_subject, langfuse_config):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in orchestrator streaming: {e}")
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error en el procesamiento: {str(e)}. Por favor, intentá nuevamente.',
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Return the agent card for A2A framework discovery.
        
        Returns:
            Dictionary containing agent metadata and capabilities
        """
        return {
            'name': 'Orchestrator Agent',
            'description': 'Agente orquestador para conversaciones educativas inteligentes de la Facultad de Ingeniería',
            'detailed_description': (
                'El Agente Orquestador gestiona conversaciones educativas completas, '
                'clasificando intenciones de estudiantes, coordinando con agentes especializados '
                'como el GapAnalyzer, y sintetizando respuestas educativamente valiosas. '
                'Mantiene memoria de conversación, proporciona orientación pedagógica personalizada, '
                'y coordina el ecosistema completo de agentes educativos.'
            ),
            'version': '1.0.0',
            'capabilities': [
                'Gestión de conversaciones educativas multi-turno',
                'Clasificación de intenciones de estudiantes',
                'Coordinación con agentes especializados (GapAnalyzer)',
                'Memoria persistente de conversación',
                'Síntesis de respuestas de múltiples fuentes',
                'Orientación pedagógica personalizada',
                'Enrutamiento inteligente de consultas',
                'Gestión de contexto educativo'
            ],
            'use_cases': [
                'Consultas teóricas sobre materias de Ingeniería',
                'Ayuda práctica con ejercicios y problemas',
                'Análisis de gaps de aprendizaje',
                'Orientación pedagógica y próximos pasos',
                'Exploración de temas relacionados',
                'Clarificación de conceptos',
                'Autoevaluación y validación de conocimiento'
            ],
            'supported_content_types': ['text', 'text/plain', 'application/json'],
            'input_schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'description': 'Mensaje o consulta del estudiante'
                    },
                    'educational_context': {
                        'type': 'object',
                        'properties': {
                            'current_subject': {'type': 'string'},
                            'current_practice': {'type': 'integer'},
                            'topics_discussed': {'type': 'array', 'items': {'type': 'string'}}
                        },
                        'description': 'Contexto educativo opcional para mayor precisión'
                    }
                },
                'required': ['message']
            },
            'output_schema': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'enum': ['success', 'needs_clarification', 'error']
                    },
                    'message': {
                        'type': 'string',
                        'description': 'Respuesta principal para el estudiante'
                    },
                    'educational_guidance': {
                        'type': 'string',
                        'description': 'Orientación pedagógica y próximos pasos'
                    },
                    'intent_classification': {
                        'type': 'object',
                        'description': 'Clasificación de intención detectada'
                    },
                    'educational_context': {
                        'type': 'object',
                        'description': 'Contexto educativo actualizado'
                    }
                }
            },
            'examples': [
                {
                    'name': 'Consulta teórica',
                    'input': {
                        'message': '¿Qué es un LEFT JOIN y cuándo se usa?'
                    },
                    'output': {
                        'status': 'success',
                        'message': 'Un LEFT JOIN es una operación de álgebra relacional que...',
                        'educational_guidance': 'Te sugiero practicar con ejercicios simples de JOIN para consolidar el concepto.'
                    }
                },
                {
                    'name': 'Ayuda práctica',
                    'input': {
                        'message': 'Mi consulta SQL no funciona, devuelve resultados duplicados',
                        'educational_context': {
                            'current_subject': 'Bases de Datos Relacionales',
                            'current_practice': 2
                        }
                    },
                    'output': {
                        'status': 'success',
                        'message': 'Analizando tu consulta, parece que hay gaps en la comprensión de JOINs...',
                        'educational_guidance': 'Revisá los conceptos de normalización antes de continuar.'
                    }
                }
            ],
            'tags': ['education', 'orchestrator', 'conversation', 'learning', 'engineering'],
            'provider': 'Luca Educational AI System',
            'contact': 'https://github.com/luca-educational-ai'
        }
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a specific educational session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with session information
        """
        try:
            return self.agent.get_session_summary(session_id)
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {"error": str(e)}
    
    def cleanup_sessions(self, max_inactive_hours: int = 24):
        """
        Clean up inactive sessions.
        
        Args:
            max_inactive_hours: Hours before considering session inactive
        """
        try:
            self.agent.cleanup_inactive_sessions(max_inactive_hours)
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    async def handle_direct_request(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        Handle direct request without streaming (for testing or sync usage).
        
        Args:
            message: Student message
            session_id: Optional session identifier
            
        Returns:
            Complete orchestrator response
        """
        try:
            session_id = session_id or 'direct_request_session'
            
            # Create conversation context
            conversation_context = self.agent.parse_student_input(message, session_id)
            
            # Run orchestration workflow
            result = await self.agent.workflow.run_conversation(conversation_context, session_id)
            
            # Return formatted response
            return self.agent.get_final_response(result)
            
        except Exception as e:
            logger.error(f"Error in direct request handling: {e}")
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error procesando la solicitud: {str(e)}',
            }