"""
Educational Context Guardrail - Validates academic relevance and curriculum alignment.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from .schemas import (
    GuardrailResult, 
    GuardrailViolation, 
    GuardrailSeverity,
    GuardrailType,
    EducationalContext,
    GuardrailConfig
)

logger = logging.getLogger(__name__)


class EducationalContextGuardrail:
    """Validates that content is educationally appropriate and curriculum-aligned."""
    
    def __init__(self, config: GuardrailConfig):
        """Initialize educational context guardrail."""
        self.config = config
        
        # Initialize OpenAI for educational relevance assessment
        self.openai_client = None
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info("OpenAI client initialized for educational relevance assessment")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI for educational assessment: {e}")
        
        # Academic keywords and domains for UCA Engineering curriculum
        self.academic_keywords = {
            # Programming & Software Engineering
            "programacion", "algoritmos", "estructuras de datos", "java", "python", "javascript",
            "bases de datos", "sql", "mysql", "postgresql", "mongodb", "join", "normalizacion",
            "desarrollo", "software", "aplicaciones", "web", "frontend", "backend",
            
            # Mathematics & Engineering
            "matematicas", "calculo", "algebra", "estadistica", "probabilidad", "geometria",
            "ingenieria", "sistemas", "redes", "arquitectura", "diseño", "analisis",
            "optimizacion", "modelado", "simulacion",
            
            # Computer Science
            "ciencias de la computacion", "inteligencia artificial", "machine learning",
            "data science", "big data", "cybersecurity", "seguridad", "encriptacion",
            "sistemas operativos", "unix", "linux", "windows", "networking",
            
            # Academic processes
            "ejercicio", "practica", "tarea", "proyecto", "examen", "evaluacion",
            "estudio", "aprender", "entender", "explicar", "teorema", "formula",
            "metodologia", "investigacion", "analisis", "sintesis"
        }
        
        # Non-academic topics that should be flagged
        self.non_academic_topics = {
            # Entertainment
            "futbol", "deportes", "musica", "peliculas", "series", "tv", "netflix",
            "juegos", "gaming", "videojuegos", "anime", "manga", "comics",
            
            # Social/Personal
            "relaciones", "amor", "pareja", "citas", "matrimonio", "familia",
            "politica", "religion", "filosofia personal", "horoscopo",
            
            # Off-topic professional
            "cocina", "recetas", "medicina", "salud", "fitness", "ejercicio fisico",
            "viajes", "turismo", "moda", "belleza", "decoracion",
            
            # Inappropriate requests
            "hacer trampa", "copiar", "plagiar", "falsificar", "mentir"
        }
    
    async def validate(self, user_input: str, context: EducationalContext) -> GuardrailResult:
        """
        Validate educational relevance of user input.
        
        Args:
            user_input: The user's input text
            context: Educational context
            
        Returns:
            GuardrailResult with educational validation results
        """
        violations = []
        metadata = {}
        
        # 1. Keyword-based academic relevance check
        relevance_result = self._check_academic_keywords(user_input, context)
        metadata['keyword_analysis'] = relevance_result
        
        # 2. Off-topic detection
        off_topic_result = self._check_off_topic_content(user_input)
        if off_topic_result['violations']:
            violations.extend(off_topic_result['violations'])
            metadata['off_topic_analysis'] = off_topic_result
        
        # 3. LLM-based educational relevance assessment (if available)
        if self.openai_client and relevance_result['academic_score'] < 0.3:
            try:
                llm_result = await self._assess_educational_relevance_llm(user_input, context)
                metadata['llm_assessment'] = llm_result
                
                if llm_result['violations']:
                    violations.extend(llm_result['violations'])
            except Exception as e:
                logger.warning(f"LLM educational assessment error: {e}")
                metadata['llm_assessment_error'] = str(e)
        
        # 4. Curriculum domain validation
        if context.subject:
            domain_result = self._validate_curriculum_domain(user_input, context)
            metadata['domain_validation'] = domain_result
            
            if domain_result['violations']:
                violations.extend(domain_result['violations'])
        
        return GuardrailResult(
            passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]]) == 0,
            violations=violations,
            metadata=metadata
        )
    
    async def validate_response(self, agent_response: str, original_input: str, context: EducationalContext) -> GuardrailResult:
        """
        Validate that agent response maintains educational value.
        
        Args:
            agent_response: The agent's response
            original_input: The original student input
            context: Educational context
            
        Returns:
            GuardrailResult for response validation
        """
        violations = []
        metadata = {}
        
        if not self.config.validate_educational_value:
            return GuardrailResult(passed=True)
        
        # Check if response provides educational value
        if self.openai_client:
            try:
                edu_value_result = await self._assess_response_educational_value(
                    agent_response, original_input, context
                )
                metadata['educational_value_assessment'] = edu_value_result
                
                if edu_value_result['violations']:
                    violations.extend(edu_value_result['violations'])
                    
            except Exception as e:
                logger.warning(f"Response educational value assessment error: {e}")
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            metadata=metadata
        )
    
    def _check_academic_keywords(self, text: str, context: EducationalContext) -> Dict[str, Any]:
        """Check for academic keywords and calculate relevance score."""
        text_lower = text.lower()
        
        # Count academic keywords
        academic_matches = []
        for keyword in self.academic_keywords:
            if keyword in text_lower:
                academic_matches.append(keyword)
        
        # Calculate academic relevance score
        academic_score = min(len(academic_matches) / 3.0, 1.0)  # Normalize to 0-1
        
        # Boost score if specific subject keywords are found
        if context.subject:
            subject_keywords = {
                "Bases de Datos": ["base", "datos", "sql", "join", "tabla", "consulta", "normalizacion"],
                "Programación": ["programar", "codigo", "algoritmo", "funcion", "variable", "clase"],
                "Matemáticas": ["matematica", "calculo", "algebra", "ecuacion", "formula", "derivada"],
                "Redes": ["red", "protocolo", "tcp", "ip", "router", "switch", "firewall"],
            }
            
            if context.subject in subject_keywords:
                subject_matches = [kw for kw in subject_keywords[context.subject] if kw in text_lower]
                if subject_matches:
                    academic_score += 0.3  # Bonus for subject-specific terms
                    academic_score = min(academic_score, 1.0)
        
        return {
            "academic_matches": academic_matches,
            "academic_score": academic_score,
            "text_length": len(text),
            "subject_context": context.subject
        }
    
    def _check_off_topic_content(self, text: str) -> Dict[str, Any]:
        """Check for clearly off-topic content."""
        violations = []
        text_lower = text.lower()
        
        found_off_topic = []
        for topic in self.non_academic_topics:
            if topic in text_lower:
                found_off_topic.append(topic)
        
        if found_off_topic:
            # Determine severity based on how off-topic it is
            severity = GuardrailSeverity.BLOCK if len(found_off_topic) > 2 else GuardrailSeverity.WARNING
            
            if not self.config.strict_academic_mode and self.config.allow_general_knowledge:
                # In permissive mode, only warn for clearly inappropriate topics
                inappropriate_topics = {"hacer trampa", "copiar", "plagiar", "falsificar"}
                if any(topic in inappropriate_topics for topic in found_off_topic):
                    severity = GuardrailSeverity.BLOCK
                else:
                    severity = GuardrailSeverity.WARNING
            
            violations.append(GuardrailViolation(
                type=GuardrailType.OFF_TOPIC,
                severity=severity,
                message="La consulta parece estar fuera del contexto académico",
                details={
                    "off_topic_terms": found_off_topic,
                    "strict_mode": self.config.strict_academic_mode
                }
            ))
        
        return {
            "violations": violations,
            "off_topic_terms": found_off_topic
        }
    
    def _validate_curriculum_domain(self, text: str, context: EducationalContext) -> Dict[str, Any]:
        """Validate that content aligns with curriculum domains."""
        violations = []
        
        # Check if the query is within allowed curriculum domains
        text_lower = text.lower()
        domain_matches = []
        
        for domain in context.curriculum_domains:
            if domain.lower() in text_lower:
                domain_matches.append(domain)
        
        # If no domain matches and we're in strict mode, flag it
        if not domain_matches and self.config.strict_academic_mode:
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=GuardrailSeverity.WARNING,
                message=f"La consulta no parece estar alineada con los dominios curriculares: {', '.join(context.curriculum_domains)}",
                details={
                    "curriculum_domains": context.curriculum_domains,
                    "domain_matches": domain_matches
                }
            ))
        
        return {
            "violations": violations,
            "domain_matches": domain_matches,
            "curriculum_domains": context.curriculum_domains
        }
    
    async def _assess_educational_relevance_llm(self, text: str, context: EducationalContext) -> Dict[str, Any]:
        """Use LLM to assess educational relevance of ambiguous content."""
        try:
            prompt = f"""
Analiza si la siguiente consulta de un estudiante universitario de Ingeniería es educativamente apropiada y relevante para el contexto académico.

Contexto educativo:
- Institución: {context.institution}
- Nivel: {context.academic_level}
- Materia: {context.subject or 'No especificada'}
- Dominios curriculares: {', '.join(context.curriculum_domains)}

Consulta del estudiante: "{text}"

Evalúa:
1. ¿Es esta consulta educativamente apropiada? (Sí/No)
2. ¿Está relacionada con el curriculum de Ingeniería? (Sí/No)
3. Puntaje de relevancia educativa (0-10)
4. Explicación breve

Responde en formato JSON:
{{
    "educationally_appropriate": true/false,
    "curriculum_related": true/false,
    "relevance_score": 0-10,
    "explanation": "explicación breve"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.choices[0].message.content)
            
            violations = []
            if not result.get("educationally_appropriate", True):
                violations.append(GuardrailViolation(
                    type=GuardrailType.EDUCATIONAL_CONTEXT,
                    severity=GuardrailSeverity.BLOCK,
                    message=f"Consulta no apropiada educativamente: {result.get('explanation', 'Sin explicación')}",
                    details=result
                ))
            elif not result.get("curriculum_related", True) and result.get("relevance_score", 10) < 4:
                violations.append(GuardrailViolation(
                    type=GuardrailType.EDUCATIONAL_CONTEXT,
                    severity=GuardrailSeverity.WARNING,
                    message=f"Consulta con baja relevancia curricular: {result.get('explanation', 'Sin explicación')}",
                    details=result
                ))
            
            return {
                "violations": violations,
                "llm_assessment": result
            }
            
        except Exception as e:
            logger.debug(f"LLM educational relevance assessment failed: {e}")
            return {"violations": [], "error": str(e)}
    
    async def _assess_response_educational_value(self, response: str, original_input: str, context: EducationalContext) -> Dict[str, Any]:
        """Assess if agent response provides educational value."""
        try:
            prompt = f"""
Evalúa si la siguiente respuesta del asistente educativo proporciona valor educativo apropiado para un estudiante universitario.

Consulta original: "{original_input}"
Respuesta del asistente: "{response}"
Contexto: Materia {context.subject or 'No especificada'}, Nivel universitario

Evalúa:
1. ¿Proporciona valor educativo? (Sí/No)
2. ¿Es apropiada para el nivel universitario? (Sí/No) 
3. ¿Evita dar respuestas directas sin explicación pedagógica? (Sí/No)
4. Puntaje de calidad educativa (0-10)

Responde en JSON:
{{
    "educational_value": true/false,
    "appropriate_level": true/false,
    "avoids_direct_answers": true/false,
    "quality_score": 0-10
}}
"""
            
            response_eval = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            import json
            result = json.loads(response_eval.choices[0].message.content)
            
            violations = []
            if not result.get("educational_value", True) or result.get("quality_score", 10) < 4:
                violations.append(GuardrailViolation(
                    type=GuardrailType.RESPONSE_VALIDATION,
                    severity=GuardrailSeverity.WARNING,
                    message="La respuesta podría tener bajo valor educativo",
                    details=result
                ))
            
            return {
                "violations": violations,
                "educational_assessment": result
            }
            
        except Exception as e:
            logger.error(f"Response educational value assessment failed: {e}")
            return {"violations": [], "error": str(e)}