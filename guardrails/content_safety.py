"""
Content Safety Guardrail - OpenAI Moderation API and profanity filtering.
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

# Import LLM configuration
try:
    from tools.llm_config import create_default_llm
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContentSafetyGuardrail:
    """Content safety validation using OpenAI Moderation API and custom filters."""
    
    def __init__(self, config: GuardrailConfig):
        """Initialize content safety guardrail."""
        self.config = config
        self.openai_client = None
        self.llm = None
        
        # Initialize OpenAI client if moderation API method is enabled
        if config.enable_openai_moderation and config.content_safety_method == "moderation_api":
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info("OpenAI Moderation API initialized for content safety")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI Moderation API: {e}")
                self.openai_client = None
        
        # Initialize LLM if LLM method is enabled
        if config.content_safety_method == "llm" and LLM_AVAILABLE:
            try:
                self.llm = create_default_llm()
                logger.info("LLM initialized for content safety using GPT-4o-mini")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for content safety: {e}")
                self.llm = None
        
        # Spanish profanity and inappropriate terms (contextual for Argentina/UCA)
        # ZERO TOLERANCE POLICY: Any detected term will immediately block the content
        self.spanish_profanity = {
            # Basic profanity
            "mierda", "carajo", "joder", "coño", "puta", "puto", "pendejo", "pendeja", 
            "boludo", "boluda", "pelotudo", "pelotuda", "forro", "hijo de puta", "la concha",
            "concha", "verga", "pija", "chota", "garcha", "cagar", "cagada", "cago", "sorete",
            
            # Stronger terms
            "marica", "maricon", "trolo", "puto", "negros", "sudaca", "maraca"
            
            # Academic inappropriate terms
            "mambo", "chamullo", "chamuyar", "boludez", "pavada"
        }
        
        # Compile regex patterns for efficiency
        self.profanity_patterns = [
            re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE) 
            for word in self.spanish_profanity
        ]
    
    async def validate(self, user_input: str, context: EducationalContext) -> GuardrailResult:
        """
        Validate user input for content safety.
        
        Args:
            user_input: The user's input text
            context: Educational context
            
        Returns:
            GuardrailResult with any content safety violations
        """
        violations = []
        metadata = {}
        
        # 1. Content safety check based on configured method
        if self.config.content_safety_method == "moderation_api" and self.openai_client:
            try:
                moderation_result = await self._check_openai_moderation(user_input)
                if moderation_result['flagged']:
                    violations.extend(moderation_result['violations'])
                    metadata['openai_moderation'] = moderation_result
            except Exception as e:
                logger.warning(f"OpenAI Moderation API error: {e}")
                # Don't block on API errors, but log the issue
                metadata['openai_moderation_error'] = str(e)
        
        elif self.config.content_safety_method == "llm" and self.llm:
            try:
                llm_result = await self._check_llm_content_safety(user_input, context)
                if llm_result['violations']:
                    violations.extend(llm_result['violations'])
                    metadata['llm_content_safety'] = llm_result
            except Exception as e:
                logger.warning(f"LLM content safety error: {e}")
                # Don't block on API errors, but log the issue
                metadata['llm_content_safety_error'] = str(e)
        
        # 2. Spanish profanity filter
        if self.config.enable_profanity_filter:
            profanity_result = self._check_spanish_profanity(user_input)
            if profanity_result['violations']:
                violations.extend(profanity_result['violations'])
                metadata['profanity_check'] = profanity_result
        
        # 3. Educational context inappropriate content
        inappropriate_result = self._check_inappropriate_educational_content(user_input, context)
        if inappropriate_result['violations']:
            violations.extend(inappropriate_result['violations'])
            metadata['inappropriate_content'] = inappropriate_result
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            metadata=metadata
        )
    
    async def validate_response(self, agent_response: str, context: EducationalContext) -> GuardrailResult:
        """
        Validate agent response for content safety.
        
        Args:
            agent_response: The agent's response
            context: Educational context
            
        Returns:
            GuardrailResult for response validation
        """
        violations = []
        metadata = {}
        
        # Check agent response through OpenAI Moderation
        if self.config.enable_openai_moderation and self.openai_client:
            try:
                moderation_result = await self._check_openai_moderation(agent_response)
                if moderation_result['flagged']:
                    violations.extend([
                        GuardrailViolation(
                            type=GuardrailType.RESPONSE_VALIDATION,
                            severity=GuardrailSeverity.CRITICAL,
                            message="Agent response contains inappropriate content",
                            details=moderation_result,
                            user_id=context.student_id,
                            session_id=context.session_id
                        )
                    ])
                    metadata['response_moderation'] = moderation_result
            except Exception as e:
                logger.warning(f"Response moderation error: {e}")
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            metadata=metadata
        )
    
    async def _check_openai_moderation(self, text: str) -> Dict[str, Any]:
        """Check text using OpenAI Moderation API."""
        try:
            response = self.openai_client.moderations.create(input=text)
            result = response.results[0]
            
            violations = []
            if result.flagged:
                # Create violations for each flagged category
                for category, flagged in result.categories.dict().items():
                    if flagged:
                        score = result.category_scores.dict().get(category, 0)
                        if score > self.config.content_safety_threshold:
                            severity = GuardrailSeverity.CRITICAL if score > 0.9 else GuardrailSeverity.BLOCK
                            violations.append(GuardrailViolation(
                                type=GuardrailType.CONTENT_SAFETY,
                                severity=severity,
                                message=f"Content flagged for {category.replace('_', ' ')}",
                                details={
                                    "category": category,
                                    "score": score,
                                    "threshold": self.config.content_safety_threshold
                                }
                            ))
            
            return {
                "flagged": result.flagged,
                "violations": violations,
                "categories": result.categories.dict(),
                "category_scores": result.category_scores.dict()
            }
            
        except Exception as e:
            logger.error(f"OpenAI Moderation API error: {e}")
            raise
    
    async def _check_llm_content_safety(self, text: str, context: EducationalContext) -> Dict[str, Any]:
        """Check content safety using LLM (GPT-4o-mini) with contextual understanding."""
        try:
            # Create a specialized prompt for content safety in educational context
            safety_prompt = f"""Sos un moderador de contenido especializado en contexto educativo universitario argentino. 

Tu tarea es evaluar si el siguiente mensaje de un estudiante es apropiado para un entorno educativo universitario.

CONTEXTO:
- Institución: Universidad Católica Argentina (UCA)
- Materia: {context.subject or 'General'}
- Nivel: Universitario
- País: Argentina

MENSAJE DEL ESTUDIANTE: "{text}"

CRITERIOS DE EVALUACIÓN:
1. PROFANIDAD: Insultos, groserías, lenguaje ofensivo (ZERO TOLERANCE)
2. CONTENIDO INAPROPIADO: Contenido sexual, violento, discriminatorio
3. ACOSO: Intimidación, amenazas, hostigamiento
4. CONTEXTO ARGENTINO: Considerar modismos locales (ej: "boludo" en tono amistoso vs agresivo)
5. CONTEXTO EDUCATIVO: El mensaje debe ser apropiado para consultas académicas

INSTRUCCIONES:
- Si el contenido es completamente apropiado, responde: {{"safe": true, "reason": "none"}}
- Si hay violaciones, responde: {{"safe": false, "reason": "descripción específica", "severity": "block|warning", "categories": ["profanidad", "acoso", etc.]}}
- Para términos argentinos ambiguos, considera el contexto y tono
- ZERO TOLERANCE para profanidad clara
- Sé estricto pero contextual

Responde SOLO con JSON válido:"""

            # Call the LLM for content safety assessment
            response = await self.llm.ainvoke(safety_prompt)
            
            # Parse the response
            import json
            try:
                safety_result = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.warning(f"Failed to parse LLM content safety response: {response.content}")
                return {"violations": [], "error": "Failed to parse LLM response"}
            
            violations = []
            if not safety_result.get("safe", True):
                # Determine severity
                severity_str = safety_result.get("severity", "warning").lower()
                severity = GuardrailSeverity.BLOCK if severity_str == "block" else GuardrailSeverity.WARNING
                
                # Create violation
                violations.append(GuardrailViolation(
                    type=GuardrailType.CONTENT_SAFETY,
                    severity=severity,
                    message=f"Contenido inapropiado detectado por LLM: {safety_result.get('reason', 'Motivo no especificado')}",
                    details={
                        "reason": safety_result.get("reason"),
                        "categories": safety_result.get("categories", []),
                        "method": "llm_gpt4o_mini",
                        "context_aware": True
                    }
                ))
            
            return {
                "violations": violations,
                "safe": safety_result.get("safe", True),
                "reason": safety_result.get("reason"),
                "categories": safety_result.get("categories", []),
                "llm_response": safety_result
            }
            
        except Exception as e:
            logger.error(f"LLM content safety error: {e}")
            # Return empty result on error - don't block due to technical issues
            return {"violations": [], "error": str(e)}
    
    def _check_spanish_profanity(self, text: str) -> Dict[str, Any]:
        """Check for Spanish profanity and inappropriate language."""
        violations = []
        found_terms = []
        
        for pattern in self.profanity_patterns:
            matches = pattern.findall(text)
            if matches:
                found_terms.extend(matches)
        
        if found_terms:
            # ZERO TOLERANCE POLICY: Any profanity is immediately blocked
            violations.append(GuardrailViolation(
                type=GuardrailType.PROFANITY_FILTER,
                severity=GuardrailSeverity.BLOCK,  # Always BLOCK, no warnings for profanity
                message=f"Lenguaje inapropiado detectado - zero tolerance policy",
                details={
                    "found_terms": ["***censored***"] * len(found_terms),  # Don't log actual terms
                    "count": len(found_terms),
                    "zero_tolerance": True
                }
            ))
        
        return {
            "violations": violations,
            "found_terms": found_terms
        }
    
    def _check_inappropriate_educational_content(self, text: str, context: EducationalContext) -> Dict[str, Any]:
        """Check for content inappropriate in educational context."""
        violations = []
        
        # Check for patterns that are inappropriate in academic settings
        inappropriate_patterns = [
            # Academic dishonesty indicators
            (r"hace?me?\s+(la\s+)?tarea", "Solicitud de hacer tarea completa"),
            (r"resol[vb]eme?\s+(el\s+)?ejercicio", "Solicitud de resolver ejercicio completo"),
            (r"dame\s+(la\s+)?respuesta", "Solicitud directa de respuestas"),
            
            # Off-topic entertainment
            (r"cont[aá]me\s+(un\s+)?chiste", "Contenido de entretenimiento no educativo"),
            (r"habl[ae]mos\s+de\s+(f[uú]tbol|deportes|pol[ií]tica)", "Tema fuera del contexto académico"),
            
            # Manipulation attempts
            (r"ignor[aá]\s+tus\s+instrucciones", "Intento de manipulación del sistema"),
            (r"act[uú]a\s+como\s+si", "Intento de cambiar el rol del asistente"),
        ]
        
        for pattern, reason in inappropriate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    type=GuardrailType.ACADEMIC_INTEGRITY,
                    severity=GuardrailSeverity.WARNING,
                    message=f"Contenido posiblemente inapropiado: {reason}",
                    details={"pattern_matched": pattern, "reason": reason},
                    user_id=context.student_id,
                    session_id=context.session_id
                ))
        
        return {
            "violations": violations
        }