import os
import json
import logging
from collections.abc import AsyncIterable
from typing import Any, Dict, Optional, List
from uuid import uuid4

from tools import create_default_llm
from .workflow import GapAnalysisWorkflow
from .schemas import (
    StudentContext,
    GapAnalysisResponse,
    GapAnalysisResult
)


logger = logging.getLogger(__name__)


class GapAnalyzerAgent:
    """
    Educational Gap Analyzer Agent.
    
    This agent analyzes student questions about practice exercises to identify
    learning gaps, evaluate their importance, and provide prioritized recommendations
    for addressing those gaps.
    
    The agent uses a sophisticated LangGraph workflow that:
    1. Retrieves educational context from the knowledge graph
    2. Analyzes the student's question to identify specific learning gaps
    3. Evaluates gaps for pedagogical relevance and importance
    4. Prioritizes gaps and generates specific recommendations
    5. Provides a structured analysis with actionable insights
    """

    SYSTEM_INSTRUCTION = (
        'Eres un tutor inteligente especializado en análisis de gaps educativos. '
        'Tu función es analizar las preguntas de los estudiantes sobre ejercicios prácticos '
        'para identificar gaps específicos en su aprendizaje y proporcionar recomendaciones '
        'priorizadas para abordar esos gaps. '
        'Utilizas el contexto educativo completo incluyendo teoría, objetivos, ejercicios, '
        'soluciones y tips del profesor para realizar un análisis profundo y pedagógicamente relevante.'
    )

    def __init__(self):
        """Initialize the GapAnalyzer agent with workflow and LLM."""
        try:
            self.llm = create_default_llm()
            self.workflow = GapAnalysisWorkflow()
            logger.info("GapAnalyzer agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GapAnalyzer agent: {e}")
            raise

    def parse_student_input(self, query: str, context_id: str) -> StudentContext:
        """
        Parse student input to extract context information.
        
        Now expects a structured input with all context already provided.
        The query should be a JSON string or the system should provide
        structured context separately.
        """
        try:
            import json
            
            # Try to parse as JSON first
            try:
                if isinstance(query, str) and query.startswith('{'):
                    parsed_data = json.loads(query)
                    return StudentContext(**parsed_data)
            except json.JSONDecodeError:
                pass
            
            # If not JSON, create a basic context with defaults
            # In production, this should be enhanced to accept structured input
            logger.warning("Received unstructured input, using defaults")
            
            return StudentContext(
                student_question=query,
                conversation_history=[],
                subject_name="Bases de Datos Relacionales",
                practice_context="Práctica: 1 - Ejercicios básicos de bases de datos",
                exercise_context="Ejercicio: 1 - Consulta básica",
                solution_context="Consultar material de práctica",
                tips_context="Revisar conceptos teóricos"
            )
            
        except Exception as e:
            logger.error(f"Error parsing student input: {e}")
            # Return default context
            return StudentContext(
                student_question=query,
                conversation_history=[],
                subject_name="Bases de Datos Relacionales", 
                practice_context="Práctica: 1 - Ejercicios básicos",
                exercise_context="Ejercicio: 1 - Consulta básica",
                solution_context="Consultar material de práctica",
                tips_context="Revisar conceptos teóricos"
            )

    def format_gap_analysis_response(self, result: GapAnalysisResult) -> str:
        """
        Format the gap analysis result into a human-readable response.
        
        Args:
            result: Complete gap analysis result
            
        Returns:
            Formatted response string for the student
        """
        try:
            response_parts = []
            
            # Header
            response_parts.append("**ANÁLISIS DE GAPS EDUCATIVOS**")
            response_parts.append("=" * 50)
            
            # Summary
            response_parts.append(f"**Resumen:** {result.summary}")
            response_parts.append(f"**Confianza del análisis:** {result.confidence_score:.1%}")
            response_parts.append("")
            
            # Top priority gaps
            if result.prioritized_gaps:
                response_parts.append("**GAPS IDENTIFICADOS (por prioridad):**")
                response_parts.append("")
                
                for i, pg in enumerate(result.prioritized_gaps[:5], 1):  # Show top 5
                    gap = pg.gap
                    eval = pg.evaluation
                    
                    response_parts.append(f"**{i}. {gap.title}** (Prioridad: {eval.priority_score:.2f})")
                    response_parts.append(f"   Descripción: {gap.description}")
                    response_parts.append(f"   Categoría: {gap.category.value.title()}")
                    response_parts.append(f"   Severidad: {gap.severity.value.title()}")
                    response_parts.append(f"   Evidencia: {gap.evidence}")
                    
                    if gap.affected_concepts:
                        response_parts.append(f"   Conceptos afectados: {', '.join(gap.affected_concepts)}")
                    
                    if pg.recommended_actions:
                        response_parts.append("   **Acciones recomendadas:**")
                        for action in pg.recommended_actions:
                            response_parts.append(f"      • {action}")
                    
                    response_parts.append("")
            else:
                response_parts.append("No se identificaron gaps significativos en la comprensión.")
                response_parts.append("")
            
            # General recommendations
            if result.recommendations:
                response_parts.append("**RECOMENDACIONES GENERALES:**")
                for rec in result.recommendations:
                    response_parts.append(f"• {rec}")
                response_parts.append("")
            
            # Context information
            response_parts.append("**CONTEXTO DEL ANÁLISIS:**")
            response_parts.append(f"• Materia: {result.student_context.subject_name}")
            response_parts.append(f"• {result.student_context.practice_context}")
            response_parts.append(f"• {result.student_context.exercise_context}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return f"Error al formatear la respuesta del análisis: {str(e)}"

    async def stream(self, query: str, context_id: str) -> AsyncIterable[Dict[str, Any]]:
        """
        Stream the gap analysis process to provide real-time feedback.
        
        Args:
            query: Student's question
            context_id: Conversation context ID
            
        Yields:
            Progress updates during the analysis
        """
        try:
            # Step 1: Parse input and show progress
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Analizando pregunta y extrayendo contexto...',
            }
            
            student_context = self.parse_student_input(query, context_id)
            
            # Step 2: Start workflow
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Recuperando contexto educativo...',
            }
            
            # Step 3: Run analysis
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Identificando gaps de aprendizaje...',
            }
            
            # Step 4: Evaluation
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Evaluando relevancia pedagógica de los gaps...',
            }
            
            # Step 5: Prioritization
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Priorizando gaps y generando recomendaciones...',
            }
            
            # Run the actual analysis
            result = await self.workflow.run_analysis(student_context, context_id)
            
            # Step 6: Final result
            yield self.get_final_response(result)
            
        except Exception as e:
            logger.error(f"Error in streaming analysis: {e}")
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error durante el análisis: {str(e)}. Por favor, intenta nuevamente.',
            }

    def get_final_response(self, result: GapAnalysisResult) -> Dict[str, Any]:
        """
        Generate the final response based on analysis result.
        
        Args:
            result: Complete gap analysis result
            
        Returns:
            Final response dictionary for the A2A framework
        """
        try:
            if result.confidence_score > 0.7:
                status = 'completed'
            elif result.confidence_score > 0.3:
                status = 'completed'  # Still completed but with lower confidence
            else:
                status = 'error'
            
            formatted_message = self.format_gap_analysis_response(result)
            
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': formatted_message,
                'structured_response': GapAnalysisResponse(
                    status=status,
                    message=result.summary,
                    gaps_found=len(result.prioritized_gaps),
                    top_priority_gaps=[pg.gap.title for pg in result.prioritized_gaps[:3]],
                    detailed_analysis=result
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error al generar la respuesta final: {str(e)}',
            }

    def get_agent_response(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get agent response (compatibility method for A2A framework).
        
        This method is kept for compatibility with the existing A2A executor pattern.
        """
        # This is a simplified version - in practice, the streaming method handles most logic
        return {
            'is_task_complete': True,
            'require_user_input': False,
            'content': 'Análisis de gaps completado. Consulta el resultado anterior.',
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
