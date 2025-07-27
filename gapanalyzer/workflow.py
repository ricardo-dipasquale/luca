"""
LangGraph workflow for educational gap analysis.

This module implements the complete workflow for analyzing learning gaps in student questions,
including context retrieval, gap identification, evaluation, and prioritization.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from tools import get_kg_tools, create_default_llm
from tools.kg_tools import (
    get_theoretical_content_tool
)
from tools.observability import create_observed_llm
from kg.persistence import create_neo4j_persistence
from .schemas import (
    WorkflowState,
    StudentContext,
    EducationalContext,
    IdentifiedGap,
    GapEvaluation,
    GapAnalysisResult,
    GapAnalysisResponse,
    GapSeverity,
    GapCategory
)


logger = logging.getLogger(__name__)


class GapAnalysisWorkflow:
    """
    LangGraph workflow for educational gap analysis.
    
    The workflow consists of the following nodes:
    1. retrieve_context: Get educational context from KG
    2. analyze_gaps: Identify learning gaps from student question
    3. evaluate_gaps: Assess relevance and importance of gaps
    4. generate_response: Create final structured response
    """
    
    def __init__(self, use_neo4j_persistence: bool = True):
        """Initialize the workflow with LLM and tools."""
        self.llm = create_observed_llm()
        
        # Initialize persistence layer
        if use_neo4j_persistence:
            try:
                self.checkpointer, self.memory_store = create_neo4j_persistence()
                logger.info("Using Neo4j persistence for gap analysis memory")
            except Exception as e:
                logger.warning(f"Failed to initialize Neo4j persistence, falling back to in-memory: {e}")
                self.checkpointer = MemorySaver()
                self.memory_store = None
        else:
            self.checkpointer = MemorySaver()
            self.memory_store = None
            
        self.graph = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("validate_context", self._validate_context)
        workflow.add_node("analyze_gaps", self._analyze_gaps)
        workflow.add_node("evaluate_gaps", self._evaluate_gaps)
        workflow.add_node("feedback_analysis", self._feedback_analysis)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("validate_context")
        
        # Add basic edges
        workflow.add_edge("validate_context", "analyze_gaps")
        workflow.add_edge("analyze_gaps", "evaluate_gaps")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        # Add conditional edges for feedback loop
        workflow.add_conditional_edges(
            "evaluate_gaps",
            self._should_do_feedback,
            {
                "feedback": "feedback_analysis",
                "complete": "generate_response",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "feedback_analysis",
            self._feedback_decision,
            {
                "retry": "analyze_gaps",  # Go back to analysis with feedback
                "complete": "generate_response",
                "error": "handle_error"
            }
        )
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "validate_context",
            self._should_continue,
            {
                "continue": "analyze_gaps",
                "error": "handle_error"
            }
        )
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _should_continue(self, state: WorkflowState) -> str:
        """Determine if workflow should continue or handle error."""
        if state.error_message:
            return "error"
        return "continue"
    
    def _should_do_feedback(self, state: WorkflowState) -> str:
        """Determine if feedback analysis is needed."""
        if state.error_message:
            return "error"
        
        # Check if we should do feedback based on gap analysis quality
        if (state.feedback_iterations < state.max_feedback_iterations and
            len(state.evaluated_gaps) > 0):
            
            # Analyze if gaps seem incomplete or low confidence
            avg_confidence = sum(eval_gap.priority_score for eval_gap in state.evaluated_gaps) / len(state.evaluated_gaps)
            
            if avg_confidence < 0.6 or state.educational_context.needs_theory_lookup:
                state.needs_feedback = True
                state.feedback_reason = "Baja confianza en análisis o falta contexto teórico"
                return "feedback"
        
        return "complete"
    
    def _feedback_decision(self, state: WorkflowState) -> str:
        """Decide whether to retry analysis or complete."""
        if state.error_message:
            return "error"
        
        if state.needs_feedback and state.feedback_iterations < state.max_feedback_iterations:
            return "retry"
        
        return "complete"
    
    async def _validate_context(self, state: WorkflowState) -> WorkflowState:
        """
        Node 1: Validate and prepare educational context.
        
        This node validates the provided context and determines if additional
        theoretical context is needed for gap analysis.
        """
        try:
            logger.info("Validating educational context")
            
            if not state.student_context:
                state.error_message = "No student context provided"
                return state
            
            ctx = state.student_context
            
            # Check for specific error indicators in context
            error_indicators = [
                "Error al procesar práctica",
                "Error al procesar ejercicio", 
                "no encontrada",
                "no encontrado",
                "Práctica no encontrada",
                "Ejercicio no encontrado"
            ]
            
            # Check if context indicates missing content
            context_text = f"{ctx.practice_context} {ctx.exercise_context}".lower()
            for indicator in error_indicators:
                if indicator.lower() in context_text:
                    state.error_message = f"Contenido educativo no encontrado: {indicator}"
                    logger.warning(f"Detected missing content indicator: {indicator}")
                    return state
            
            # Validate required context fields
            context_complete = True
            needs_theory = True
            
            if not ctx.practice_context or len(ctx.practice_context) < 20:
                context_complete = False
                logger.warning("Practice context appears incomplete")
            
            if not ctx.exercise_context or len(ctx.exercise_context) < 20:
                context_complete = False
                logger.warning("Exercise context appears incomplete")
            
            # If context is severely incomplete, it might indicate missing content
            if not context_complete and (not ctx.practice_context or not ctx.exercise_context):
                state.error_message = "El ejercicio o práctica solicitada no existe o no está disponible"
                logger.warning("Context too incomplete - likely missing content")
                return state
            
            # Create educational context
            educational_context = EducationalContext(
                context_complete=context_complete,
                needs_theory_lookup=needs_theory
            )
            
            state.educational_context = educational_context
            logger.info(f"Educational context validated for {ctx.subject_name}")
            
        except Exception as e:
            logger.error(f"Error validating context: {e}")
            state.error_message = f"Failed to validate educational context: {str(e)}"
        
        return state
    
    
    async def _analyze_gaps(self, state: WorkflowState) -> WorkflowState:
        """
        Node 2: Analyze the student's question to identify learning gaps.
        
        Uses the LLM to perform deep analysis of the student's question against
        the educational context to identify specific learning gaps.
        """
        try:
            logger.info("Analyzing learning gaps")
            
            # Create structured prompt for gap analysis
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """Sos un experto en análisis de gaps educativos. Tu tarea es identificar gaps específicos en el aprendizaje del estudiante basándote en su pregunta y el contexto educativo proporcionado.

CONTEXTO EDUCATIVO:
Materia: {subject_name}

{practice_context}

{exercise_context}

{solution_context}

{tips_context}

Teoría adicional: {theory_background}

ITERACIÓN: {iteration_info}

INSTRUCCIONES:
1. Analizá la pregunta del estudiante en el contexto del material educativo
2. Identificá gaps específicos de aprendizaje (NO genéricos) que apunten a la solución de la práctica prestando atención al material provisto.
3. No identifiques gaps que contradigan los tips provistos que son los lineamientos del profesor (tips).
4. Clasificá cada gap por categoría: conceptual, procedural, theoretical, practical, prerequisite, communication
5. Asigná severidad: critical, high, medium, low
6. Proporcioná evidencia específica de la pregunta que indica cada gap
7. Identificá conceptos afectados y conocimiento prerequisito faltante
8. Usá español argentino en toda la respuesta

Respondé en formato JSON con esta estructura:
{{
  "gaps": [
    {{
      "gap_id": "gap_001",
      "title": "Título conciso del gap",
      "description": "Descripción detallada del gap identificado",
      "category": "conceptual|procedural|theoretical|practical|prerequisite|communication",
      "severity": "critical|high|medium|low", 
      "evidence": "Evidencia específica de la pregunta del estudiante",
      "affected_concepts": ["concepto1", "concepto2"],
      "prerequisite_knowledge": ["prerequisito1", "prerequisito2"]
    }}
  ]
}}

SÉ ESPECÍFICO Y BASADO EN EVIDENCIA. No inventes gaps genéricos."""),
                ("human", """PREGUNTA DEL ESTUDIANTE: {student_question}

HISTORIAL DE CONVERSACIÓN: {conversation_history}

Analizá esta pregunta e identificá los gaps de aprendizaje específicos.""")
            ])
            
            # Prepare context for the prompt
            ctx = state.student_context
            edu_ctx = state.educational_context
            
            # Prepare iteration information
            iteration_info = f"Iteración {state.feedback_iterations + 1} de máximo {state.max_feedback_iterations}"
            if state.feedback_iterations > 0:
                iteration_info += f" (Feedback previo: {state.feedback_reason or 'Mejora general'})"
            
            formatted_prompt = analysis_prompt.format_messages(
                subject_name=ctx.subject_name,
                practice_context=ctx.practice_context,
                exercise_context=ctx.exercise_context,
                solution_context=ctx.solution_context or "No se proporcionó solución esperada",
                tips_context=ctx.tips_context or "No se proporcionaron tips",
                theory_background=edu_ctx.theory_background or "No se recuperó teoría adicional",
                iteration_info=iteration_info,
                student_question=ctx.student_question,
                conversation_history="\n".join(ctx.conversation_history) if ctx.conversation_history else "No hay historial previo"
            )
            
            # Get LLM response (automatically observed via Langfuse callback)
            response = await self.llm.ainvoke(formatted_prompt)
            
            # Parse JSON response
            try:
                response_text = response.content
                # Extract JSON from response (in case there's extra text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_content = response_text[json_start:json_end]
                
                gap_data = json.loads(json_content)
                
                # Convert to IdentifiedGap objects
                identified_gaps = []
                for i, gap_dict in enumerate(gap_data.get("gaps", [])):
                    gap = IdentifiedGap(
                        gap_id=gap_dict.get("gap_id", f"gap_{i+1:03d}"),
                        title=gap_dict.get("title", "Gap sin título"),
                        description=gap_dict.get("description", ""),
                        category=GapCategory(gap_dict.get("category", "conceptual")),
                        severity=GapSeverity(gap_dict.get("severity", "medium")),
                        evidence=gap_dict.get("evidence", ""),
                        affected_concepts=gap_dict.get("affected_concepts", []),
                        prerequisite_knowledge=gap_dict.get("prerequisite_knowledge", [])
                    )
                    identified_gaps.append(gap)
                
                state.raw_gaps = identified_gaps
                logger.info(f"Identified {len(identified_gaps)} learning gaps")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse gap analysis JSON: {e}")
                logger.error(f"Response content: {response.content}")
                state.error_message = f"Failed to parse gap analysis result: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in gap analysis: {e}")
            state.error_message = f"Gap analysis failed: {str(e)}"
        
        return state
    
    async def _evaluate_gaps(self, state: WorkflowState) -> WorkflowState:
        """
        Node 3: Evaluate the relevance and importance of identified gaps.
        
        This node evaluates each gap for pedagogical relevance, impact on learning,
        and addressability to provide a comprehensive assessment.
        """
        try:
            logger.info("Evaluating gap relevance and importance")
            
            evaluation_prompt = ChatPromptTemplate.from_messages([
                ("system", """Sos un pedagogo experto evaluando la relevancia e importancia de gaps de aprendizaje identificados en materias de la Facultad de Ingeniería en el ámbito de sus prácticas.

Para cada gap, evaluá:
1. RELEVANCIA PEDAGÓGICA (0-1): ¿Qué tan relevante es este gap para los objetivos actuales de aprendizaje?
2. IMPACTO EN APRENDIZAJE (0-1): ¿Cuánto impacta este gap en el progreso general del estudiante?
3. DIRECCIONABILIDAD (0-1): ¿Qué tan fácil es de abordar este gap? (1 = muy fácil, 0 = muy difícil)

CONTEXTO EDUCATIVO:
{practice_context}
{exercise_context}

Respondé en formato JSON usando español argentino:
{{
  "evaluations": [
    {{
      "gap_id": "gap_id_from_input",
      "pedagogical_relevance": 0.0-1.0,
      "impact_on_learning": 0.0-1.0,
      "addressability": 0.0-1.0,
      "priority_score": 0.0-1.0,
      "evaluation_reasoning": "Explicación de la evaluación"
    }}
  ]
}}

El priority_score debe ser una combinación ponderada: (relevancia * 0.4 + impacto * 0.4 + direccionabilidad * 0.2)"""),
                ("human", """GAPS IDENTIFICADOS:
{gaps_json}

Evalúa cada gap según los criterios pedagógicos.""")
            ])
            
            # Prepare gaps for evaluation
            gaps_for_eval = []
            for gap in state.raw_gaps:
                gaps_for_eval.append({
                    "gap_id": gap.gap_id,
                    "title": gap.title,
                    "description": gap.description,
                    "category": gap.category.value,
                    "severity": gap.severity.value,
                    "evidence": gap.evidence
                })
            
            formatted_prompt = evaluation_prompt.format_messages(
                practice_context=state.student_context.practice_context,
                exercise_context=state.student_context.exercise_context,
                gaps_json=json.dumps(gaps_for_eval, indent=2, ensure_ascii=False)
            )
            
            # Get LLM response (automatically observed via Langfuse callback)
            response = await self.llm.ainvoke(formatted_prompt)
            
            # Parse evaluation results
            try:
                response_text = response.content
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_content = response_text[json_start:json_end]
                
                eval_data = json.loads(json_content)
                
                evaluations = []
                for eval_dict in eval_data.get("evaluations", []):
                    evaluation = GapEvaluation(
                        gap_id=eval_dict.get("gap_id", ""),
                        pedagogical_relevance=float(eval_dict.get("pedagogical_relevance", 0.5)),
                        impact_on_learning=float(eval_dict.get("impact_on_learning", 0.5)),
                        addressability=float(eval_dict.get("addressability", 0.5)),
                        priority_score=float(eval_dict.get("priority_score", 0.5)),
                        evaluation_reasoning=eval_dict.get("evaluation_reasoning", "")
                    )
                    evaluations.append(evaluation)
                
                state.evaluated_gaps = evaluations
                logger.info(f"Evaluated {len(evaluations)} gaps")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse evaluation JSON: {e}")
                state.error_message = f"Failed to parse gap evaluation result: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in gap evaluation: {e}")
            state.error_message = f"Gap evaluation failed: {str(e)}"
        
        return state
    
    
    async def _generate_response(self, state: WorkflowState) -> WorkflowState:
        """
        Node 5: Generate the final structured response.
        
        Creates the complete analysis result and formats it for the A2A framework.
        """
        try:
            logger.info("Generating final response")
            
            # Calculate confidence score based on various factors
            confidence_factors = []
            
            # Factor 1: Number of gaps found (more gaps = more thorough analysis)
            gap_count = len(state.raw_gaps)
            if gap_count >= 3:
                confidence_factors.append(0.9)
            elif gap_count >= 2:
                confidence_factors.append(0.8)
            elif gap_count >= 1:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.4)
            
            # Factor 2: Quality of educational context
            if state.educational_context: #and state.educational_context.exercise_statement:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
            
            # Factor 3: Evaluation completeness
            if len(state.evaluated_gaps) == len(state.raw_gaps):
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.7)
            
            confidence_score = sum(confidence_factors) / len(confidence_factors)
            
            # Generate summary
            summary_parts = []
            if state.raw_gaps:
                summary_parts.append(f"Se identificaron {len(state.raw_gaps)} gaps de aprendizaje.")
                
                # Add severity distribution
                severity_counts = {}
                for gap in state.raw_gaps:
                    severity = gap.severity.value
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                if severity_counts:
                    severity_info = ", ".join([f"{count} {sev}" for sev, count in severity_counts.items()])
                    summary_parts.append(f"Distribución por severidad: {severity_info}.")
            else:
                summary_parts.append("No se identificaron gaps específicos de aprendizaje.")
            
            summary = " ".join(summary_parts)
            
            # Generate basic recommendations (detailed recommendations handled by separate agent)
            general_recommendations = [
                "Revisar los conceptos teóricos relacionados con el ejercicio",
                "Consultar los tips proporcionados por el profesor",
                "Practicar con ejercicios similares de menor complejidad"
            ]
            
            # Create final result
            final_result = GapAnalysisResult(
                student_context=state.student_context,
                educational_context=state.educational_context,
                identified_gaps=state.raw_gaps,
                prioritized_gaps=[],  # Empty since we removed prioritization
                summary=summary,
                confidence_score=confidence_score,
                recommendations=general_recommendations
            )
            
            state.final_result = final_result
            logger.info("Generated complete gap analysis result")
            
            # Store gap analysis results in long-term memory
            await self._store_gap_analysis_memory(state)
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            state.error_message = f"Failed to generate final response: {str(e)}"
        
        return state
    
    async def _store_gap_analysis_memory(self, state: WorkflowState) -> None:
        """Store gap analysis results in long-term memory using Neo4j store."""
        if not self.memory_store:
            return
        
        try:
            # Create namespace for gap analysis memories
            user_id = getattr(state.student_context, 'user_id', 'anonymous')
            namespace = (user_id, "gap_analysis")
            
            # Store identified learning gaps
            gaps_memory = {
                "type": "learning_gaps",
                "gaps": [
                    {
                        "description": gap.description,
                        "severity": gap.severity.value,
                        "category": gap.category.value
                    }
                    for gap in state.raw_gaps
                ],
                "analysis_confidence": state.final_result.confidence_score,
                "practice_number": getattr(state.student_context, 'practice_number', None),
                "exercise_section": getattr(state.student_context, 'exercise_section', None),
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate unique key for this analysis
            analysis_key = f"gaps_{state.student_context.practice_number}_{state.student_context.exercise_section}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.memory_store.put(namespace, analysis_key, gaps_memory)
            
            # Store learning patterns
            patterns_memory = {
                "type": "learning_patterns",
                "common_gap_categories": [gap.category.value for gap in state.raw_gaps],
                "difficulty_indicators": {
                    "high_severity_gaps": len([g for g in state.raw_gaps if g.severity == GapSeverity.HIGH]),
                    "medium_severity_gaps": len([g for g in state.raw_gaps if g.severity == GapSeverity.MEDIUM]),
                    "low_severity_gaps": len([g for g in state.raw_gaps if g.severity == GapSeverity.LOW])
                },
                "practice_context": {
                    "practice_number": state.student_context.practice_number,
                    "exercise_section": state.student_context.exercise_section
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Check if we have existing patterns and merge
            existing_patterns = self.memory_store.get(namespace, "learning_patterns_summary")
            if existing_patterns:
                # Merge gap categories
                existing_patterns["common_gap_categories"].extend(patterns_memory["common_gap_categories"])
                # Keep only last 20 entries
                existing_patterns["common_gap_categories"] = existing_patterns["common_gap_categories"][-20:]
                existing_patterns["updated_at"] = datetime.now().isoformat()
                patterns_memory = existing_patterns
            
            self.memory_store.put(namespace, "learning_patterns_summary", patterns_memory)
            
            # Store recommendations effectiveness tracking
            if state.final_result.recommendations:
                recommendations_memory = {
                    "type": "recommendations",
                    "recommendations": state.final_result.recommendations,
                    "context": {
                        "practice_number": state.student_context.practice_number,
                        "exercise_section": state.student_context.exercise_section,
                        "gap_count": len(state.raw_gaps)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                rec_key = f"recommendations_{analysis_key}"
                self.memory_store.put(namespace, rec_key, recommendations_memory)
            
            logger.debug(f"Stored gap analysis memory for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to store gap analysis memory: {e}")
    
    async def _feedback_analysis(self, state: WorkflowState) -> WorkflowState:
        """
        Feedback analysis node.
        
        Analyzes the current gap analysis and determines if additional context
        or iteration is needed to improve the analysis quality.
        """
        try:
            logger.info(f"Performing feedback analysis - iteration {state.feedback_iterations + 1}")
            
            # Increment feedback counter
            state.feedback_iterations += 1
            
            # Check if we need theoretical context
            if state.educational_context.needs_theory_lookup and not state.educational_context.theory_background:
                logger.info("Retrieving additional theoretical context")
                
                # Extract key concepts from gaps for theory lookup
                key_concepts = []
                for gap in state.raw_gaps:
                    key_concepts.extend(gap.affected_concepts)
                
                if key_concepts:
                    # Use the most common concept
                    concept_counts = {}
                    for concept in key_concepts:
                        concept_counts[concept] = concept_counts.get(concept, 0) + 1
                    
                    main_concept = max(concept_counts.keys(), key=lambda k: concept_counts[k])
                    
                    # Get theoretical content
                    theory_content = get_theoretical_content_tool.invoke({
                        "topic_description": main_concept
                    })
                    
                    # Update educational context
                    state.educational_context.theory_background = theory_content
                    state.educational_context.needs_theory_lookup = False
                    
                    logger.info(f"Retrieved theoretical content for: {main_concept}")
            
            # Analyze gap quality and decide if another iteration is warranted
            if len(state.raw_gaps) == 0:
                state.feedback_reason = "No se encontraron gaps - se requiere análisis más profundo"
                state.needs_feedback = True
            elif len(state.raw_gaps) < 2:
                # Check if the single gap is comprehensive
                single_gap = state.raw_gaps[0]
                if len(single_gap.description) < 50:
                    state.feedback_reason = "Gap identificado parece superficial - se requiere análisis más detallado"
                    state.needs_feedback = True
                else:
                    state.needs_feedback = False
            else:
                # Check overall confidence based on evaluations
                if state.evaluated_gaps:
                    avg_confidence = sum(eval_gap.priority_score for eval_gap in state.evaluated_gaps) / len(state.evaluated_gaps)
                    if avg_confidence < 0.5:
                        state.feedback_reason = "Baja confianza en evaluación - refinando análisis"
                        state.needs_feedback = True
                    else:
                        state.needs_feedback = False
                else:
                    state.needs_feedback = False
            
            logger.info(f"Feedback analysis complete. Needs feedback: {state.needs_feedback}")
            
        except Exception as e:
            logger.error(f"Error in feedback analysis: {e}")
            state.error_message = f"Error en análisis de feedback: {str(e)}"
        
        return state
    
    async def _handle_error(self, state: WorkflowState) -> WorkflowState:
        """
        Error handling node.
        
        Processes errors and creates appropriate error responses.
        Focus on being concrete and specific about what content doesn't exist.
        """
        logger.error(f"Handling workflow error: {state.error_message}")
        
        # Create concise, specific error message
        error_message = state.error_message or "Error desconocido"
        
        # Be more specific about missing content
        if "no encontrada" in error_message or "no encontrado" in error_message:
            # Extract specific content that doesn't exist
            summary = error_message  # Use the specific error as-is
            recommendations = ["Verificar el número de práctica y ejercicio", "Consultar contenido disponible"]
        else:
            # Generic error
            summary = f"Error en el procesamiento: {error_message}"
            recommendations = ["Intentar nuevamente", "Verificar contexto proporcionado"]
        
        # Create minimal, concrete error result
        error_result = GapAnalysisResult(
            student_context=state.student_context or StudentContext(
                student_question="Error en procesamiento",
                subject_name="Unknown",
                practice_context="Error al procesar práctica",
                exercise_context="Error al procesar ejercicio"
            ),
            educational_context=EducationalContext(
                context_complete=False,
                needs_theory_lookup=False,
                theory_background="Error al recuperar contexto"
            ),
            identified_gaps=[],
            prioritized_gaps=[],  # Empty since prioritization was removed
            summary=summary,
            confidence_score=0.0,
            recommendations=recommendations
        )
        
        state.final_result = error_result
        return state
    
    async def run_analysis(self, student_context: StudentContext, thread_id: str = None) -> GapAnalysisResult:
        """
        Run the complete gap analysis workflow.
        
        Args:
            student_context: Context about the student's question
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Complete gap analysis result
        """
        try:
            # Initialize state
            initial_state = WorkflowState(student_context=student_context)
            
            # Configure for conversation continuity
            config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
            
            # Run workflow
            final_state = await self.graph.ainvoke(initial_state, config)
            
            return final_state["final_result"]
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Return error result
            return GapAnalysisResult(
                student_context=student_context,
                educational_context=EducationalContext(
                    context_complete=False,
                    needs_theory_lookup=False,
                    theory_background="Error al recuperar contexto"
                ),
                identified_gaps=[],
                prioritized_gaps=[],
                summary=f"Error crítico en el análisis: {str(e)}",
                confidence_score=0.0,
                recommendations=["Contactar soporte técnico", "Verificar configuración del sistema"]
            )