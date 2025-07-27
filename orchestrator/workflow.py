"""
LangGraph workflow for educational conversation orchestration.

This module implements the complete workflow for managing educational conversations,
including intent classification, agent routing, memory management, and response synthesis.
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
from tools.observability import create_observed_llm
from tools.kg_tools import get_kg_interface
from kg.persistence import create_neo4j_persistence
from .schemas import (
    WorkflowState,
    ConversationContext,
    ConversationMemory,
    IntentClassificationResult,
    AgentRoutingDecision,
    ResponseSynthesis,
    OrchestratorResponse,
    StudentIntent,
    GapAnalysisRequest
)


logger = logging.getLogger(__name__)


class OrchestratorWorkflow:
    """
    LangGraph workflow for educational conversation orchestration.
    
    The workflow consists of the following nodes:
    1. classify_intent: Determine student's intent from their message
    2. route_to_agent: Decide which agent or approach to use
    3. execute_agent_calls: Call specialized agents (GapAnalyzer, etc.)
    4. synthesize_response: Combine information into coherent response
    5. update_memory: Update conversation memory and context
    """
    
    def __init__(self, use_neo4j_persistence: bool = True):
        """Initialize the workflow with LLM and tools."""
        self.llm = create_observed_llm()
        
        # Initialize persistence layer
        if use_neo4j_persistence:
            try:
                self.checkpointer, self.memory_store = create_neo4j_persistence()
                logger.info("Using Neo4j persistence for agent memory")
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
        workflow.add_node("classify_intent", self._classify_intent)
        
        # Intent-specific processing nodes
        workflow.add_node("handle_theoretical_question", self._handle_theoretical_question)
        workflow.add_node("handle_practical_general", self._handle_practical_general)
        workflow.add_node("handle_practical_specific", self._handle_practical_specific)
        workflow.add_node("handle_clarification", self._handle_clarification)
        workflow.add_node("handle_exploration", self._handle_exploration)
        workflow.add_node("handle_evaluation", self._handle_evaluation)
        workflow.add_node("handle_social", self._handle_social)
        workflow.add_node("handle_off_topic", self._handle_off_topic)
        
        # Response processing nodes
        workflow.add_node("synthesize_response", self._synthesize_response)
        workflow.add_node("synthesize_practical_specific_response", self._synthesize_practical_specific_response)
        workflow.add_node("update_memory", self._update_memory)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add direct routing from intent classification to specific handlers
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "theoretical_question": "handle_theoretical_question",
                "practical_general": "handle_practical_general", 
                "practical_specific": "handle_practical_specific",
                "clarification": "handle_clarification",
                "exploration": "handle_exploration",
                "evaluation": "handle_evaluation",
                "greeting": "handle_social",
                "goodbye": "handle_social",
                "off_topic": "handle_off_topic",
                "error": "handle_error"
            }
        )
        
        # Intent handlers flow to appropriate synthesis (practical_specific gets specialized treatment)
        workflow.add_edge("handle_theoretical_question", "synthesize_response")
        workflow.add_edge("handle_practical_general", "synthesize_response")
        workflow.add_edge("handle_clarification", "synthesize_response")
        workflow.add_edge("handle_exploration", "synthesize_response")
        workflow.add_edge("handle_evaluation", "synthesize_response")
        workflow.add_edge("handle_social", "synthesize_response")
        workflow.add_edge("handle_off_topic", "synthesize_response")
        
        # Handle practical_specific has conditional routing for error handling
        workflow.add_conditional_edges(
            "handle_practical_specific",
            self._route_after_practical_specific,
            {
                "error": "handle_error",
                "synthesize": "synthesize_practical_specific_response"
            }
        )
        
        # Response synthesis flows to memory update and then end
        workflow.add_edge("synthesize_response", "update_memory")
        workflow.add_edge("synthesize_practical_specific_response", "update_memory")
        workflow.add_edge("update_memory", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _route_by_intent(self, state: WorkflowState) -> str:
        """Route to appropriate handler based on classified intent."""
        if not state.intent_result:
            logger.error("No intent classification result available")
            return "error"
        
        # Note: Don't check error_message here as it should be handled by intent classification
        # The error_message check was moved to intent classification phase
        
        intent = state.intent_result.predicted_intent
        logger.info(f"Routing to handler for intent: {intent}")
        
        # Map intent to handler
        intent_mapping = {
            StudentIntent.THEORETICAL_QUESTION: "theoretical_question",
            StudentIntent.PRACTICAL_GENERAL: "practical_general", 
            StudentIntent.PRACTICAL_SPECIFIC: "practical_specific",
            StudentIntent.CLARIFICATION: "clarification",
            StudentIntent.EXPLORATION: "exploration",
            StudentIntent.EVALUATION: "evaluation",
            StudentIntent.GREETING: "greeting",
            StudentIntent.GOODBYE: "goodbye",
            StudentIntent.OFF_TOPIC: "off_topic"
        }
        
        return intent_mapping.get(intent, "error")
    
    def _route_after_practical_specific(self, state: WorkflowState) -> str:
        """Route after handle_practical_specific based on whether errors occurred."""
        if state.error_message:
            logger.info(f"Routing to error handler after practical_specific due to: {state.error_message}")
            return "error"
        else:
            logger.info("Routing to synthesize_practical_specific_response")
            return "synthesize"
    
    async def _classify_intent(self, state: WorkflowState) -> WorkflowState:
        """
        Node 1: Classify the student's intent from their message.
        
        Analyzes the student's message in context to determine what type of
        assistance they need and how the conversation should proceed.
        """
        try:
            logger.info("Classifying student intent")
            
            # Clear any previous error state for new message processing
            state.error_message = None
            state.needs_clarification = False
            
            if not state.conversation_context:
                state.error_message = "No conversation context provided"
                return state
            
            ctx = state.conversation_context
            
            # Get recent conversation history for context
            recent_messages = ctx.memory.get_recent_history(max_turns=6)
            history_text = "\\n".join([
                f"{turn.role}: {turn.content}" for turn in recent_messages
            ])
            
            # Create intent classification prompt
            classification_prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres un experto en clasificación de intenciones educativas. Tu tarea es analizar el mensaje del estudiante y clasificar su intención principal.

CONTEXTO EDUCATIVO:
- Materia actual: {current_subject}
- Práctica actual: {current_practice}
- Temas discutidos: {topics_discussed}

HISTORIAL RECIENTE:
{conversation_history}

INTENCIONES POSIBLES:
- theoretical_question: Pregunta sobre conceptos, definiciones, teoría
- practical_general: Pregunta práctica general, no específica a ejercicios del KG
- practical_specific: Ayuda con ejercicio/práctica específica mapeada en el KG
- clarification: Pide aclaración sobre respuestas anteriores
- exploration: Quiere explorar temas relacionados, curiosidad
- evaluation: Pide autoevaluación, validación de conocimiento
- greeting: Saludos iniciales, inicio de conversación
- goodbye: Despedida, fin de conversación  
- off_topic: No relacionado con educación

INSTRUCCIONES:
1. Analiza el mensaje actual en el contexto de la conversación
2. Identifica la intención principal más probable
3. Para distinguir practical_general vs practical_specific:
   - practical_specific: El estudiante menciona explícitamente práctica/ejercicio/sección específica (ej: "práctica 2", "ejercicio 1.d", "sección 3") O el contexto permite mapear a ejercicio específico del KG
   - practical_general: Pregunta práctica sobre conceptos aplicados pero sin referencia específica a ejercicios del KG
4. Evalúa la confianza en tu clasificación (0-1)
5. Proporciona razonamiento claro
6. Sugiere acciones basadas en la intención
7. Determina si necesitas más contexto
                 
CONSIDERACIONES DEL LENGUAJE:
1. El alumno se expresa en español argentino.
2. En el contexto de prácticas específicas, el alumno suele usar los siguientes sinónimos para ejercicio: punto, ejercicio, problema, item.


Responde en formato JSON:
{{
  "predicted_intent": "intent_name",
  "confidence": 0.0-1.0,
  "reasoning": "Explicación clara del razonamiento",
  "requires_context": true/false,
  "suggested_actions": ["acción1", "acción2"]
}}

Sé preciso y considera el contexto educativo."""),
                ("human", """MENSAJE DEL ESTUDIANTE: {current_message}

Clasifica la intención de este mensaje.""")
            ])
            
            # Prepare context
            current_subject = ctx.memory.educational_context.current_subject or "No especificada"
            current_practice = ctx.memory.educational_context.current_practice or "Ninguna"
            topics_discussed = ", ".join(ctx.memory.educational_context.topics_discussed) or "Ninguno"
            
            formatted_prompt = classification_prompt.format_messages(
                current_subject=current_subject,
                current_practice=current_practice,
                topics_discussed=topics_discussed,
                conversation_history=history_text or "Sin historial previo",
                current_message=ctx.current_message
            )
            
            # Get LLM response
            response = await self.llm.ainvoke(formatted_prompt)
            
            # Parse JSON response
            try:
                response_text = response.content
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_content = response_text[json_start:json_end]
                
                intent_data = json.loads(json_content)
                
                # Create IntentClassificationResult
                intent_result = IntentClassificationResult(
                    predicted_intent=StudentIntent(intent_data.get("predicted_intent", "theoretical_question")),
                    confidence=float(intent_data.get("confidence", 0.5)),
                    reasoning=intent_data.get("reasoning", ""),
                    requires_context=bool(intent_data.get("requires_context", False)),
                    suggested_actions=intent_data.get("suggested_actions", [])
                )
                
                state.intent_result = intent_result
                logger.info(f"Classified intent: {intent_result.predicted_intent} (confidence: {intent_result.confidence:.2f})")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse intent classification JSON: {e}")
                # Fallback to default classification
                state.intent_result = IntentClassificationResult(
                    predicted_intent=StudentIntent.THEORETICAL_QUESTION,
                    confidence=0.3,
                    reasoning="Error en clasificación, usando intención por defecto",
                    requires_context=True,
                    suggested_actions=["Solicitar más información"]
                )
                
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            state.error_message = f"Intent classification failed: {str(e)}"
            # Ensure we have a fallback intent result for routing
            if not state.intent_result:
                state.intent_result = IntentClassificationResult(
                    predicted_intent=StudentIntent.THEORETICAL_QUESTION,
                    confidence=0.1,
                    reasoning="Error en clasificación, usando intención por defecto",
                    requires_context=True,
                    suggested_actions=["Reformular la pregunta"]
                )
        
        return state
    
    # Intent-specific handler nodes
    
    async def _handle_theoretical_question(self, state: WorkflowState) -> WorkflowState:
        """Handle theoretical questions using knowledge retrieval."""
        try:
            logger.info("Handling theoretical question")
            ctx = state.conversation_context
            
            # Call knowledge retrieval for theoretical content
            response = await self._call_knowledge_retrieval(ctx, {
                "retrieval_type": "theoretical",
                "include_examples": True
            })
            
            state.agent_responses["knowledge_retrieval"] = response
            logger.info("Theoretical question handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling theoretical question: {e}")
            state.error_message = f"Theoretical question handling failed: {str(e)}"
        
        return state
    
    async def _handle_practical_general(self, state: WorkflowState) -> WorkflowState:
        """Handle general practical questions using knowledge retrieval."""
        try:
            logger.info("Handling general practical question")
            ctx = state.conversation_context
            
            # Call knowledge retrieval with practical focus
            response = await self._call_knowledge_retrieval(ctx, {
                "retrieval_type": "practical",
                "include_examples": True,
                "focus_practical": True
            })
            
            state.agent_responses["knowledge_retrieval"] = response
            logger.info("General practical question handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling practical general question: {e}")
            state.error_message = f"Practical general question handling failed: {str(e)}"
        
        return state
    
    async def _handle_practical_specific(self, state: WorkflowState) -> WorkflowState:
        """Handle specific practice/exercise questions using GapAnalyzer."""
        try:
            logger.info("Handling specific practical question")
            ctx = state.conversation_context
            
            # Extract educational parameters from context and message
            educational_params = self._extract_educational_parameters(ctx)
            
            if not educational_params:
                # If we can't extract parameters, ask for clarification
                response = await self._request_educational_clarification(ctx)
                state.agent_responses["clarification"] = response
                logger.info("Requested clarification for educational parameters")
                return state
            
            # Create context from KG using extracted parameters
            try:
                student_context = await self._create_context_from_kg(
                    question=ctx.current_message,
                    subject_name=educational_params["subject_name"],
                    practice_number=educational_params["practice_number"],
                    section_number=educational_params["section_number"],
                    exercise_identifier=educational_params["exercise_identifier"],
                    conversation_history=ctx.memory.get_student_messages(max_messages=3)
                )
                
                # Call GapAnalyzer with the constructed context
                response = await self._call_gap_analyzer_with_context(student_context, ctx.session_id)
                state.agent_responses["gap_analyzer"] = response
                logger.info("Specific practical question handled successfully with KG context")
                
            except ValueError as e:
                # Handle case where practice/exercise not found in KG
                error_msg = str(e)
                logger.error(f"Educational content not found in KG: {error_msg}")
                
                # Set error state to route to handle_error for proper clarification
                state.error_message = f"CONTENT_NOT_FOUND: {error_msg}"
                state.needs_clarification = True
                logger.info("Set error state for missing educational content - routing to error handler")
            
        except Exception as e:
            logger.error(f"Error handling practical specific question: {e}")
            state.error_message = f"Practical specific question handling failed: {str(e)}"
        
        return state
    
    async def _handle_clarification(self, state: WorkflowState) -> WorkflowState:
        """Handle clarification requests using conversation context."""
        try:
            logger.info("Handling clarification request")
            ctx = state.conversation_context
            
            # Generate contextual clarification
            response = await self._generate_direct_response(ctx, {
                "use_conversation_history": True,
                "response_type": "explanatory"
            })
            
            state.agent_responses["direct_response"] = response
            logger.info("Clarification request handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling clarification: {e}")
            state.error_message = f"Clarification handling failed: {str(e)}"
        
        return state
    
    async def _handle_exploration(self, state: WorkflowState) -> WorkflowState:
        """Handle exploration questions using knowledge retrieval and direct response."""
        try:
            logger.info("Handling exploration question")
            ctx = state.conversation_context
            
            # Combine knowledge retrieval with exploratory guidance
            knowledge_response = await self._call_knowledge_retrieval(ctx, {
                "retrieval_type": "exploration",
                "include_related_topics": True
            })
            
            guidance_response = await self._generate_direct_response(ctx, {
                "use_conversation_history": True,
                "response_type": "exploratory"
            })
            
            state.agent_responses["knowledge_retrieval"] = knowledge_response
            state.agent_responses["direct_response"] = guidance_response
            logger.info("Exploration question handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling exploration: {e}")
            state.error_message = f"Exploration handling failed: {str(e)}"
        
        return state
    
    async def _handle_evaluation(self, state: WorkflowState) -> WorkflowState:
        """Handle evaluation/self-assessment requests."""
        try:
            logger.info("Handling evaluation request")
            ctx = state.conversation_context
            
            # Generate evaluation guidance
            response = await self._generate_direct_response(ctx, {
                "response_type": "evaluation",
                "include_assessment_guidance": True
            })
            
            state.agent_responses["direct_response"] = response
            logger.info("Evaluation request handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling evaluation: {e}")
            state.error_message = f"Evaluation handling failed: {str(e)}"
        
        return state
    
    async def _handle_social(self, state: WorkflowState) -> WorkflowState:
        """Handle social interactions (greetings, goodbyes)."""
        try:
            logger.info("Handling social interaction")
            ctx = state.conversation_context
            
            # Generate appropriate social response
            response = await self._generate_direct_response(ctx, {
                "response_type": "social"
            })
            
            state.agent_responses["direct_response"] = response
            logger.info("Social interaction handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling social interaction: {e}")
            state.error_message = f"Social interaction handling failed: {str(e)}"
        
        return state
    
    async def _handle_off_topic(self, state: WorkflowState) -> WorkflowState:
        """Handle off-topic messages with educational redirection."""
        try:
            logger.info("Handling off-topic message")
            ctx = state.conversation_context
            
            # Generate redirection to educational content
            response = await self._generate_clarification(ctx, {
                "redirect_to_education": True
            })
            
            state.agent_responses["clarification"] = response
            logger.info("Off-topic message handled successfully")
            
        except Exception as e:
            logger.error(f"Error handling off-topic message: {e}")
            state.error_message = f"Off-topic handling failed: {str(e)}"
        
        return state
    
    
    async def _synthesize_response(self, state: WorkflowState) -> WorkflowState:
        """
        Synthesize responses from intent-specific handlers into coherent educational response.
        
        Combines information from various intent handlers into a coherent,
        educational response with appropriate guidance and next steps.
        """
        try:
            logger.info("Synthesizing response")
            
            # Create synthesis prompt
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres un tutor educativo experto en síntesis de respuestas. Tu tarea es crear una respuesta educativa coherente y útil basada en:

1. El mensaje del estudiante
2. Su intención clasificada  
3. Las respuestas de handlers especializados
4. El contexto de la conversación

PRINCIPIOS DE SÍNTESIS:
- Prioriza la claridad y utilidad educativa
- Adapta el tono al nivel del estudiante
- Incluye orientación pedagógica cuando sea apropiado
- Sugiere pasos siguientes concretos
- Mantén el foco en los objetivos de aprendizaje
- Usa español argentino

ESTRUCTURA DE RESPUESTA:
1. Respuesta principal (directa al punto)
2. Información de apoyo (si es relevante)
3. Orientación educativa (siguiente paso, método de estudio)
4. Conexiones con otros temas (si aplica)

Genera una respuesta sintética que sea útil y educativamente valiosa."""),
                ("human", """MENSAJE DEL ESTUDIANTE: {student_message}

INTENCIÓN CLASIFICADA: {intent} (confianza: {confidence})

RESPUESTAS DE HANDLERS:
{handler_responses}

CONTEXTO EDUCATIVO:
- Materia: {subject}
- Práctica: {practice}
- Temas discutidos: {topics}

Sintetiza una respuesta educativa completa.""")
            ])
            
            # Prepare handler responses text
            handler_responses_text = []
            for handler, response in state.agent_responses.items():
                handler_responses_text.append(f"[{handler.upper()}]\\n{response}\\n")
            
            ctx = state.conversation_context
            formatted_prompt = synthesis_prompt.format_messages(
                student_message=ctx.current_message,
                intent=state.intent_result.predicted_intent.value,
                confidence=state.intent_result.confidence,
                handler_responses="\\n".join(handler_responses_text) or "Sin respuestas de handlers",
                subject=ctx.memory.educational_context.current_subject or "No especificada",
                practice=ctx.memory.educational_context.current_practice or "Ninguna",
                topics=", ".join(ctx.memory.educational_context.topics_discussed) or "Ninguno"
            )
            
            # Get synthesis response
            response = await self.llm.ainvoke(formatted_prompt)
            synthesis_content = response.content
            
            # Create synthesis result
            synthesis = ResponseSynthesis(
                primary_content=synthesis_content,
                supporting_information=[],  # Could extract from structured response
                next_steps=state.intent_result.suggested_actions,
                educational_guidance=f"Basado en tu {state.intent_result.predicted_intent.value}, te sugiero continuar explorando los conceptos relacionados.",
                confidence_level=min(state.intent_result.confidence + 0.1, 1.0)
            )
            
            state.response_synthesis = synthesis
            logger.info("Response synthesis completed")
            
        except Exception as e:
            logger.error(f"Error in response synthesis: {e}")
            state.error_message = f"Response synthesis failed: {str(e)}"
        
        return state
    
    async def _synthesize_practical_specific_response(self, state: WorkflowState) -> WorkflowState:
        """
        Specialized synthesis for practical_specific responses.
        
        Creates pedagogical guidance based on gap analysis results, focusing on:
        - Concrete next steps to unblock the student
        - Framework-specific guidance (e.g., álgebra relacional vs SQL)
        - Avoids giving direct answers to exercises
        - Prioritizes most critical gaps for immediate action
        """
        try:
            logger.info("Synthesizing practical-specific response with pedagogical focus")
            
            # Extract gap analysis results from handler response
            gap_analysis_response = state.agent_responses.get('gap_analyzer', '')
            
            # Create specialized synthesis prompt for practical guidance
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres un tutor pedagógico especializado en guiar estudiantes a través de ejercicios prácticos sin dar las respuestas directas, sino orientando al estudiante a partir del análisis de gaps a llegar a la respuesta sin dársela directamente. Específicamente trabajamos sobre prácticas (problemas/ejercicios).

TU MISIÓN:
- Analizar los gaps identificados en el análisis del ejercicio
- Proveer orientación pedagógica específica para destrabar al estudiante
- NUNCA dar la respuesta del ejercicio ni mostrar cómo debería verse
- Enfocar en el framework/paradigma específico de la práctica
- Sugerir pasos concretos y específicos para que el estudiante avance por sí mismo
                 
ESTILO DE COMUNICACION: Conciso, sos un profesor orientador, usá la variante Argentina del español, no supongas que el estudiante es siempre de género masculino. No hables del "gap" como algo que el alumno deba conocer, mostrale el "gap" sin decirle "tenés un gap", "este es el gap más crítico".

PRINCIPIOS PEDAGÓGICOS:
1. AUTODESCUBRIMIENTO: Guiar para que el estudiante descubra por sí mismo
2. FRAMEWORK ESPECÍFICO: Mantener la orientación en el marco conceptual de la práctica
3. PASOS CONCRETOS: Dar acciones específicas, no conceptos vagos

ESTRUCTURA DE RESPUESTA:
1. Reconocimiento empático del problema
2. Identificación del gap específico más crítico (a partir del análisis de gaps provisto)
3. Orientación metodológica concreta en el framework de la práctica
4. Pregunta reflexiva para guiar el autodescubrimiento
5. Sugerir siguiente paso específico a realizar

EJEMPLOS DE ORIENTACIÓN:
- "En álgebra relacional, empezá por definir exactamente qué conjuntos necesitás..."
- "Antes de escribir SQL, dibujá qué tablas participan y qué conexión querés lograr..."
- "Para este tipo de JOIN, preguntate: ¿qué registros quiero que queden afuera?"

EVITAR ABSOLUTAMENTE:
- Mostrar código SQL o expresiones de álgebra relacional completas
- Decir "la respuesta es..." o "deberías obtener..."
- Conceptos generales sin aplicación específica al ejercicio"""),
                ("human", """CONTEXTO DEL EJERCICIO:
Estudiante: {student_message}
Materia: {subject}
Práctica: {practice} 
Ejercicio: {exercise_context}

ANÁLISIS DE GAPS IDENTIFICADOS:
{gap_analysis}

CONTEXTO EDUCATIVO DE LA PRÁCTICA:
{practice_context}

Crea una respuesta pedagógica que guíe al estudiante a destrabar su situación específica en este ejercicio, enfocándote en el framework conceptual de la práctica y sin dar la respuesta directa.""")
            ])
            
            ctx = state.conversation_context
            
            # Extract exercise and practice context from handler responses or conversation context
            exercise_context = self._extract_exercise_context_from_state(state)
            practice_context = self._extract_practice_context_from_state(state)
            
            # If we have structured gap analysis results, extract them
            gap_summary = gap_analysis_response
            if not gap_summary:
                gap_summary = "No se pudo completar el análisis de gaps. Procederé con orientación general."
            
            formatted_prompt = synthesis_prompt.format_messages(
                student_message=ctx.current_message,
                subject=ctx.memory.educational_context.current_subject or "No especificada",
                practice=f"Práctica {ctx.memory.educational_context.current_practice}" if ctx.memory.educational_context.current_practice else "Práctica no identificada",
                exercise_context=exercise_context,
                gap_analysis=gap_summary,
                practice_context=practice_context
            )
            
            # Get specialized pedagogical response
            response = await self.llm.ainvoke(formatted_prompt)
            pedagogical_content = response.content
            
            # Create synthesis result with pedagogical focus
            synthesis = ResponseSynthesis(
                primary_content=pedagogical_content,
                supporting_information=[
                    "Recordá que el objetivo es que vos mismo llegues a la respuesta",
                    "Si necesitás repasar conceptos, revisá el material teórico de la práctica"
                ],
                next_steps=[
                    "Aplicá la orientación metodológica sugerida",
                    "Reflexioná sobre las preguntas planteadas",
                    "Intentá el ejercicio paso a paso",
                    "Si seguís trabado, probá explicar tu razonamiento en voz alta"
                ],
                educational_guidance="Esta orientación está diseñada para ayudarte a desarrollar autonomía en la resolución de problemas. El proceso de descubrimiento es tan importante como la respuesta final.",
                confidence_level=min(state.intent_result.confidence + 0.2, 1.0)  # Higher confidence for specialized synthesis
            )
            
            state.response_synthesis = synthesis
            logger.info("Practical-specific pedagogical synthesis completed")
            
        except Exception as e:
            logger.error(f"Error in practical-specific synthesis: {e}")
            # Fallback to general synthesis
            logger.info("Falling back to general synthesis due to error")
            return await self._synthesize_response(state)
        
        return state
    
    async def _update_memory(self, state: WorkflowState) -> WorkflowState:
        """
        Node 5: Update conversation memory and context.
        
        Updates the conversation memory with the new interaction and
        generates the final response for the student.
        """
        try:
            logger.info("Updating conversation memory")
            
            ctx = state.conversation_context
            
            # Add current student message to memory
            ctx.memory.add_turn(
                role="student",
                content=ctx.current_message,
                intent=state.intent_result.predicted_intent,
                confidence=state.intent_result.confidence,
                handler_used=state.intent_result.predicted_intent.value
            )
            
            # Add assistant response to memory
            if state.response_synthesis:
                ctx.memory.add_turn(
                    role="assistant",
                    content=state.response_synthesis.primary_content,
                    synthesis_confidence=state.response_synthesis.confidence_level
                )
            
            # Update educational context if relevant
            if state.intent_result.predicted_intent in [
                StudentIntent.THEORETICAL_QUESTION,
                StudentIntent.PRACTICAL_GENERAL,
                StudentIntent.PRACTICAL_SPECIFIC
            ]:
                # Extract topics from the conversation (simplified)
                message_lower = ctx.current_message.lower()
                if "sql" in message_lower or "join" in message_lower:
                    if "SQL" not in ctx.memory.educational_context.topics_discussed:
                        ctx.memory.educational_context.topics_discussed.append("SQL")
                
                if "práctica" in message_lower:
                    # Try to extract practice number (simplified)
                    import re
                    practice_match = re.search(r'práctica\\s+(\\d+)', message_lower)
                    if practice_match:
                        ctx.memory.educational_context.current_practice = int(practice_match.group(1))
            
            # Store long-term memories in Neo4j if available
            await self._store_long_term_memory(state, ctx)
            
            # Create final response
            final_response = OrchestratorResponse(
                status='success',
                message=state.response_synthesis.primary_content if state.response_synthesis else "Error en síntesis",
                educational_guidance=state.response_synthesis.educational_guidance if state.response_synthesis else None,
                intent_classification=state.intent_result,
                routing_decision=None,  # No longer using routing_decision
                response_synthesis=state.response_synthesis,
                conversation_context=ctx
            )
            
            state.final_response = final_response
            logger.info("Memory update and final response generation completed")
            
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            state.error_message = f"Memory update failed: {str(e)}"
        
        return state
    
    async def _store_long_term_memory(self, state: WorkflowState, ctx: ConversationContext) -> None:
        """Store important information in long-term memory using Neo4j store."""
        if not self.memory_store:
            return
        
        try:
            # Create namespace for this student/session
            user_id = ctx.user_id or "anonymous"
            namespace = (user_id, "educational_memory")
            
            # Store topics discussed
            topics_memory = {
                "type": "topics_discussed",
                "topics": ctx.memory.educational_context.topics_discussed,
                "updated_at": datetime.now().isoformat(),
                "session_id": ctx.session_id
            }
            self.memory_store.put(namespace, "topics_discussed", topics_memory)
            
            # Store practice progress
            if ctx.memory.educational_context.current_practice:
                practice_memory = {
                    "type": "practice_progress",
                    "current_practice": ctx.memory.educational_context.current_practice,
                    "subject": ctx.educational_subject or "general",
                    "updated_at": datetime.now().isoformat(),
                    "session_id": ctx.session_id
                }
                self.memory_store.put(namespace, "practice_progress", practice_memory)
            
            # Store learning patterns based on intent patterns
            intent_memory = {
                "type": "learning_pattern",
                "recent_intents": [state.intent_result.predicted_intent.value],
                "confidence_scores": [state.intent_result.confidence],
                "timestamp": datetime.now().isoformat(),
                "session_id": ctx.session_id
            }
            
            # Check if we have existing learning patterns and merge
            existing_patterns = self.memory_store.get(namespace, "learning_patterns")
            if existing_patterns:
                existing_patterns["recent_intents"].append(state.intent_result.predicted_intent.value)
                existing_patterns["confidence_scores"].append(state.intent_result.confidence)
                # Keep only last 10 intents
                existing_patterns["recent_intents"] = existing_patterns["recent_intents"][-10:]
                existing_patterns["confidence_scores"] = existing_patterns["confidence_scores"][-10:]
                existing_patterns["updated_at"] = datetime.now().isoformat()
                intent_memory = existing_patterns
            
            self.memory_store.put(namespace, "learning_patterns", intent_memory)
            
            logger.debug(f"Stored long-term memory for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to store long-term memory: {e}")
    
    async def _handle_error(self, state: WorkflowState) -> WorkflowState:
        """
        Error handling node.
        
        Processes errors and creates appropriate error responses.
        Special handling for content not found errors to provide helpful clarification.
        """
        logger.error(f"Handling workflow error: {state.error_message}")
        
        # Check if this is a content not found error
        if state.error_message and "CONTENT_NOT_FOUND:" in state.error_message:
            # Extract the original error message
            error_details = state.error_message.replace("CONTENT_NOT_FOUND: ", "")
            
            error_response = OrchestratorResponse(
                status='needs_clarification',
                message=error_details
            )
            
        else:
            # Handle general errors
            error_response = OrchestratorResponse(
                status='error',
                message=f"Disculpá, tuve un problema procesando tu mensaje: {state.error_message}. ¿Podrías intentar reformular tu pregunta?"
            )
        
        state.final_response = error_response
        return state
    
    
    def _extract_exercise_context_from_state(self, state: WorkflowState) -> str:
        """
        Extract exercise context information from state for specialized synthesis.
        
        Returns:
            String with exercise context information
        """
        try:
            ctx = state.conversation_context
            
            # Try to get context from gap analyzer response
            gap_response = state.agent_responses.get('gap_analyzer', '')
            if 'Ejercicio:' in gap_response:
                # Extract exercise info from gap analyzer response
                import re
                exercise_match = re.search(r'Ejercicio:\s*([^\n]+)', gap_response)
                if exercise_match:
                    return exercise_match.group(1).strip()
            
            # Fall back to extracting from conversation context
            practice_num = ctx.memory.educational_context.current_practice
            exercise_ref = ctx.memory.educational_context.current_exercise
            
            if practice_num and exercise_ref:
                return f"Práctica {practice_num}, Ejercicio {exercise_ref}"
            elif practice_num:
                return f"Ejercicio de la Práctica {practice_num}"
            else:
                return "Ejercicio específico mencionado en el mensaje"
                
        except Exception as e:
            logger.warning(f"Error extracting exercise context: {e}")
            return "Ejercicio práctico específico"
    
    def _extract_practice_context_from_state(self, state: WorkflowState) -> str:
        """
        Extract practice framework context for specialized synthesis.
        
        Returns:
            String with practice framework information
        """
        try:
            ctx = state.conversation_context
            subject = ctx.memory.educational_context.current_subject
            practice_num = ctx.memory.educational_context.current_practice
            
            # Try to get context from gap analyzer response
            gap_response = state.agent_responses.get('gap_analyzer', '')
            if 'Práctica:' in gap_response:
                # Extract practice info from gap analyzer response
                import re
                practice_match = re.search(r'Práctica:[^\n]*\n([^\n]+)', gap_response)
                if practice_match:
                    return practice_match.group(1).strip()
            
            # Generate framework context based on subject and practice
            if subject and 'base' in subject.lower() and 'datos' in subject.lower():
                if practice_num:
                    if practice_num <= 2:
                        return "Marco conceptual: Álgebra Relacional - operaciones entre conjuntos de tuplas, proyecciones, selecciones, productos cartesianos y joins"
                    elif practice_num <= 4:
                        return "Marco conceptual: SQL - lenguaje declarativo de consultas, estructura de SELECT, FROM, WHERE, JOIN"
                    else:
                        return "Marco conceptual: Bases de Datos Relacionales - diseño, normalización, integridad referencial"
                else:
                    return "Marco conceptual: Bases de Datos Relacionales - modelo relacional, álgebra relacional, SQL"
            
            # Generic fallback
            return f"Marco conceptual de {subject or 'la materia'}" + (f" - Práctica {practice_num}" if practice_num else "")
            
        except Exception as e:
            logger.warning(f"Error extracting practice context: {e}")
            return "Marco conceptual de la práctica actual"
    
    # Helper methods for educational parameter extraction and context building
    
    def _extract_educational_parameters(self, ctx: ConversationContext) -> Optional[Dict[str, Any]]:
        """
        Extract educational parameters from conversation context and current message.
        
        Returns:
            Dict with subject_name, practice_number, section_number, exercise_identifier
            or None if parameters cannot be extracted
        """
        try:
            import re
            
            # Get subject from context (should already be available)
            subject_name = ctx.memory.educational_context.current_subject or "Bases de Datos Relacionales"
            
            # Get practice number from context or extract from message
            practice_number = ctx.memory.educational_context.current_practice
            section_number = None
            exercise_identifier = None
            
            message_lower = ctx.current_message.lower()
            
            # Try to extract practice number from message if not in context
            if not practice_number:
                practice_match = re.search(r'práctica\s+(\d+)', message_lower)
                if practice_match:
                    practice_number = int(practice_match.group(1))
            
            # Extract exercise code (e.g., "1.d", "2.a", "ejercicio 1.d", "problema k", "punto k", "ítem j")
            exercise_patterns = [
                r'ejercicio\s+(\d+)\.([a-z])',  # "ejercicio 1.d"
                r'(\d+)\.([a-z])',              # "1.d"
                r'sección\s+(\d+).*ejercicio\s+([a-z])',  # "sección 1 ejercicio d"
                r'problema\s+([a-z])\s+de\s+la\s+práctica\s+(\d+)',  # "problema k de la práctica 1"
                r'punto\s+([a-z])\s+de\s+la\s+práctica\s+(\d+)',     # "punto k de la práctica 4"
                r'ítem\s+([a-z])\s+de\s+la\s+práctica\s+(\d+)',      # "ítem j de la práctica 8"
                r'item\s+([a-z])\s+de\s+la\s+práctica\s+(\d+)',      # "item o de la práctica 3"
                r'el\s+problema\s+([a-z])',     # "el problema k" (uses current practice)
                r'problema\s+([a-z])',          # "problema k" (uses current practice)
                r'el\s+punto\s+([a-z])',        # "el punto k" (uses current practice)
                r'punto\s+([a-z])',             # "punto k" (uses current practice)
                r'el\s+ítem\s+([a-z])',         # "el ítem j" (uses current practice)
                r'ítem\s+([a-z])',              # "ítem j" (uses current practice)
                r'el\s+item\s+([a-z])',         # "el item o" (uses current practice)
                r'item\s+([a-z])',              # "item o" (uses current practice)
            ]
            
            for i, pattern in enumerate(exercise_patterns):
                match = re.search(pattern, message_lower)
                if match:
                    if i == 3:  # "problema k de la práctica 1" - different group order
                        exercise_identifier = match.group(1)
                        practice_number = int(match.group(2))
                        section_number = "1"  # Default to section 1 for "problema" references
                    elif i == 4:  # "punto k de la práctica 4" - different group order
                        exercise_identifier = match.group(1)
                        practice_number = int(match.group(2))
                        section_number = "1"  # Default to section 1 for "punto" references
                    elif i == 5:  # "ítem j de la práctica 8" - different group order
                        exercise_identifier = match.group(1)
                        practice_number = int(match.group(2))
                        section_number = "1"  # Default to section 1 for "ítem" references
                    elif i == 6:  # "item o de la práctica 3" - different group order
                        exercise_identifier = match.group(1)
                        practice_number = int(match.group(2))
                        section_number = "1"  # Default to section 1 for "item" references
                    elif i in [7, 8, 9, 10, 11, 12, 13]:  # Single letter patterns with current practice
                        exercise_identifier = match.group(1)
                        section_number = "1"  # Default to section 1 for single letter references
                    else:  # Standard patterns: section first, exercise second
                        section_number = match.group(1)
                        exercise_identifier = match.group(2)
                    break
            
            # If we have enough information, return parameters
            if practice_number and section_number and exercise_identifier:
                return {
                    "subject_name": subject_name,
                    "practice_number": practice_number,
                    "section_number": section_number,
                    "exercise_identifier": exercise_identifier
                }
            
            # Try alternative patterns: just practice and exercise without explicit section
            if practice_number:
                # Try "ejercicio k" pattern
                exercise_match = re.search(r'ejercicio\s+([a-z])', message_lower)
                if exercise_match:
                    # Assume section 1 if not specified
                    return {
                        "subject_name": subject_name,
                        "practice_number": practice_number,
                        "section_number": "1",
                        "exercise_identifier": exercise_match.group(1)
                    }
                
                # Try "problema k" pattern (if not already matched above)
                problema_match = re.search(r'problema\s+([a-z])', message_lower)
                if problema_match:
                    # Assume section 1 if not specified
                    return {
                        "subject_name": subject_name,
                        "practice_number": practice_number,
                        "section_number": "1",
                        "exercise_identifier": problema_match.group(1)
                    }
                
                # Try "punto k" pattern (if not already matched above)
                punto_match = re.search(r'punto\s+([a-z])', message_lower)
                if punto_match:
                    # Assume section 1 if not specified
                    return {
                        "subject_name": subject_name,
                        "practice_number": practice_number,
                        "section_number": "1",
                        "exercise_identifier": punto_match.group(1)
                    }
                
                # Try "ítem j" pattern (if not already matched above)
                item_match = re.search(r'ítem\s+([a-z])', message_lower)
                if item_match:
                    # Assume section 1 if not specified
                    return {
                        "subject_name": subject_name,
                        "practice_number": practice_number,
                        "section_number": "1",
                        "exercise_identifier": item_match.group(1)
                    }
                
                # Try "item o" pattern (if not already matched above)
                item_plain_match = re.search(r'item\s+([a-z])', message_lower)
                if item_plain_match:
                    # Assume section 1 if not specified
                    return {
                        "subject_name": subject_name,
                        "practice_number": practice_number,
                        "section_number": "1",
                        "exercise_identifier": item_plain_match.group(1)
                    }
            
            logger.warning(f"Could not extract educational parameters from message: {ctx.current_message}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting educational parameters: {e}")
            return None
    
    async def _create_context_from_kg(
        self, 
        question: str, 
        subject_name: str,
        practice_number: int, 
        section_number: str, 
        exercise_identifier: str,
        conversation_history: List[str]
    ) -> 'StudentContext':
        """
        Create a StudentContext using knowledge graph data.
        
        Args:
            question: Student's question
            subject_name: Subject name
            practice_number: Practice number
            section_number: Section number (string)
            exercise_identifier: Exercise identifier (string)
            conversation_history: Recent conversation history
            
        Returns:
            StudentContext built from knowledge graph data
            
        Raises:
            ValueError: If practice/exercise not found in KG
        """
        from gapanalyzer.schemas import StudentContext
        
        try:
            # Initialize KG interface
            kg_interface = get_kg_interface()
            
            # Get practice details
            practice_details = kg_interface.get_practice_details(practice_number)
            if not practice_details:
                raise ValueError(f"Práctica {practice_number} no encontrada en el grafo de conocimiento")
            
            # Get exercise details
            exercise_details = kg_interface.get_exercise_details(practice_number, section_number, exercise_identifier)
            if not exercise_details:
                raise ValueError(f"Ejercicio {practice_number}.{section_number}.{exercise_identifier} no encontrado en el grafo de conocimiento")
            
            # Get tips for the specific practice, section, and exercise
            practice_tips = kg_interface.get_practice_tips(practice_number, section_number, exercise_identifier)
            
            # Build practice context
            practice_context_parts = []
            practice_context_parts.append(f"Práctica: {practice_details['number']} - {practice_details['name']}")
            if practice_details["description"]:
                practice_context_parts.append(f"Descripción: {practice_details['description']}")
            if practice_details["objectives"]:
                practice_context_parts.append(f"Objetivos: {practice_details['objectives']}")
            if practice_details["topics"]:
                practice_context_parts.append(f"Temas cubiertos: {', '.join(practice_details['topics'])}")
            
            practice_context = "\n\n".join(practice_context_parts)
            
            # Build exercise context
            exercise_context_parts = []
            exercise_context_parts.append(f"Ejercicio: {exercise_details['section_number']}.{exercise_details['exercise_number']}")
            exercise_context_parts.append(f"Sección: {exercise_details['section_statement']}")
            exercise_context_parts.append(f"Enunciado: {exercise_details['exercise_statement']}")
            
            exercise_context = "\n\n".join(exercise_context_parts)
            
            # Build solution context from exercise answers
            solution_context = ""
            if exercise_details["answers"]:
                solution_context = f"Soluciones esperadas:\n" + "\n".join([f"- {answer}" for answer in exercise_details["answers"]])
            else:
                solution_context = "No se encontraron soluciones en el grafo de conocimiento"
            
            # Build tips context
            tips_context_parts = []
            if practice_tips:
                # Group tips by level
                practice_level_tips = [tip for tip in practice_tips if tip["level"] == "practice"]
                section_level_tips = [tip for tip in practice_tips if tip["level"] == "section" and tip["section_number"] == section_number]
                exercise_level_tips = [tip for tip in practice_tips if tip["level"] == "exercise" and 
                                     tip["section_number"] == section_number and str(tip["exercise_number"]) == exercise_identifier]
                
                if practice_level_tips:
                    tips_context_parts.append("Tips nivel práctica:")
                    for tip in practice_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
                
                if section_level_tips:
                    tips_context_parts.append(f"\nTips nivel sección {section_number}:")
                    for tip in section_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
                
                if exercise_level_tips:
                    tips_context_parts.append(f"\nTips nivel ejercicio {section_number}.{exercise_identifier}:")
                    for tip in exercise_level_tips:
                        tips_context_parts.append(f"- {tip['tip_text']}")
            
            tips_context = "\n".join(tips_context_parts) if tips_context_parts else "No se encontraron tips específicos para este ejercicio"
            
            logger.info(f"Successfully built context from KG for practice {practice_number}, exercise {section_number}.{exercise_identifier}")
            
            return StudentContext(
                student_question=question,
                conversation_history=conversation_history,
                subject_name=subject_name,
                practice_context=practice_context,
                exercise_context=exercise_context,
                solution_context=solution_context,
                tips_context=tips_context
            )
            
        except Exception as e:
            logger.error(f"Failed to create context from KG: {e}")
            raise ValueError(str(e))
    
    async def _call_gap_analyzer_with_context(self, student_context: 'StudentContext', session_id: str) -> str:
        """Call GapAnalyzer with a fully constructed StudentContext."""
        try:
            from gapanalyzer.agent import GapAnalyzerAgent
            
            logger.info("Calling GapAnalyzer with constructed context from KG")
            
            # Create GapAnalyzer instance
            gap_analyzer = GapAnalyzerAgent()
            
            # Run gap analysis with the constructed context
            result = await gap_analyzer.workflow.run_analysis(student_context, session_id)
            
            # Format result for orchestrator
            if result.identified_gaps:
                gap_summary = f"Se identificaron {len(result.identified_gaps)} gaps de aprendizaje:"
                for i, gap in enumerate(result.identified_gaps[:3], 1):  # Top 3 gaps
                    gap_summary += f"\n{i}. {gap.title}: {gap.description}"
                    gap_summary += f" (Severidad: {gap.severity.value})"
                
                gap_summary += f"\n\nConfianza del análisis: {result.confidence_score:.1%}"
                gap_summary += f"\nResumen: {result.summary}"
                
                return gap_summary
            else:
                return "El análisis no identificó gaps significativos en la comprensión del ejercicio consultado."
                
        except Exception as e:
            logger.error(f"Error calling GapAnalyzer with context: {e}")
            return f"Error al analizar gaps con contexto específico: {str(e)}. El sistema puede continuar con otras formas de asistencia."
    
    async def _request_educational_clarification(self, ctx: ConversationContext) -> str:
        """Request clarification for missing educational parameters."""
        try:
            clarification_prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres un tutor que ayuda a los estudiantes a especificar mejor sus consultas sobre ejercicios prácticos.

El estudiante ha hecho una pregunta sobre un ejercicio específico, pero necesitás más información para poder ayudarlo efectivamente.

Pedile que especifique:
- Número de práctica
- Número de sección 
- Identificador del ejercicio (letra o número)

Sé amable y explicá por qué necesitás esta información."""),
                ("human", """El estudiante preguntó: "{student_message}"

Pedile que proporcione los detalles específicos del ejercicio para poder ayudarlo mejor.""")
            ])
            
            formatted_prompt = clarification_prompt.format_messages(
                student_message=ctx.current_message
            )
            
            response = await self.llm.ainvoke(formatted_prompt)
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating educational clarification: {e}")
            return "Para ayudarte mejor con tu ejercicio específico, necesito que me indiques: ¿de qué práctica es? ¿qué sección? ¿y cuál es el número o letra del ejercicio? Por ejemplo: 'práctica 2, sección 1, ejercicio d'."
    
    async def _handle_missing_educational_content(self, ctx: ConversationContext, error_message: str) -> str:
        """Handle cases where educational content is not found in KG."""
        try:
            feedback_prompt = ChatPromptTemplate.from_messages([
                ("system", """Eres un tutor que ayuda cuando no se encuentra el contenido educativo solicitado.

El estudiante ha preguntado sobre un ejercicio específico, pero no se encuentra en el sistema.

INFORMACIÓN DEL ERROR: {error_message}

Debés:
1. Explicar amablemente que no se encontró el ejercicio específico
2. Sugerir que verifique los datos (práctica, sección, ejercicio)
3. Ofrecer ayuda alternativa (conceptos teóricos relacionados)
4. Pedirle que reformule la consulta con información correcta

Sé empático y constructivo."""),
                ("human", """El estudiante preguntó: "{student_message}"

Error encontrado: {error_message}

Genera una respuesta de ayuda y feedback.""")
            ])
            
            formatted_prompt = feedback_prompt.format_messages(
                student_message=ctx.current_message,
                error_message=error_message
            )
            
            response = await self.llm.ainvoke(formatted_prompt)
            return response.content
            
        except Exception as e:
            logger.error(f"Error handling missing educational content: {e}")
            return f"No encontré el ejercicio que mencionás ({error_message}). ¿Podrías verificar el número de práctica, sección y ejercicio? Mientras tanto, puedo ayudarte con conceptos teóricos relacionados."

    # Helper methods for agent calls
    
    async def _call_gap_analyzer(self, ctx: ConversationContext, params: Dict[str, Any]) -> str:
        """Call the GapAnalyzer agent."""
        try:
            from gapanalyzer.agent import GapAnalyzerAgent
            from gapanalyzer.schemas import StudentContext
            
            logger.info("Calling GapAnalyzer for gap analysis")
            
            # Create GapAnalyzer instance
            gap_analyzer = GapAnalyzerAgent()
            
            # Extract practice and exercise info from conversation context
            practice_number = ctx.memory.educational_context.current_practice
            exercise_code = None  # Could be extracted from message or context
            
            # Build student context for GapAnalyzer
            student_context = StudentContext(
                student_question=ctx.current_message,
                conversation_history=ctx.memory.get_student_messages(max_messages=3),
                subject_name=ctx.memory.educational_context.current_subject or "Bases de Datos Relacionales",
                practice_context=self._build_practice_context(ctx),
                exercise_context=self._build_exercise_context(ctx),
                solution_context="Consultar material de práctica correspondiente",
                tips_context="Revisar conceptos teóricos relevantes"
            )
            
            # Run gap analysis
            result = await gap_analyzer.workflow.run_analysis(student_context, ctx.session_id)
            
            # Format result for orchestrator
            if result.identified_gaps:
                gap_summary = f"Se identificaron {len(result.identified_gaps)} gaps de aprendizaje:"
                for i, gap in enumerate(result.identified_gaps[:3], 1):  # Top 3 gaps
                    gap_summary += f"\n{i}. {gap.title}: {gap.description}"
                    gap_summary += f" (Severidad: {gap.severity.value})"
                
                gap_summary += f"\n\nConfianza del análisis: {result.confidence_score:.1%}"
                gap_summary += f"\nResumen: {result.summary}"
                
                return gap_summary
            else:
                return "El análisis no identificó gaps significativos en la comprensión del tema consultado."
                
        except Exception as e:
            logger.error(f"Error calling GapAnalyzer: {e}")
            return f"Error al analizar gaps: {str(e)}. El sistema puede continuar con otras formas de asistencia."
    
    async def _call_knowledge_retrieval(self, ctx: ConversationContext, params: Dict[str, Any]) -> str:
        """Call knowledge retrieval from KG."""
        try:
            from tools import get_kg_tools
            # Use KG tools for retrieval
            kg_tools = get_kg_tools()
            search_tool = next((tool for tool in kg_tools if "search" in tool.name), None)
            
            if search_tool:
                result = search_tool.invoke({"query_text": ctx.current_message, "limit": 5})
                return f"Información recuperada del grafo de conocimiento:\\n{result}"
            else:
                return "Información teórica sobre el tema solicitado (herramientas de KG no disponibles)"
                
        except Exception as e:
            logger.error(f"Error in knowledge retrieval: {e}")
            return f"Error al recuperar información: {str(e)}"
    
    async def _generate_direct_response(self, ctx: ConversationContext, params: Dict[str, Any]) -> str:
        """Generate direct response using LLM."""
        try:
            response_type = params.get("response_type", "explanatory")
            
            if response_type == "social":
                return "¡Hola! Estoy acá para ayudarte con tus estudios. ¿En qué puedo asistirte hoy?"
            else:
                # Generate contextual response
                return f"Respuesta contextual para: {ctx.current_message}"
                
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            return f"Error generando respuesta: {str(e)}"
    
    async def _generate_clarification(self, ctx: ConversationContext, params: Dict[str, Any]) -> str:
        """Generate clarification response."""
        try:
            if params.get("redirect_to_education"):
                return "Entiendo tu mensaje, pero estoy acá para ayudarte con temas educativos. ¿Hay algún concepto de tus materias sobre el que tengas dudas?"
            else:
                return f"Para clarificar mejor tu consulta: {ctx.current_message}, ¿podrías proporcionar más detalles?"
        except Exception as e:
            logger.error(f"Error generating clarification: {e}")
            return f"Error generando clarificación: {str(e)}"
    
    def _build_practice_context(self, ctx: ConversationContext) -> str:
        """Build practice context from conversation memory."""
        try:
            current_practice = ctx.memory.educational_context.current_practice
            current_subject = ctx.memory.educational_context.current_subject
            
            if current_practice:
                return f"Práctica: {current_practice} - {current_subject or 'Materia no especificada'}. Objetivos: Aplicar conceptos fundamentales."
            else:
                return f"Práctica: {current_subject or 'Bases de Datos Relacionales'}. Objetivo: Aplicar conceptos fundamentales de la materia."
        except Exception as e:
            logger.error(f"Error building practice context: {e}")
            return "Práctica: Ejercicios de aplicación de conceptos fundamentales"
    
    def _build_exercise_context(self, ctx: ConversationContext) -> str:
        """Build exercise context from conversation memory and current message."""
        try:
            # Try to extract exercise information from the message
            message_lower = ctx.current_message.lower()
            
            if "ejercicio" in message_lower:
                return f"Ejercicio: {ctx.current_message}"
            elif any(word in message_lower for word in ["consulta", "query", "sql", "join"]):
                return f"Ejercicio: Problema relacionado con consultas y operaciones de base de datos. Consulta: {ctx.current_message}"
            else:
                return f"Ejercicio: Consulta o problema educativo. Pregunta del estudiante: {ctx.current_message}"
        except Exception as e:
            logger.error(f"Error building exercise context: {e}")
            return f"Ejercicio: {ctx.current_message}"
    
    async def run_conversation(self, conversation_context: ConversationContext, thread_id: str = None) -> OrchestratorResponse:
        """
        Run the complete orchestration workflow.
        
        Args:
            conversation_context: Context about the conversation
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Complete orchestrator response
        """
        try:
            # Initialize state
            initial_state = WorkflowState(conversation_context=conversation_context)
            
            # Configure for conversation continuity
            config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
            
            # Run workflow
            final_state = await self.graph.ainvoke(initial_state, config)
            
            return final_state["final_response"]
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Workflow execution failed: {e}")
            logger.error(f"Full error traceback: {error_details}")
            
            # Return error response with more details for debugging
            error_message = str(e) if str(e) else "Error desconocido en el workflow"
            return OrchestratorResponse(
                status='error',
                message=f"Error crítico en el procesamiento: {error_message}. Por favor, contactá soporte técnico.",
                educational_guidance="Mientras tanto, podés consultar el material de estudio disponible."
            )