"""
Core Guardrails System - Main orchestration of educational guardrails.
"""

import logging
import time
from typing import Optional

from .content_safety import ContentSafetyGuardrail
from .educational_context import EducationalContextGuardrail
from .rate_limiting import RateLimitingGuardrail
from .schemas import (
    EducationalContext,
    GuardrailConfig,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailType,
    GuardrailViolation,
)

logger = logging.getLogger(__name__)


class EducationalGuardrailLayer:
    """Coordinates every guardrail check on student input and on the tutor's responses."""

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.config = config or GuardrailConfig()
        self.content_safety = ContentSafetyGuardrail(self.config)
        self.educational_context = EducationalContextGuardrail(self.config)
        self.rate_limiting = RateLimitingGuardrail(self.config)
        logger.info("Educational Guardrail Layer initialized")

    async def validate_input(self, user_input: str, context: EducationalContext) -> GuardrailResult:
        """Run the enabled guardrails on the student's message: content safety, rate limiting, academic context."""
        start_time = time.time()
        violations = []
        processed_input = user_input
        metadata = {
            "original_input_length": len(user_input),
            "context": context.to_dict(),
            "guardrails_executed": [],
        }

        try:
            if self.config.enable_openai_moderation or self.config.enable_profanity_filter:
                safety_result = await self.content_safety.validate(user_input, context)
                violations.extend(safety_result.violations)
                metadata["guardrails_executed"].append("content_safety")
                if safety_result.processed_input:
                    processed_input = safety_result.processed_input

            if self.config.enable_rate_limiting:
                rate_result = await self.rate_limiting.validate(user_input, context)
                violations.extend(rate_result.violations)
                metadata["guardrails_executed"].append("rate_limiting")

            if self.config.enable_educational_validation:
                edu_result = await self.educational_context.validate(processed_input, context)
                violations.extend(edu_result.violations)
                metadata["guardrails_executed"].append("educational_context")

            execution_time_ms = (time.time() - start_time) * 1000
            bloqueantes = (GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL, GuardrailSeverity.WARNING)
            result = GuardrailResult(
                passed=not any(v.severity in bloqueantes for v in violations),
                violations=violations,
                processed_input=processed_input if processed_input != user_input else None,
                metadata=metadata,
                execution_time_ms=execution_time_ms,
            )
            if result.critical_violations:
                logger.warning(f"Critical guardrail violations for user {context.student_id}: "
                               f"{[v.message for v in result.critical_violations]}")
            logger.info(f"Guardrail validation completed: passed={result.passed}, "
                        f"violations={len(violations)}, time={execution_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Error in guardrail validation: {e}")
            # Fail closed: an error in the guardrails blocks the request.
            return GuardrailResult(
                passed=False,
                violations=[GuardrailViolation(
                    type=GuardrailType.CONTENT_SAFETY,
                    severity=GuardrailSeverity.CRITICAL,
                    message=f"Guardrail system error: {str(e)}",
                    details={"error_type": type(e).__name__},
                    user_id=context.student_id,
                    session_id=context.session_id,
                )],
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def get_user_friendly_message(self, result: GuardrailResult) -> str:
        if result.passed:
            return ""

        content_violations = [v for v in result.violations if v.type == GuardrailType.CONTENT_SAFETY]
        edu_violations = [v for v in result.violations if v.type == GuardrailType.EDUCATIONAL_CONTEXT]
        rate_violations = [v for v in result.violations if v.type == GuardrailType.RATE_LIMITING]
        profanity_violations = [v for v in result.violations if v.type == GuardrailType.PROFANITY_FILTER]

        messages = []
        if profanity_violations:
            # Zero tolerance: any profanity blocks the message.
            messages.append("Tu mensaje contiene lenguaje inapropiado. Por favor, evitá el uso de insultos o groserías.")
        if content_violations:
            messages.append("Tu mensaje contiene contenido inapropiado para el contexto educativo. "
                            "Por favor, reformulá tu consulta de manera respetuosa.")
        if edu_violations:
            if any(v.severity == GuardrailSeverity.BLOCK for v in edu_violations):
                messages.append("Tu consulta no está relacionada con los temas académicos que puedo ayudarte. Por favor, "
                                "hacé preguntas sobre Ingeniería, Matemáticas, Programación u otros temas del curriculum.")
            else:
                messages.append("Tu consulta podría estar fuera del contexto académico principal. "
                                "¿Podrías ser más específico sobre cómo se relaciona con tus estudios?")
        if rate_violations:
            messages.append("Has enviado demasiadas consultas en poco tiempo. Por favor, esperá unos minutos antes de continuar.")
        if not messages:
            messages.append("Tu consulta no puede ser procesada en este momento. "
                            "Por favor, contactá a soporte técnico si el problema persiste.")
        return " ".join(messages)

    async def validate_response(self, agent_response: str, original_input: str,
                                context: EducationalContext) -> GuardrailResult:
        """Check the tutor's response (safety, educational value). Never blocks on errors: it only reports."""
        if not self.config.enable_response_validation:
            return GuardrailResult(passed=True)

        start_time = time.time()
        violations = []
        try:
            if self.config.enable_openai_moderation:
                safety_result = await self.content_safety.validate_response(agent_response, context)
                violations.extend(safety_result.violations)
            if self.config.validate_educational_value:
                edu_result = await self.educational_context.validate_response(agent_response, original_input, context)
                violations.extend(edu_result.violations)
            return GuardrailResult(
                passed=not any(v.severity in (GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL) for v in violations),
                violations=violations,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"Error in response validation: {e}")
            return GuardrailResult(passed=True, violations=[], execution_time_ms=(time.time() - start_time) * 1000)
