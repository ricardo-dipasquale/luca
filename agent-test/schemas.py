"""
JSON Schemas para el sistema de testing de agentes LUCA.

Define la estructura de datos para suites de pruebas, resultados y métricas.
"""

from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class DifficultyLevel(str, Enum):
    """Niveles de dificultad para preguntas."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class AgentType(str, Enum):
    """Tipos de agentes disponibles."""
    ORCHESTRATOR = "orchestrator"
    GAPANALYZER = "gapanalyzer"
    BOTH = "both"

class TestQuestion(BaseModel):
    """Schema para una pregunta individual en una suite."""
    
    id: str = Field(description="ID único de la pregunta")
    question: str = Field(description="Texto de la pregunta")
    expected_answer: str = Field(description="Respuesta esperada o criterios de evaluación")
    context: Optional[str] = Field(None, description="Contexto adicional para la pregunta")
    subject: Optional[str] = Field(None, description="Materia educativa específica")
    difficulty: DifficultyLevel = Field(DifficultyLevel.MEDIUM, description="Nivel de dificultad")
    
    # Métricas específicas a evaluar
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas específicas a recolectar para esta pregunta"
    )
    
    # Para GapAnalyzer
    practice_id: Optional[int] = Field(None, description="ID de práctica para GapAnalyzer")
    exercise_section: Optional[str] = Field(None, description="Sección de ejercicio específica")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags para categorización")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class TestSuite(BaseModel):
    """Schema para una suite completa de pruebas."""
    
    name: str = Field(description="Nombre único de la suite")
    description: str = Field("", description="Descripción de la suite")
    agent_type: AgentType = Field(description="Tipo de agente a testear")
    
    # Configuración de la suite
    version: str = Field("1.0", description="Versión de la suite")
    author: str = Field("", description="Autor de la suite")
    
    # Preguntas
    questions: List[TestQuestion] = Field(description="Lista de preguntas de prueba")
    
    # Configuración de ejecución
    default_iterations: int = Field(1, description="Número default de iteraciones")
    timeout_seconds: int = Field(120, description="Timeout por pregunta en segundos")
    
    # Configuración de métricas globales
    global_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas a recolectar para todas las preguntas"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_question_count(self) -> int:
        """Obtener número de preguntas en la suite."""
        return len(self.questions)
    
    def get_subjects(self) -> List[str]:
        """Obtener lista de materias únicas en la suite."""
        subjects = {q.subject for q in self.questions if q.subject}
        return list(subjects)

class ExecutionResult(BaseModel):
    """Resultado de ejecutar una pregunta individual."""
    
    question_id: str = Field(description="ID de la pregunta ejecutada")
    question_text: str = Field(description="Texto de la pregunta")
    
    # Resultado de la ejecución
    success: bool = Field(description="Si la ejecución fue exitosa")
    agent_response: str = Field("", description="Respuesta del agente")
    error: Optional[str] = Field(None, description="Error si la ejecución falló")
    
    # Timing y performance
    execution_time: float = Field(description="Tiempo de ejecución en segundos")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Métricas recolectadas
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas recolectadas durante la ejecución"
    )
    
    # Información del agente
    agent_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata adicional del agente (schema results, etc.)"
    )
    
    # Traceability
    session_id: str = Field(description="ID de sesión usado")
    langfuse_trace_id: Optional[str] = Field(None, description="ID de trace en Langfuse")
    
    # Educational context (from original question)
    subject: Optional[str] = Field(None, description="Materia educativa")
    difficulty: Optional[str] = Field(None, description="Nivel de dificultad")
    practice_id: Optional[int] = Field(None, description="ID de práctica")
    exercise_section: Optional[str] = Field(None, description="Sección de ejercicio")
    tags: List[str] = Field(default_factory=list, description="Tags de la pregunta")

class TestRun(BaseModel):
    """Resultado completo de ejecutar una suite."""
    
    run_id: str = Field(description="ID único de la ejecución")
    suite_name: str = Field(description="Nombre de la suite ejecutada")
    agent_type: AgentType = Field(description="Tipo de agente usado")
    
    # Configuración de la ejecución
    iterations: int = Field(description="Número de iteraciones ejecutadas")
    session_id: str = Field(description="ID de sesión usado")
    
    # Timing
    start_time: datetime = Field(description="Inicio de la ejecución")
    end_time: datetime = Field(description="Final de la ejecución")
    total_time: float = Field(description="Tiempo total en segundos")
    
    # Resultados
    results: List[ExecutionResult] = Field(description="Resultados por pregunta")
    total_questions: int = Field(description="Total de preguntas procesadas")
    successful_questions: int = Field(description="Preguntas ejecutadas exitosamente")
    
    # Métricas agregadas
    summary_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Métricas agregadas de toda la ejecución"
    )
    
    # Langfuse integration
    langfuse_dataset_id: Optional[str] = Field(None, description="ID del dataset en Langfuse")
    langfuse_run_id: Optional[str] = Field(None, description="ID del run en Langfuse")
    
    def get_success_rate(self) -> float:
        """Calcular tasa de éxito."""
        if self.total_questions == 0:
            return 0.0
        return self.successful_questions / self.total_questions
    
    def get_average_execution_time(self) -> float:
        """Calcular tiempo promedio por pregunta."""
        if not self.results:
            return 0.0
        return sum(r.execution_time for r in self.results) / len(self.results)

# Schemas específicos para métricas de agentes

class OrchestratorMetrics(BaseModel):
    """Métricas específicas del Orchestrator Agent."""
    
    # Intent classification
    detected_intent: Optional[str] = Field(None, description="Intent detectado")
    intent_confidence: Optional[float] = Field(None, description="Confianza del intent")
    
    # Routing decisions
    routed_to_gapanalyzer: bool = Field(False, description="Si se enrutó a GapAnalyzer")
    routing_reason: Optional[str] = Field(None, description="Razón del routing")
    
    # Knowledge graph usage
    kg_queries_executed: int = Field(0, description="Queries ejecutadas al KG")
    kg_results_found: int = Field(0, description="Resultados encontrados en KG")
    
    # Response generation
    response_length: int = Field(0, description="Longitud de la respuesta")
    tools_used: List[str] = Field(default_factory=list, description="Tools utilizadas")

class GapAnalyzerMetrics(BaseModel):
    """Métricas específicas del GapAnalyzer Agent."""
    
    # Context analysis
    practice_id: Optional[int] = Field(None, description="ID de práctica analizada")
    exercise_section: Optional[str] = Field(None, description="Sección de ejercicio")
    
    # Gap analysis
    gaps_identified: int = Field(0, description="Número de gaps identificados")
    gap_types: List[str] = Field(default_factory=list, description="Tipos de gaps encontrados")
    
    # Knowledge retrieval
    relevant_content_found: bool = Field(False, description="Si se encontró contenido relevante")
    content_sources: List[str] = Field(default_factory=list, description="Fuentes de contenido")
    
    # Response quality
    explanation_depth: Optional[str] = Field(None, description="Profundidad de explicación")
    examples_provided: int = Field(0, description="Número de ejemplos proporcionados")

# Configuración del sistema

class TestConfig(BaseModel):
    """Configuración global del sistema de testing."""
    
    # Paths
    suites_directory: str = Field("suites", description="Directorio de suites")
    results_directory: str = Field("results", description="Directorio de resultados")
    
    # Langfuse configuration
    langfuse_enabled: bool = Field(True, description="Si usar integración con Langfuse")
    langfuse_project_name: str = Field("luca-agent-testing", description="Proyecto en Langfuse")
    
    # Agent configuration
    default_timeout: int = Field(120, description="Timeout default en segundos")
    max_retries: int = Field(3, description="Número máximo de reintentos")
    
    # Metrics collection
    collect_agent_metadata: bool = Field(True, description="Si recolectar metadata de agentes")
    collect_performance_metrics: bool = Field(True, description="Si recolectar métricas de performance")

# Ejemplo de suite completa
EXAMPLE_SUITE = {
    "name": "orchestrator_basic_qa",
    "description": "Suite básica de preguntas y respuestas para Orchestrator",
    "agent_type": "orchestrator",
    "version": "1.0",
    "author": "LUCA Team",
    "questions": [
        {
            "id": "q1",
            "question": "¿Qué es un LEFT JOIN en bases de datos?",
            "expected_answer": "Un LEFT JOIN devuelve todos los registros de la tabla izquierda y los registros coincidentes de la tabla derecha",
            "subject": "Bases de Datos",
            "difficulty": "medium",
            "tags": ["sql", "joins", "bases-de-datos"],
            "metrics": {
                "should_use_kg": True,
                "expected_intent": "conceptual_explanation"
            }
        },
        {
            "id": "q2", 
            "question": "Necesito ayuda con el ejercicio 2.3 de la práctica de álgebra relacional",
            "expected_answer": "Debería enrutar a GapAnalyzer para análisis específico del ejercicio",
            "subject": "Álgebra Relacional",
            "difficulty": "hard",
            "tags": ["algebra-relacional", "ejercicios", "routing"],
            "metrics": {
                "should_route_to_gapanalyzer": True,
                "expected_intent": "practical_specific"
            }
        }
    ],
    "default_iterations": 1,
    "timeout_seconds": 60,
    "global_metrics": {
        "track_intent_detection": True,
        "track_kg_usage": True,
        "track_routing_decisions": True
    }
}