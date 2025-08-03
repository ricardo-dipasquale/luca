"""
Agent Response Validation - Post-processing validation of agent responses.
"""

import re
import logging
from typing import Dict, Any, List, Optional

from .schemas import (
    GuardrailResult, 
    GuardrailViolation, 
    GuardrailSeverity,
    GuardrailType,
    EducationalContext,
    GuardrailConfig
)

logger = logging.getLogger(__name__)


class AgentResponseValidator:
    """Validates agent responses for educational appropriateness and quality."""
    
    def __init__(self, config: GuardrailConfig):
        """Initialize response validator."""
        self.config = config
        
        # Patterns that indicate low educational value
        self.low_value_patterns = [
            # Direct answer without explanation
            (r'^[^.]{1,50}\.$', "Respuesta muy corta sin explicación"),
            (r'^(Sí|No|Si|Correcto|Incorrecto)\.?$', "Respuesta de una sola palabra sin contexto"),
            
            # Copy-paste indicators
            (r'según (google|wikipedia|internet)', "Posible contenido copiado de fuentes externas"),
            (r'fuente:', "Referencia a fuentes sin contexto educativo"),
            
            # Non-educational content
            (r'(no puedo ayudar|no soy capaz|fuera de mi alcance)', "Respuesta evasiva sin orientación educativa"),
        ]
        
        # Patterns that indicate good educational practices
        self.good_practices_patterns = [
            (r'(por ejemplo|veamos|consideremos)', "Uso de ejemplos"),
            (r'(paso a paso|primero|segundo|luego)', "Explicación estructurada"),
            (r'(porque|ya que|debido a|la razón)', "Explicación causal"),
            (r'(recorda que|es importante|ten en cuenta)', "Refuerzo pedagógico"),
        ]
        
        # Compile patterns for efficiency
        self.low_value_regex = [(re.compile(pattern, re.IGNORECASE), desc) 
                               for pattern, desc in self.low_value_patterns]
        self.good_practices_regex = [(re.compile(pattern, re.IGNORECASE), desc) 
                                   for pattern, desc in self.good_practices_patterns]
    
    async def validate_response(
        self, 
        response: str, 
        original_question: str,
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate an agent response for educational quality.
        
        Args:
            response: The agent's response
            original_question: The original student question
            context: Educational context
            
        Returns:
            GuardrailResult with validation outcome
        """
        violations = []
        metadata = {}
        
        # 1. Basic response quality checks
        quality_result = self._check_response_quality(response, original_question)
        violations.extend(quality_result['violations'])
        metadata['quality_analysis'] = quality_result
        
        # 2. Educational value assessment
        educational_result = self._assess_educational_value(response, original_question, context)
        violations.extend(educational_result['violations'])
        metadata['educational_analysis'] = educational_result
        
        # 3. Pedagogical practices check
        pedagogical_result = self._check_pedagogical_practices(response)
        metadata['pedagogical_analysis'] = pedagogical_result
        
        # 4. Language and tone appropriateness
        language_result = self._check_language_appropriateness(response)
        violations.extend(language_result['violations'])
        metadata['language_analysis'] = language_result
        
        return GuardrailResult(
            passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]]) == 0,
            violations=violations,
            metadata=metadata
        )
    
    def _check_response_quality(self, response: str, original_question: str) -> Dict[str, Any]:
        """Check basic response quality metrics."""
        violations = []
        
        # Length checks
        response_length = len(response.strip())
        question_length = len(original_question.strip())
        
        if response_length < 50:
            violations.append(GuardrailViolation(
                type=GuardrailType.RESPONSE_VALIDATION,
                severity=GuardrailSeverity.WARNING,
                message="Respuesta muy corta - podría beneficiarse de más explicación",
                details={"response_length": response_length, "min_expected": 50}
            ))
        
        # Check for very long responses that might be overwhelming
        elif response_length > 2000:
            violations.append(GuardrailViolation(
                type=GuardrailType.RESPONSE_VALIDATION,
                severity=GuardrailSeverity.WARNING,
                message="Respuesta muy larga - podría ser abrumadora para el estudiante",
                details={"response_length": response_length, "max_recommended": 2000}
            ))
        
        # Check response/question length ratio
        length_ratio = response_length / max(question_length, 1)
        if length_ratio < 0.5:
            violations.append(GuardrailViolation(
                type=GuardrailType.RESPONSE_VALIDATION,
                severity=GuardrailSeverity.WARNING,
                message="Respuesta proporcionalmente muy corta para la pregunta",
                details={"length_ratio": length_ratio, "min_ratio": 0.5}
            ))
        
        return {
            "violations": violations,
            "response_length": response_length,
            "question_length": question_length,
            "length_ratio": length_ratio
        }
    
    def _assess_educational_value(self, response: str, original_question: str, context: EducationalContext) -> Dict[str, Any]:
        """Assess educational value of the response."""
        violations = []
        educational_indicators = {
            "explanations": 0,
            "examples": 0,
            "structured_content": 0,
            "academic_terms": 0,
            "low_value_patterns": []
        }
        
        # Check for low educational value patterns
        for pattern, description in self.low_value_regex:
            if pattern.search(response):
                educational_indicators["low_value_patterns"].append(description)
                violations.append(GuardrailViolation(
                    type=GuardrailType.RESPONSE_VALIDATION,
                    severity=GuardrailSeverity.WARNING,
                    message=f"Posible bajo valor educativo: {description}",
                    details={"pattern_description": description}
                ))
        
        # Count positive educational indicators
        if re.search(r'(porque|ya que|debido a|esto significa|la razón)', response, re.IGNORECASE):
            educational_indicators["explanations"] += 1
        
        if re.search(r'(por ejemplo|veamos|consideremos|supongamos)', response, re.IGNORECASE):
            educational_indicators["examples"] += 1
        
        if re.search(r'(primero|segundo|luego|finalmente|paso \d)', response, re.IGNORECASE):
            educational_indicators["structured_content"] += 1
        
        # Count academic terms relevant to the subject
        if context.subject:
            subject_terms = {
                "Bases de Datos": ["tabla", "consulta", "sql", "join", "clave", "relación", "normalización"],
                "Programación": ["función", "variable", "algoritmo", "clase", "método", "objeto"],
                "Matemáticas": ["ecuación", "fórmula", "teorema", "demostración", "cálculo"],
                "Redes": ["protocolo", "tcp", "ip", "router", "firewall", "seguridad"]
            }
            
            if context.subject in subject_terms:
                for term in subject_terms[context.subject]:
                    if term.lower() in response.lower():
                        educational_indicators["academic_terms"] += 1
        
        # Overall educational value score
        edu_score = (
            educational_indicators["explanations"] * 2 +
            educational_indicators["examples"] * 2 +
            educational_indicators["structured_content"] * 1 +
            educational_indicators["academic_terms"] * 0.5 -
            len(educational_indicators["low_value_patterns"]) * 2
        )
        
        if edu_score < 2:
            violations.append(GuardrailViolation(
                type=GuardrailType.RESPONSE_VALIDATION,
                severity=GuardrailSeverity.WARNING,
                message="La respuesta podría beneficiarse de más valor educativo",
                details={
                    "educational_score": edu_score,
                    "indicators": educational_indicators,
                    "suggestion": "Considerar agregar ejemplos, explicaciones o estructura"
                }
            ))
        
        return {
            "violations": violations,
            "educational_score": edu_score,
            "indicators": educational_indicators
        }
    
    def _check_pedagogical_practices(self, response: str) -> Dict[str, Any]:
        """Check for good pedagogical practices in the response."""
        practices_found = []
        
        for pattern, description in self.good_practices_regex:
            if pattern.search(response):
                practices_found.append(description)
        
        # Check for scaffolding (building on previous knowledge)
        if re.search(r'(recordás que|como vimos|anteriormente|previamente)', response, re.IGNORECASE):
            practices_found.append("Conexión con conocimiento previo")
        
        # Check for encouragement and positive reinforcement
        if re.search(r'(excelente|muy bien|correcto|buen trabajo)', response, re.IGNORECASE):
            practices_found.append("Refuerzo positivo")
        
        # Check for questioning to promote thinking
        if re.search(r'(qué pensás|cómo crees|por qué será|qué pasaría si)', response, re.IGNORECASE):
            practices_found.append("Preguntas para estimular pensamiento")
        
        return {
            "practices_found": practices_found,
            "practice_count": len(practices_found),
            "pedagogical_quality": "high" if len(practices_found) >= 3 else "medium" if len(practices_found) >= 1 else "low"
        }
    
    def _check_language_appropriateness(self, response: str) -> Dict[str, Any]:
        """Check language appropriateness for university level."""
        violations = []
        
        # Check for overly casual language
        casual_patterns = [
            r'\bcopado\b', r'\bgenial\b', r'\bbarbaro\b', r'\bmassa\b',
            r'\btipo que\b', r'\bonda\b', r'\btranqui\b'
        ]
        
        casual_found = []
        for pattern in casual_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                casual_found.append(pattern)
        
        if casual_found:
            violations.append(GuardrailViolation(
                type=GuardrailType.RESPONSE_VALIDATION,
                severity=GuardrailSeverity.WARNING,
                message="El lenguaje podría ser demasiado casual para el contexto universitario",
                details={"casual_expressions": casual_found}
            ))
        
        # Check for appropriate formality level
        formal_indicators = len(re.findall(r'(utilizamos|realizamos|consideramos|analizamos)', response, re.IGNORECASE))
        informal_indicators = len(re.findall(r'(usamos|hacemos|vemos|miramos)', response, re.IGNORECASE))
        
        formality_ratio = formal_indicators / max(formal_indicators + informal_indicators, 1)
        
        return {
            "violations": violations,
            "casual_expressions": casual_found,
            "formality_ratio": formality_ratio,
            "appropriate_formality": formality_ratio >= 0.3  # At least 30% formal language
        }