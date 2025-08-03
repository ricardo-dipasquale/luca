"""
Core Guardrails System - Main orchestration of educational guardrails.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .schemas import (
    GuardrailResult, 
    GuardrailViolation, 
    GuardrailSeverity,
    GuardrailType,
    EducationalContext,
    GuardrailConfig
)

# Import specific guardrail implementations
from .content_safety import ContentSafetyGuardrail
from .educational_context import EducationalContextGuardrail
from .rate_limiting import RateLimitingGuardrail

# Import Langfuse for observability
try:
    from tools.observability import get_langfuse_client
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

logger = logging.getLogger(__name__)


class EducationalGuardrailLayer:
    """
    Main orchestration layer for educational guardrails.
    
    This class coordinates all guardrail checks and provides the primary
    interface for validating student inputs before they reach the agents.
    """
    
    def __init__(self, config: Optional[GuardrailConfig] = None):
        """
        Initialize the guardrail layer.
        
        Args:
            config: Configuration for the guardrail system
        """
        self.config = config or GuardrailConfig()
        self.langfuse_client = None
        
        # Try to initialize Langfuse client if available and enabled
        if LANGFUSE_AVAILABLE and self.config.enable_langfuse_logging:
            try:
                self.langfuse_client = get_langfuse_client()
                # Test that the client works by checking if it has the required methods
                if self.langfuse_client and hasattr(self.langfuse_client, 'start_span'):
                    logger.debug("Langfuse client initialized and validated")
                else:
                    logger.warning("Langfuse client missing required methods, disabling")
                    self.langfuse_client = None
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse client: {e}, disabling observability")
                self.langfuse_client = None
        
        # Initialize individual guardrail components
        self.content_safety = ContentSafetyGuardrail(self.config)
        self.educational_context = EducationalContextGuardrail(self.config)
        self.rate_limiting = RateLimitingGuardrail(self.config)
        
        logger.info("Educational Guardrail Layer initialized")
        if self.langfuse_client:
            logger.info("Langfuse integration enabled for guardrail observability")
    
    async def validate_input(
        self, 
        user_input: str, 
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate user input through all enabled guardrails.
        
        Args:
            user_input: The student's input message
            context: Educational context for the validation
            
        Returns:
            GuardrailResult with validation outcome and any violations
        """
        start_time = time.time()
        violations = []
        processed_input = user_input
        metadata = {
            "original_input_length": len(user_input),
            "context": context.to_dict(),
            "guardrails_executed": []
        }
        
        # Simple event logging to Langfuse (no span context needed)
        langfuse_enabled = self.langfuse_client and self.config.enable_langfuse_logging
        if langfuse_enabled:
            try:
                # Create a simple event for guardrail validation start
                self.langfuse_client.create_event(
                    name="guardrail_validation_start",
                    input={"user_input": user_input[:500], "subject": context.subject or "unknown"},
                    metadata={
                        "guardrails_enabled": True,
                        "institution": context.institution or "UCA",
                        "student_id": context.student_id or "anonymous",
                        "session_id": context.session_id or "anonymous"
                    }
                )
                logger.debug("Langfuse event created for guardrail validation")
            except Exception as e:
                logger.debug(f"Failed to create Langfuse event: {e}")
                langfuse_enabled = False
        
        try:
            # 1. Content Safety Check (highest priority)
            if self.config.enable_openai_moderation or self.config.enable_profanity_filter:
                logger.debug("Running content safety check")
                safety_result = await self.content_safety.validate(user_input, context)
                violations.extend(safety_result.violations)
                metadata["guardrails_executed"].append("content_safety")
                
                if safety_result.processed_input:
                    processed_input = safety_result.processed_input
                
                # Log to Langfuse (simplified event)
                if langfuse_enabled and safety_result.violations:
                    try:
                        self.langfuse_client.create_event(
                            name="content_safety_violation",
                            metadata={
                                "violations_count": len(safety_result.violations),
                                "student_id": context.student_id or "anonymous"
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Failed to log content safety to Langfuse: {e}")
            
            # 2. Rate Limiting Check
            if self.config.enable_rate_limiting:
                logger.debug("Running rate limiting check")
                rate_result = await self.rate_limiting.validate(user_input, context)
                violations.extend(rate_result.violations)
                metadata["guardrails_executed"].append("rate_limiting")
                
                # Log to Langfuse (simplified event)
                if langfuse_enabled and rate_result.violations:
                    try:
                        self.langfuse_client.create_event(
                            name="rate_limit_violation",
                            metadata={
                                "violations_count": len(rate_result.violations),
                                "student_id": context.student_id or "anonymous"
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Failed to log rate limiting to Langfuse: {e}")
            
            # 3. Educational Context Validation
            if self.config.enable_educational_validation:
                logger.debug("Running educational context validation")
                edu_result = await self.educational_context.validate(processed_input, context)
                violations.extend(edu_result.violations)
                metadata["guardrails_executed"].append("educational_context")
                
                # Log to Langfuse (simplified event)
                if langfuse_enabled:
                    try:
                        self.langfuse_client.create_event(
                            name="educational_context_check",
                            metadata={
                                "violations_count": len(edu_result.violations),
                                "academic_score": edu_result.metadata.get("relevance_score", 0),
                                "student_id": context.student_id or "anonymous"
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Failed to log educational context to Langfuse: {e}")
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create final result
            result = GuardrailResult(
                passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL,GuardrailSeverity.WARNING]]) == 0,
                violations=violations,
                processed_input=processed_input if processed_input != user_input else None,
                metadata=metadata,
                execution_time_ms=execution_time_ms
            )
            
            # Log final result to Langfuse (simplified event)
            if langfuse_enabled:
                try:
                    self.langfuse_client.create_event(
                        name="guardrail_validation_complete",
                        output={
                            "passed": result.passed,
                            "total_violations": len(violations),
                            "execution_time_ms": execution_time_ms
                        },
                        metadata={
                            "student_id": context.student_id or "anonymous",
                            "session_id": context.session_id or "anonymous"
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to log final result to Langfuse: {e}")
            
            # Log critical violations
            if result.critical_violations:
                logger.warning(f"Critical guardrail violations detected for user {context.student_id}: {[v.message for v in result.critical_violations]}")
            
            logger.info(f"Guardrail validation completed: passed={result.passed}, violations={len(violations)}, time={execution_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            # Log error to Langfuse (simplified event)
            if langfuse_enabled:
                try:
                    self.langfuse_client.create_event(
                        name="guardrail_validation_error",
                        output={"error": str(e)},
                        metadata={"student_id": context.student_id or "anonymous"}
                    )
                except Exception as langfuse_error:
                    logger.debug(f"Failed to log error to Langfuse: {langfuse_error}")
            
            logger.error(f"Error in guardrail validation: {e}")
            
            # Return error result that blocks the request
            return GuardrailResult(
                passed=False,
                violations=[GuardrailViolation(
                    type=GuardrailType.CONTENT_SAFETY,
                    severity=GuardrailSeverity.CRITICAL,
                    message=f"Guardrail system error: {str(e)}",
                    details={"error_type": type(e).__name__},
                    user_id=context.student_id,
                    session_id=context.session_id
                )],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_user_friendly_message(self, result: GuardrailResult) -> str:
        """
        Generate a user-friendly message for guardrail violations.
        
        Args:
            result: The guardrail validation result
            
        Returns:
            User-friendly message explaining the issue
        """
        if result.passed:
            return ""
        
        # Categorize violations
        content_violations = [v for v in result.violations if v.type == GuardrailType.CONTENT_SAFETY]
        edu_violations = [v for v in result.violations if v.type == GuardrailType.EDUCATIONAL_CONTEXT]
        rate_violations = [v for v in result.violations if v.type == GuardrailType.RATE_LIMITING]
        profanity_violations = [v for v in result.violations if v.type == GuardrailType.PROFANITY_FILTER]
        
        messages = []

        if profanity_violations:
            # ZERO TOLERANCE POLICY: Any profanity blocks the content
            messages.append("Tu mensaje contiene lenguaje inapropiado. Por favor, evitá el uso de insultos o groserías.")        

        if content_violations:
            messages.append("Tu mensaje contiene contenido inapropiado para el contexto educativo. Por favor, reformulá tu consulta de manera respetuosa.")
        
        if edu_violations:
            if any(v.severity == GuardrailSeverity.BLOCK for v in edu_violations):
                messages.append("Tu consulta no está relacionada con los temas académicos que puedo ayudarte. Por favor, hacé preguntas sobre Ingeniería, Matemáticas, Programación u otros temas del curriculum.")
            else:
                messages.append("Tu consulta podría estar fuera del contexto académico principal. ¿Podrías ser más específico about cómo se relaciona con tus estudios?")
        
        if rate_violations:
            messages.append("Has enviado demasiadas consultas en poco tiempo. Por favor, esperá unos minutos antes de continuar.")
        
        if not messages:
            messages.append("Tu consulta no puede ser procesada en este momento. Por favor, contactá a soporte técnico si el problema persiste.")
        
        return " ".join(messages)
    
    async def validate_response(
        self, 
        agent_response: str, 
        original_input: str,
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate agent response before delivering to student.
        
        Args:
            agent_response: The agent's response
            original_input: The original student input
            context: Educational context
            
        Returns:
            GuardrailResult for the response validation
        """
        if not self.config.enable_response_validation:
            return GuardrailResult(passed=True)
        
        start_time = time.time()
        violations = []
        
        # Simple event logging for response validation
        langfuse_enabled = self.langfuse_client and self.config.enable_langfuse_logging
        if langfuse_enabled:
            try:
                self.langfuse_client.create_event(
                    name="response_validation_start",
                    input={"agent_response": agent_response[:500], "original_input": original_input[:500]},
                    metadata={
                        "student_id": context.student_id or "anonymous",
                        "session_id": context.session_id or "anonymous" 
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to create Langfuse event for response validation: {e}")
                langfuse_enabled = False
        
        try:
            # Check response for inappropriate content
            if self.config.enable_openai_moderation:
                safety_result = await self.content_safety.validate_response(agent_response, context)
                violations.extend(safety_result.violations)
            
            # Validate educational value if enabled
            if self.config.validate_educational_value:
                edu_result = await self.educational_context.validate_response(agent_response, original_input, context)
                violations.extend(edu_result.violations)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = GuardrailResult(
                passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]]) == 0,
                violations=violations,
                execution_time_ms=execution_time_ms
            )
            
            # Log to Langfuse
            if langfuse_enabled:
                try:
                    self.langfuse_client.create_event(
                        name="response_validation_complete",
                        output={
                            "passed": result.passed,
                            "total_violations": len(violations),
                            "execution_time_ms": execution_time_ms
                        },
                        metadata={"student_id": context.student_id or "anonymous"}
                    )
                except Exception as e:
                    logger.debug(f"Failed to log response validation result to Langfuse: {e}")
            
            return result
            
        except Exception as e:
            if langfuse_enabled:
                try:
                    self.langfuse_client.create_event(
                        name="response_validation_error",
                        output={"error": str(e)},
                        metadata={"student_id": context.student_id or "anonymous"}
                    )
                except Exception as langfuse_error:
                    logger.debug(f"Failed to log response validation error to Langfuse: {langfuse_error}")
            
            logger.error(f"Error in response validation: {e}")
            return GuardrailResult(
                passed=True,  # Don't block responses due to validation errors
                violations=[],
                execution_time_ms=(time.time() - start_time) * 1000
            )