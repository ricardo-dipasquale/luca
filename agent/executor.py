"""Entrada única para el frontend: guardrails (entrada y salida) alrededor del agente tutor."""

from typing import Any, AsyncIterator, Optional

from agent.graph import TutorAgent


class TutorExecutor:
    def __init__(self, agent: Any = None, enable_guardrails: bool = True):
        self.agent = agent or TutorAgent()
        self.guardrails = None
        if enable_guardrails:
            from guardrails.config import load_guardrail_config_from_env
            from guardrails.orchestrator_integration import GuardrailOrchestrator

            self.guardrails = GuardrailOrchestrator(load_guardrail_config_from_env())

    async def stream(
        self, message: str, session_id: str, exercise_id: Optional[str] = None,
        user_id: Optional[str] = None, subject: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        # Signature imposed by GuardrailOrchestrator: (message, session_id, student_id, subject, config).
        async def tutor(processed: str, session: str, _student: Optional[str], _subject: Optional[str], _config: Any):
            async for chunk in self.agent.stream(processed, session, exercise_id):
                yield chunk

        if self.guardrails is None:
            async for chunk in tutor(message, session_id, user_id, subject, None):
                yield chunk
            return
        async for chunk in self.guardrails.create_guardrail_streaming_wrapper(
            tutor, message, session_id, user_id, subject
        ):
            yield chunk
