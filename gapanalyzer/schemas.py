"""
Data schemas for the GapAnalyzer agent.

This module defines the structured data models used throughout the gap analysis workflow,
including input contexts, analysis results, and final gap reports.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class GapSeverity(str, Enum):
    """Severity levels for identified learning gaps."""
    CRITICAL = "critical"      # Fundamental misunderstanding, blocks progress
    HIGH = "high"             # Significant gap affecting comprehension
    MEDIUM = "medium"         # Moderate gap, may cause confusion
    LOW = "low"               # Minor gap, easily addressable


class GapCategory(str, Enum):
    """Categories of learning gaps."""
    CONCEPTUAL = "conceptual"           # Misunderstanding of concepts
    PROCEDURAL = "procedural"           # Issues with procedures/methods
    THEORETICAL = "theoretical"         # Gap in theoretical understanding
    PRACTICAL = "practical"             # Difficulty applying knowledge
    PREREQUISITE = "prerequisite"       # Missing prerequisite knowledge
    COMMUNICATION = "communication"     # Issues expressing understanding


class ResponseQuality(str, Enum):
    """Quality assessment of student responses."""
    CORRECTA = "correcta"           # Correct response
    INCORRECTA = "incorrecta"       # Incorrect response
    PARCIAL = "parcial"             # Partially correct response
    NO_PROVISTA = "no_provista"     # No response provided/analyzed


class StudentContext(BaseModel):
    """Context information about the student and their question."""
    student_question: str = Field(description="The student's original question or concern")
    conversation_history: List[str] = Field(
        default=[],
        description="Previous messages in the conversation for context"
    )
    subject_name: str = Field(description="Name of the subject/course")
    practice_context: str = Field(description="Complete practice context including objectives and description")
    exercise_context: str = Field(description="Specific exercise statement and requirements")
    solution_context: Optional[str] = Field(
        default=None,
        description="Expected solution or answer to the exercise"
    )
    tips_context: Optional[str] = Field(
        default=None,
        description="Tips and hints provided by the teacher"
    )
    # Additional fields for workflow tracking
    practice_number: Optional[int] = Field(
        default=None,
        description="Practice number for tracking and memory storage"
    )
    exercise_section: Optional[str] = Field(
        default=None,
        description="Exercise section identifier (e.g., '1.d', '2.a')"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_question": "No entiendo por qué esta consulta SQL no devuelve los resultados esperados",
                "conversation_history": [
                    "Estoy trabajando en el ejercicio h de la práctica 2",
                    "Mi consulta devuelve filas duplicadas"
                ],
                "subject_name": "Bases de Datos Relacionales",
                "practice_context": "Práctica: 2 - Resolver estos ejercicios de álgebra relacional y SQL. Objetivos: Aplicar operaciones de álgebra relacional, escribir consultas SQL complejas con JOIN.",
                "exercise_context": "Ejercicio: h - Resuelva en álgebra relacional lo siguiente: Obtener el nombre de todos los empleados que trabajen en el departamento de 'Ventas' junto con el nombre de su supervisor.",
                "solution_context": "Solución esperada: SELECT e.nombre, s.nombre FROM empleados e JOIN empleados s ON e.supervisor_id = s.id JOIN departamentos d ON e.depto_id = d.id WHERE d.nombre = 'Ventas'",
                "tips_context": "Tips: Recuerde usar INNER JOIN para relacionar empleados con supervisores. Tenga en cuenta que un empleado puede ser supervisor de otros."
            }
        }


class ResponseQualityAssessment(BaseModel):
    """Assessment of student response quality."""
    quality: ResponseQuality = Field(
        default=ResponseQuality.NO_PROVISTA,
        description="Quality level of the student's response"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for the quality assessment"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in the quality assessment (0-1)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "quality": "parcial",
                "reasoning": "La respuesta muestra comprensión parcial del concepto pero tiene errores en la implementación",
                "confidence": 0.8
            }
        }


class EducationalContext(BaseModel):
    """Educational context derived from student input."""
    theory_background: Optional[str] = Field(
        default=None,
        description="Additional theoretical background if retrieved"
    )
    context_complete: bool = Field(
        default=True,
        description="Whether the provided context is sufficient for analysis"
    )
    needs_theory_lookup: bool = Field(
        default=False,
        description="Whether additional theoretical context is needed"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "theory_background": "El álgebra relacional define operaciones para manipular relaciones...",
                "context_complete": True,
                "needs_theory_lookup": False
            }
        }


class IdentifiedGap(BaseModel):
    """A single identified learning gap."""
    gap_id: str = Field(description="Unique identifier for this gap")
    title: str = Field(description="Brief title describing the gap")
    description: str = Field(description="Detailed description of the learning gap")
    category: GapCategory = Field(description="Category of the gap")
    severity: GapSeverity = Field(description="Severity level of the gap")
    evidence: str = Field(description="Evidence from student's question/response that indicates this gap")
    affected_concepts: List[str] = Field(description="Specific concepts affected by this gap")
    prerequisite_knowledge: List[str] = Field(
        default=[],
        description="Prerequisites the student might be missing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "gap_id": "gap_001",
                "title": "Confusión sobre JOINs en SQL",
                "description": "El estudiante no comprende cuándo y cómo usar diferentes tipos de JOIN",
                "category": "procedural",
                "severity": "high",
                "evidence": "La pregunta indica uso incorrecto de INNER JOIN cuando necesita LEFT JOIN",
                "affected_concepts": ["INNER JOIN", "LEFT JOIN", "relaciones entre tablas"],
                "prerequisite_knowledge": ["álgebra relacional básica", "modelo relacional"]
            }
        }


class GapEvaluation(BaseModel):
    """Evaluation of a gap's relevance and importance."""
    gap_id: str = Field(description="Reference to the gap being evaluated")
    pedagogical_relevance: float = Field(
        ge=0.0, le=1.0,
        description="How relevant this gap is to the current learning objectives (0-1)"
    )
    impact_on_learning: float = Field(
        ge=0.0, le=1.0,
        description="How much this gap impacts overall learning progress (0-1)"
    )
    addressability: float = Field(
        ge=0.0, le=1.0,
        description="How easily this gap can be addressed (0-1, higher = easier)"
    )
    priority_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall priority score calculated from other factors"
    )
    evaluation_reasoning: str = Field(description="Explanation of the evaluation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gap_id": "gap_001",
                "pedagogical_relevance": 0.9,
                "impact_on_learning": 0.8,
                "addressability": 0.7,
                "priority_score": 0.85,
                "evaluation_reasoning": "Este gap es fundamental para el ejercicio actual y afecta conceptos clave"
            }
        }


class PrioritizedGap(BaseModel):
    """A gap with its evaluation and priority ranking."""
    gap: IdentifiedGap = Field(description="The identified gap")
    evaluation: GapEvaluation = Field(description="Evaluation of the gap")
    rank: int = Field(description="Priority ranking (1 = highest priority)")
    recommended_actions: List[str] = Field(default=[], description="Specific actions to address this gap")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gap": "...",  # IdentifiedGap object
                "evaluation": "...",  # GapEvaluation object  
                "rank": 1,
                "recommended_actions": [
                    "Revisar conceptos de JOIN en el material teórico",
                    "Practicar con ejercicios simples de JOIN",
                    "Dibujar diagramas de las relaciones entre tablas"
                ]
            }
        }


class GapAnalysisResult(BaseModel):
    """Complete result of the gap analysis workflow."""
    student_context: StudentContext = Field(description="Original student context")
    educational_context: EducationalContext = Field(description="Retrieved educational context")
    identified_gaps: List[IdentifiedGap] = Field(description="All identified gaps")
    prioritized_gaps: List[PrioritizedGap] = Field(
        description="Gaps ordered by priority (highest first)"
    )
    summary: str = Field(description="Executive summary of the analysis")
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the analysis quality (0-1)"
    )
    recommendations: List[str] = Field(description="General recommendations for the student")
    response_quality: ResponseQualityAssessment = Field(
        default_factory=ResponseQualityAssessment,
        description="Assessment of the student's response quality"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Se identificaron 3 gaps principales relacionados con JOINs en SQL...",
                "confidence_score": 0.85,
                "recommendations": [
                    "Enfocar estudio en tipos de JOIN",
                    "Practicar con ejercicios incrementales",
                    "Consultar con el profesor sobre dudas específicas"
                ]
            }
        }


class WorkflowState(BaseModel):
    """State object for the LangGraph workflow."""
    # Input
    student_context: Optional[StudentContext] = None
    
    # Retrieved context
    educational_context: Optional[EducationalContext] = None
    
    # Analysis results
    raw_gaps: List[IdentifiedGap] = Field(default=[])
    evaluated_gaps: List[GapEvaluation] = Field(default=[])
    prioritized_gaps: List[PrioritizedGap] = Field(default=[])
    
    # Response quality assessment
    response_quality: ResponseQualityAssessment = Field(default_factory=ResponseQualityAssessment)
    
    # Final result
    final_result: Optional[GapAnalysisResult] = None
    
    # Workflow control
    error_message: Optional[str] = None
    should_retry: bool = False
    iteration_count: int = 0
    
    # Feedback loop control
    feedback_iterations: int = Field(default=0, description="Number of feedback iterations performed")
    max_feedback_iterations: int = Field(default=3, description="Maximum number of feedback iterations allowed")
    needs_feedback: bool = Field(default=False, description="Whether feedback analysis is needed")
    feedback_reason: Optional[str] = Field(default=None, description="Reason for requesting feedback")
    
    class Config:
        arbitrary_types_allowed = True


# Response format for the A2A framework
class GapAnalysisResponse(BaseModel):
    """Response format for the A2A framework."""
    status: Literal['input_required', 'completed', 'error'] = 'completed'
    message: str = Field(description="Human-readable summary of the analysis")
    gaps_found: int = Field(description="Number of gaps identified")
    top_priority_gaps: List[str] = Field(description="Titles of top 3 priority gaps")
    response_quality: ResponseQualityAssessment = Field(
        default_factory=ResponseQualityAssessment,
        description="Assessment of student response quality"
    )
    detailed_analysis: Optional[GapAnalysisResult] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "message": "Análisis completado. Se identificaron 3 gaps principales en su comprensión de JOINs.",
                "gaps_found": 3,
                "top_priority_gaps": [
                    "Confusión sobre tipos de JOIN",
                    "Falta de comprensión del producto cartesiano",
                    "Uso incorrecto de condiciones WHERE"
                ]
            }
        }