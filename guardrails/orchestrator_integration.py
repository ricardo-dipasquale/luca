"""
Orchestrator Integration - Integrates guardrails with the Orchestrator Agent.
"""

import logging
from typing import Dict, Any, Optional, AsyncIterable
from datetime import datetime

from .core import EducationalGuardrailLayer
from .schemas import EducationalContext, GuardrailConfig, GuardrailSeverity

logger = logging.getLogger(__name__)


class GuardrailOrchestrator:
    """
    Integrates guardrails with the Orchestrator Agent workflow.
    
    This class acts as a middleware layer that validates inputs and outputs
    in the orchestration process.
    """
    
    def __init__(self, config: Optional[GuardrailConfig] = None):
        """Initialize guardrail orchestrator."""
        self.config = config or GuardrailConfig()
        self.guardrail_layer = EducationalGuardrailLayer(self.config)
        logger.info("Guardrail Orchestrator initialized")
    
    async def validate_student_input(
        self, 
        user_message: str, 
        session_id: str,
        student_id: Optional[str] = None,
        educational_subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate student input before processing by Orchestrator.
        
        Args:
            user_message: The student's message
            session_id: Session identifier
            student_id: Optional student identifier
            educational_subject: Optional educational subject context
            
        Returns:
            Dictionary with validation results and processed input
        """
        # Create educational context
        context = EducationalContext(
            student_id=student_id,
            session_id=session_id,
            subject=educational_subject,
            current_topic=None,  # Could be extracted from conversation history
            academic_level="university",
            institution="UCA",
            language="es"
        )
        
        # Validate input through guardrail layer
        validation_result = await self.guardrail_layer.validate_input(user_message, context)
        
        # Prepare response
        response = {
            "validation_passed": validation_result.passed,
            "should_block": validation_result.should_block,
            "has_warnings": validation_result.has_warnings,
            "processed_input": validation_result.processed_input or user_message,
            "violations": [v.to_dict() for v in validation_result.violations],
            "metadata": validation_result.metadata,
            "execution_time_ms": validation_result.execution_time_ms
        }
        
        # Add user-friendly message if blocked
        if validation_result.should_block:
            response["user_message"] = self.guardrail_layer.get_user_friendly_message(validation_result)
        elif validation_result.has_warnings:
            # For warnings, we can add a gentle note
            warning_messages = [v.message for v in validation_result.violations if v.severity == GuardrailSeverity.WARNING]
            if warning_messages:
                response["warning_message"] = "Nota: " + "; ".join(warning_messages[:2])  # Limit to 2 warnings
        
        # Log significant events
        if validation_result.should_block:
            logger.warning(f"Blocked input from student {student_id} in session {session_id}: {[v.message for v in validation_result.violations]}")
        elif validation_result.has_warnings:
            logger.info(f"Warning for input from student {student_id} in session {session_id}: {[v.message for v in validation_result.violations]}")
        
        return response
    
    async def validate_agent_response(
        self,
        agent_response: str,
        original_input: str,
        session_id: str,
        student_id: Optional[str] = None,
        educational_subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate agent response before delivering to student.
        
        Args:
            agent_response: The agent's response
            original_input: The original student input
            session_id: Session identifier
            student_id: Optional student identifier
            educational_subject: Optional educational subject context
            
        Returns:
            Dictionary with validation results
        """
        if not self.config.enable_response_validation:
            return {
                "validation_passed": True,
                "response": agent_response
            }
        
        # Create educational context
        context = EducationalContext(
            student_id=student_id,
            session_id=session_id,
            subject=educational_subject,
            academic_level="university",
            institution="UCA",
            language="es"
        )
        
        # Validate response
        validation_result = await self.guardrail_layer.validate_response(
            agent_response, original_input, context
        )
        
        response = {
            "validation_passed": validation_result.passed,
            "response": agent_response,  # Could be modified if needed
            "violations": [v.to_dict() for v in validation_result.violations],
            "metadata": validation_result.metadata,
            "execution_time_ms": validation_result.execution_time_ms
        }
        
        # If response validation fails, we typically don't block but log
        if not validation_result.passed:
            logger.warning(f"Response validation concerns for session {session_id}: {[v.message for v in validation_result.violations]}")
        
        return response
    
    async def create_guardrail_streaming_wrapper(
        self,
        original_stream_func,
        user_message: str,
        session_id: str,
        student_id: Optional[str] = None,
        educational_subject: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncIterable[Dict[str, Any]]:
        """
        Create a streaming wrapper that includes guardrail validation.
        
        Args:
            original_stream_func: The original streaming function to wrap
            user_message: Student's message
            session_id: Session identifier
            student_id: Optional student identifier
            educational_subject: Optional subject context
            config: Optional config for the original function
            
        Yields:
            Stream chunks with guardrail information
        """
        # Step 1: Validate input
        yield {
            'is_task_complete': False,
            'require_user_input': False,
            'content': '🛡️ Validando seguridad y contexto educativo...',
            'guardrail_step': 'input_validation'
        }
        
        # Perform input validation
        input_validation = await self.validate_student_input(
            user_message, session_id, student_id, educational_subject
        )
        
        # If input is blocked, return error
        if input_validation["should_block"]:
            yield {
                'is_task_complete': True,
                'require_user_input': True,
                'content': input_validation["user_message"],
                'guardrail_blocked': True,
                'guardrail_violations': input_validation["violations"],
                'structured_response': {
                    'status': 'blocked_by_guardrails',
                    'guardrail_result': input_validation
                }
            }
            return
        
        # If warnings, include them in metadata but continue
        guardrail_metadata = {
            'input_validation': input_validation,
            'warnings': input_validation.get("warning_message")
        }
        
        # Use processed input if available
        processed_message = input_validation["processed_input"]
        
        # Step 2: Process through original stream
        final_response = ""
        final_metadata = {}
        
        async for chunk in original_stream_func(
            processed_message, session_id, student_id, educational_subject, config
        ):
            # Add guardrail metadata to chunks
            if 'guardrail_metadata' not in chunk:
                chunk['guardrail_metadata'] = guardrail_metadata
            
            # Capture final response for validation
            if chunk.get('is_task_complete'):
                final_response = chunk.get('content', '')
                final_metadata = chunk.get('structured_response', {})
            
            yield chunk
        
        # Step 3: Validate final response
        if final_response and self.config.enable_response_validation:
            response_validation = await self.validate_agent_response(
                final_response, user_message, session_id, student_id, educational_subject
            )
            
            # Log any response validation issues (but don't block)
            if not response_validation["validation_passed"]:
                logger.info(f"Response validation warnings for session {session_id}")
                # Could yield additional metadata about response quality
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '',  # Empty content, just metadata
                    'response_validation': response_validation,
                    'guardrail_step': 'response_validation'
                }
    
    def get_guardrail_status(self, student_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current guardrail status for a student.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Dictionary with guardrail status information
        """
        status = {
            "guardrails_enabled": True,
            "config": self.config.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add rate limiting status if available
        if student_id and self.config.enable_rate_limiting:
            try:
                rate_status = self.guardrail_layer.rate_limiting.get_user_status(student_id)
                status["rate_limiting"] = rate_status
            except Exception as e:
                logger.warning(f"Error getting rate limiting status: {e}")
                status["rate_limiting"] = {"error": str(e)}
        
        return status
    
    def update_config(self, new_config: GuardrailConfig):
        """
        Update guardrail configuration.
        
        Args:
            new_config: New guardrail configuration
        """
        self.config = new_config
        self.guardrail_layer = EducationalGuardrailLayer(new_config)
        logger.info("Guardrail configuration updated")
    
    async def admin_override_block(self, session_id: str, reason: str) -> bool:
        """
        Admin function to override a block (emergency use).
        
        Args:
            session_id: Session to unblock
            reason: Reason for override
            
        Returns:
            Success status
        """
        # In a real implementation, this would need proper admin authentication
        logger.warning(f"Admin override applied to session {session_id}: {reason}")
        return True