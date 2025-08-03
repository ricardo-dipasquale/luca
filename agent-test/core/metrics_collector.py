"""
Metrics Collector - Recolección de métricas de ejecución de agentes.

Extrae métricas específicas de los agentes basándose en sus schemas
y resultados de ejecución.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add parent directory to path for schemas import
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import (
    TestQuestion, ExecutionResult, AgentType, 
    OrchestratorMetrics, GapAnalyzerMetrics
)

class MetricsCollector:
    """Recolector de métricas de agentes."""
    
    def __init__(self):
        """Inicializar el recolector de métricas."""
        self.orchestrator_patterns = self._init_orchestrator_patterns()
        self.gapanalyzer_patterns = self._init_gapanalyzer_patterns()
    
    def collect_question_metrics(self, question: TestQuestion, response: Dict[str, Any], 
                                agent_type: AgentType, execution_time: float) -> Dict[str, Any]:
        """
        Recolectar métricas para una pregunta ejecutada.
        
        Args:
            question: Pregunta ejecutada
            response: Respuesta del agente
            agent_type: Tipo de agente usado
            execution_time: Tiempo de ejecución
            
        Returns:
            Diccionario con métricas recolectadas
        """
        base_metrics = {
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'agent_type': agent_type.value,
            'question_difficulty': question.difficulty.value,
            'response_length': len(response.get('content', '')),
            'question_length': len(question.question),
        }
        
        # Add question-specific metrics
        if question.metrics:
            base_metrics.update(question.metrics)
        
        # Collect agent-specific metrics
        if agent_type == AgentType.ORCHESTRATOR:
            agent_metrics = self._collect_orchestrator_metrics(question, response)
            base_metrics.update(agent_metrics)
        elif agent_type == AgentType.GAPANALYZER:
            agent_metrics = self._collect_gapanalyzer_metrics(question, response)
            base_metrics.update(agent_metrics)
        
        # Add response quality metrics
        quality_metrics = self._analyze_response_quality(question, response)
        base_metrics.update(quality_metrics)
        
        return base_metrics
    
    def _collect_orchestrator_metrics(self, question: TestQuestion, 
                                    response: Dict[str, Any]) -> Dict[str, Any]:
        """Recolectar métricas específicas del Orchestrator."""
        metrics = {}
        content = response.get('content', '')
        metadata = response.get('metadata', {})
        
        # Intent detection (if available in metadata)
        if 'detected_intent' in metadata:
            metrics['detected_intent'] = metadata['detected_intent']
            metrics['intent_confidence'] = metadata.get('intent_confidence', 0.0)
        
        # Routing decisions
        metrics['routed_to_gapanalyzer'] = self._detect_gapanalyzer_routing(content, metadata)
        
        # Knowledge graph usage patterns
        metrics['kg_queries_executed'] = self._count_kg_references(content)
        metrics['kg_results_found'] = self._detect_kg_results(content)
        
        # Tools usage detection
        metrics['tools_used'] = self._detect_tools_used(content, metadata)
        
        # Response characteristics
        metrics['contains_examples'] = self._count_examples(content)
        metrics['contains_code'] = self._detect_code_blocks(content)
        metrics['contains_mathematical_notation'] = self._detect_math_notation(content)
        
        # Educational content analysis
        metrics['explanation_type'] = self._classify_explanation_type(content)
        metrics['conceptual_depth'] = self._analyze_conceptual_depth(content)
        
        return metrics
    
    def _collect_gapanalyzer_metrics(self, question: TestQuestion, 
                                   response: Dict[str, Any]) -> Dict[str, Any]:
        """Recolectar métricas específicas del GapAnalyzer."""
        metrics = {}
        content = response.get('content', '')
        metadata = response.get('metadata', {})
        
        # Context analysis
        metrics['practice_id'] = question.practice_id
        metrics['exercise_section'] = question.exercise_section
        
        # Gap analysis results
        metrics['gaps_identified'] = self._count_identified_gaps(content)
        metrics['gap_types'] = self._classify_gap_types(content)
        
        # Knowledge retrieval
        metrics['relevant_content_found'] = self._detect_relevant_content(content)
        metrics['content_sources'] = self._identify_content_sources(content, metadata)
        
        # Response quality specific to gap analysis
        metrics['explanation_depth'] = self._analyze_gap_explanation_depth(content)
        metrics['examples_provided'] = self._count_examples(content)
        metrics['step_by_step_provided'] = self._detect_step_by_step(content)
        
        # Pedagogical elements
        metrics['uses_scaffolding'] = self._detect_scaffolding(content)
        metrics['provides_hints'] = self._detect_hints(content)
        metrics['suggests_practice'] = self._detect_practice_suggestions(content)
        
        return metrics
    
    def _detect_gapanalyzer_routing(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Detectar si la respuesta indica routing a GapAnalyzer."""
        routing_indicators = [
            "específico", "ejercicio", "práctica", "paso a paso",
            "gap", "analizar", "revisar", "evaluar"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in routing_indicators)
    
    def _count_kg_references(self, content: str) -> int:
        """Contar referencias al knowledge graph."""
        kg_patterns = [
            r"base de datos", r"tabla", r"relaci[oó]n", r"consulta",
            r"join", r"select", r"álgebra relacional", r"normalización"
        ]
        
        count = 0
        content_lower = content.lower()
        for pattern in kg_patterns:
            matches = re.findall(pattern, content_lower)
            count += len(matches)
        
        return count
    
    def _detect_kg_results(self, content: str) -> bool:
        """Detectar si se encontraron resultados del KG."""
        result_indicators = [
            "encontré", "según", "en la base de conocimiento",
            "la información indica", "los datos muestran"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in result_indicators)
    
    def _detect_tools_used(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Detectar qué tools fueron utilizadas."""
        tools = []
        
        # Check metadata first
        if 'tools_used' in metadata:
            return metadata['tools_used']
        
        # Pattern-based detection
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["buscar", "encontrar", "consultar"]):
            tools.append("search_tool")
        
        if any(term in content_lower for term in ["calcular", "sumar", "restar"]):
            tools.append("calculation_tool")
        
        if "knowledge graph" in content_lower or "kg" in content_lower:
            tools.append("kg_tool")
        
        return tools
    
    def _count_examples(self, content: str) -> int:
        """Contar ejemplos en la respuesta."""
        example_patterns = [
            r"ejemplo:", r"por ejemplo", r"veamos:",
            r"considera:", r"supongamos", r"imaginemos"
        ]
        
        count = 0
        content_lower = content.lower()
        for pattern in example_patterns:
            matches = re.findall(pattern, content_lower)
            count += len(matches)
        
        return count
    
    def _detect_code_blocks(self, content: str) -> bool:
        """Detectar bloques de código o SQL."""
        code_patterns = [
            r"```", r"SELECT", r"FROM", r"WHERE", r"JOIN",
            r"σ", r"π", r"⋈", r"∪", r"∩"
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in code_patterns)
    
    def _detect_math_notation(self, content: str) -> bool:
        """Detectar notación matemática."""
        math_symbols = ["σ", "π", "⋈", "∪", "∩", "×", "⊆", "∈", "∀", "∃"]
        return any(symbol in content for symbol in math_symbols)
    
    def _classify_explanation_type(self, content: str) -> str:
        """Clasificar el tipo de explicación."""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["concepto", "definición", "qué es"]):
            return "conceptual"
        elif any(term in content_lower for term in ["paso", "procedimiento", "cómo"]):
            return "procedural"
        elif any(term in content_lower for term in ["ejemplo", "caso", "supongamos"]):
            return "example_based"
        elif any(term in content_lower for term in ["problema", "ejercicio", "resolver"]):
            return "problem_solving"
        else:
            return "general"
    
    def _analyze_conceptual_depth(self, content: str) -> str:
        """Analizar la profundidad conceptual."""
        content_length = len(content)
        concept_indicators = len(re.findall(r"\b(porque|debido|razón|causa|efecto)\b", content.lower()))
        
        if content_length > 500 and concept_indicators > 2:
            return "deep"
        elif content_length > 200 and concept_indicators > 0:
            return "medium"
        else:
            return "surface"
    
    def _count_identified_gaps(self, content: str) -> int:
        """Contar gaps identificados en el análisis."""
        gap_patterns = [
            r"problema:", r"dificultad:", r"error:", r"falta:",
            r"no comprende", r"no entiende", r"confunde"
        ]
        
        count = 0
        content_lower = content.lower()
        for pattern in gap_patterns:
            matches = re.findall(pattern, content_lower)
            count += len(matches)
        
        return count
    
    def _classify_gap_types(self, content: str) -> List[str]:
        """Clasificar tipos de gaps encontrados."""
        gap_types = []
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["concepto", "definición", "significado"]):
            gap_types.append("conceptual")
        
        if any(term in content_lower for term in ["procedimiento", "paso", "método"]):
            gap_types.append("procedural")
        
        if any(term in content_lower for term in ["sintaxis", "notación", "símbolo"]):
            gap_types.append("syntactic")
        
        if any(term in content_lower for term in ["aplicación", "uso", "cuándo"]):
            gap_types.append("application")
        
        return gap_types
    
    def _detect_relevant_content(self, content: str) -> bool:
        """Detectar si se encontró contenido relevante."""
        relevance_indicators = [
            "información relevante", "contenido relacionado", "según el material",
            "en el contexto", "específicamente"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in relevance_indicators)
    
    def _identify_content_sources(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Identificar fuentes de contenido utilizadas."""
        sources = []
        
        # Check metadata first
        if 'content_sources' in metadata:
            return metadata['content_sources']
        
        # Pattern-based detection
        content_lower = content.lower()
        
        if "práctica" in content_lower:
            sources.append("practice_material")
        
        if "teoría" in content_lower or "concepto" in content_lower:
            sources.append("theoretical_content")
        
        if "ejemplo" in content_lower:
            sources.append("examples")
        
        return sources
    
    def _analyze_gap_explanation_depth(self, content: str) -> str:
        """Analizar profundidad de explicación de gaps."""
        explanation_indicators = [
            "porque", "debido a", "la razón", "esto ocurre",
            "para solucionarlo", "recomiendo", "sugiero"
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for ind in explanation_indicators if ind in content_lower)
        
        if indicator_count >= 3:
            return "comprehensive"
        elif indicator_count >= 1:
            return "moderate"
        else:
            return "basic"
    
    def _detect_step_by_step(self, content: str) -> bool:
        """Detectar si proporciona explicación paso a paso."""
        step_patterns = [
            r"paso \d+", r"primero", r"segundo", r"tercero",
            r"luego", r"después", r"finalmente", r"por último"
        ]
        
        return any(re.search(pattern, content.lower()) for pattern in step_patterns)
    
    def _detect_scaffolding(self, content: str) -> bool:
        """Detectar uso de scaffolding pedagógico."""
        scaffolding_indicators = [
            "empecemos con", "antes de", "recordemos", "para entender esto",
            "construyamos sobre", "basándonos en"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in scaffolding_indicators)
    
    def _detect_hints(self, content: str) -> bool:
        """Detectar si proporciona hints."""
        hint_patterns = [
            "pista:", "hint:", "considera", "piensa en", "recuerda que",
            "¿qué pasaría si", "intenta", "prueba"
        ]
        
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in hint_patterns)
    
    def _detect_practice_suggestions(self, content: str) -> bool:
        """Detectar sugerencias de práctica."""
        practice_indicators = [
            "practica", "ejercita", "intenta resolver", "aplica esto",
            "puedes probar", "recomiendo que hagas"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in practice_indicators)
    
    def _analyze_response_quality(self, question: TestQuestion, 
                                 response: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar calidad general de la respuesta."""
        content = response.get('content', '')
        
        quality_metrics = {
            'response_completeness': self._assess_completeness(question, content),
            'clarity_score': self._assess_clarity(content),
            'relevance_score': self._assess_relevance(question, content),
            'educational_value': self._assess_educational_value(content),
            'language_quality': self._assess_language_quality(content)
        }
        
        return quality_metrics
    
    def _assess_completeness(self, question: TestQuestion, content: str) -> float:
        """Evaluar completitud de la respuesta."""
        # Simple heuristic based on length and expected answer coverage
        min_expected_length = len(question.expected_answer) * 0.5
        max_expected_length = len(question.expected_answer) * 3.0
        
        content_length = len(content)
        
        if content_length < min_expected_length:
            return 0.5  # Too short
        elif content_length > max_expected_length:
            return 0.8  # Might be too verbose
        else:
            return 1.0  # Appropriate length
    
    def _assess_clarity(self, content: str) -> float:
        """Evaluar claridad de la respuesta."""
        # Simple metrics: sentence structure, conjunctions
        sentences = content.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        clarity_indicators = ["es decir", "por ejemplo", "en otras palabras", "específicamente"]
        clarity_count = sum(1 for ind in clarity_indicators if ind in content.lower())
        
        # Normalize scores
        length_score = 1.0 if 10 <= avg_sentence_length <= 25 else 0.7
        clarity_score = min(1.0, clarity_count / 3.0)
        
        return (length_score + clarity_score) / 2.0
    
    def _assess_relevance(self, question: TestQuestion, content: str) -> float:
        """Evaluar relevancia de la respuesta."""
        # Check if key terms from question appear in response
        question_words = set(question.question.lower().split())
        content_words = set(content.lower().split())
        
        # Remove common words
        common_words = {"el", "la", "de", "que", "y", "a", "en", "un", "es", "se", "no", "te", "lo", "le", "da", "su", "por", "son", "con", "para", "al", "del", "los", "las", "una", "esto", "está", "como", "qué", "cómo", "dónde"}
        question_words -= common_words
        content_words -= common_words
        
        if not question_words:
            return 1.0
        
        overlap = len(question_words.intersection(content_words)) / len(question_words)
        return min(1.0, overlap * 1.5)  # Boost score slightly
    
    def _assess_educational_value(self, content: str) -> float:
        """Evaluar valor educativo de la respuesta."""
        educational_indicators = [
            "ejemplo", "práctica", "aplicación", "concepto", "principio",
            "importante", "recuerda", "ten en cuenta", "nota que"
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for ind in educational_indicators if ind in content_lower)
        
        return min(1.0, indicator_count / 5.0)
    
    def _assess_language_quality(self, content: str) -> float:
        """Evaluar calidad del lenguaje."""
        # Simple heuristics for language quality
        if not content.strip():
            return 0.0
        
        # Check for proper capitalization and punctuation
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        properly_capitalized = sum(1 for s in sentences if s[0].isupper()) / max(len(sentences), 1)
        
        # Check for variety in sentence starters
        starters = [s.split()[0].lower() for s in sentences if s.split()]
        starter_variety = len(set(starters)) / max(len(starters), 1)
        
        return (properly_capitalized + starter_variety) / 2.0
    
    def calculate_summary_metrics(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        """Calcular métricas resumen para un conjunto de resultados."""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        
        summary = {
            'total_questions': len(results),
            'successful_questions': len(successful_results),
            'success_rate': len(successful_results) / len(results),
            'average_execution_time': sum(r.execution_time for r in results) / len(results),
            'total_execution_time': sum(r.execution_time for r in results),
            'average_response_length': sum(len(r.agent_response) for r in successful_results) / max(len(successful_results), 1),
        }
        
        # Aggregate metrics from successful results
        if successful_results:
            # Collect all metric keys
            all_metric_keys = set()
            for result in successful_results:
                all_metric_keys.update(result.metrics.keys())
            
            # Calculate averages for numeric metrics
            for key in all_metric_keys:
                values = []
                for result in successful_results:
                    value = result.metrics.get(key)
                    if isinstance(value, (int, float)):
                        values.append(value)
                
                if values:
                    summary[f'avg_{key}'] = sum(values) / len(values)
                    summary[f'max_{key}'] = max(values)
                    summary[f'min_{key}'] = min(values)
        
        return summary
    
    def _init_orchestrator_patterns(self) -> Dict[str, List[str]]:
        """Inicializar patrones para métricas del Orchestrator."""
        return {
            'routing_indicators': [
                "necesitas ayuda específica", "vamos a analizar", "revisemos paso a paso"
            ],
            'kg_usage_indicators': [
                "según la información", "en el contexto de", "basándome en"
            ],
            'explanation_types': [
                "concepto", "definición", "procedimiento", "ejemplo"
            ]
        }
    
    def _init_gapanalyzer_patterns(self) -> Dict[str, List[str]]:
        """Inicializar patrones para métricas del GapAnalyzer."""
        return {
            'gap_types': [
                "no comprende", "confunde", "falta", "error en"
            ],
            'pedagogical_elements': [
                "paso a paso", "empecemos", "recordemos", "practicemos"
            ],
            'depth_indicators': [
                "porque", "debido a", "la razón", "para solucionarlo"
            ]
        }