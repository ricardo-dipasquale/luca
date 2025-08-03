"""
Orchestrator-specific Guardrails - Mid-level validation within orchestrator workflow.
"""

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

# Import orchestrator schemas for intent validation
try:
    from orchestrator.schemas import StudentIntent
    ORCHESTRATOR_SCHEMAS_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_SCHEMAS_AVAILABLE = False

logger = logging.getLogger(__name__)


class OrchestratorGuardrails:
    """Mid-level guardrails specific to orchestrator workflow."""
    
    def __init__(self, config: GuardrailConfig):
        """Initialize orchestrator-specific guardrails."""
        self.config = config
        logger.info("Orchestrator-specific guardrails initialized")
    
    async def validate_intent_classification(
        self, 
        intent: Any,  # StudentIntent when available
        original_input: str,
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate that intent classification is appropriate for educational context.
        
        Args:
            intent: Classified student intent
            original_input: Original student input
            context: Educational context
            
        Returns:
            GuardrailResult with intent validation
        """
        violations = []
        metadata = {"intent_value": str(intent) if intent else None}
        
        if not ORCHESTRATOR_SCHEMAS_AVAILABLE:
            # If orchestrator schemas not available, skip intent validation
            return GuardrailResult(passed=True, metadata=metadata)
        
        # Check if intent is educationally appropriate
        inappropriate_intents = []
        
        # Example validation logic (would need to be adapted based on actual StudentIntent enum)
        if hasattr(intent, 'value'):
            intent_value = intent.value.lower() if isinstance(intent.value, str) else str(intent.value).lower()
            
            # Flag potentially problematic intents
            if 'entertainment' in intent_value or 'social' in intent_value:
                inappropriate_intents.append("entertainment_or_social")
            elif 'manipulation' in intent_value or 'jailbreak' in intent_value:
                inappropriate_intents.append("system_manipulation") 
            elif 'off_topic' in intent_value:
                inappropriate_intents.append("off_topic_content")
        
        # Create violations for inappropriate intents
        for inappropriate in inappropriate_intents:
            severity = GuardrailSeverity.BLOCK if inappropriate == "system_manipulation" else GuardrailSeverity.WARNING
            
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=severity,
                message=f"Intent classification suggests inappropriate content: {inappropriate}",
                details={
                    "classified_intent": str(intent),
                    "inappropriate_category": inappropriate,
                    "original_input": original_input[:100]  # First 100 chars for context
                },
                user_id=context.student_id,
                session_id=context.session_id
            ))
        
        return GuardrailResult(
            passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]]) == 0,
            violations=violations,
            metadata=metadata
        )
    
    async def validate_routing_decision(
        self,
        routing_agent: str,
        reasoning: str,
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate agent routing decisions.
        
        Args:
            routing_agent: Target agent for routing
            reasoning: Reasoning for routing decision
            context: Educational context
            
        Returns:
            GuardrailResult with routing validation
        """
        violations = []
        metadata = {
            "routing_agent": routing_agent,
            "reasoning": reasoning
        }
        
        # Validate that routing is to appropriate educational agents
        valid_educational_agents = ["orchestrator", "gapanalyzer", "tutor", "practice_helper"]
        
        if routing_agent and routing_agent.lower() not in valid_educational_agents:
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=GuardrailSeverity.WARNING,
                message=f"Routing to unrecognized agent: {routing_agent}",
                details={
                    "routing_agent": routing_agent,
                    "valid_agents": valid_educational_agents,
                    "reasoning": reasoning
                },
                user_id=context.student_id,
                session_id=context.session_id
            ))
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            metadata=metadata
        )
    
    async def validate_knowledge_retrieval(
        self,
        query_results: List[Dict[str, Any]],
        original_query: str,
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate knowledge graph query results for educational appropriateness.
        
        Args:
            query_results: Results from knowledge graph queries
            original_query: Original student query
            context: Educational context
            
        Returns:
            GuardrailResult with knowledge retrieval validation
        """
        violations = []
        metadata = {
            "results_count": len(query_results),
            "query_successful": len(query_results) > 0
        }
        
        # Check if results are educationally relevant
        if query_results:
            # Analyze result content for educational value
            educational_keywords = ["ejercicio", "practica", "teoria", "concepto", "ejemplo", "formula"]
            
            educational_content_found = False
            for result in query_results[:5]:  # Check first 5 results
                result_text = str(result).lower()
                if any(keyword in result_text for keyword in educational_keywords):
                    educational_content_found = True
                    break
            
            if not educational_content_found:
                violations.append(GuardrailViolation(
                    type=GuardrailType.EDUCATIONAL_CONTEXT,
                    severity=GuardrailSeverity.WARNING,
                    message="Knowledge retrieval results may lack educational content",
                    details={
                        "results_preview": [str(r)[:100] for r in query_results[:3]],
                        "educational_keywords_checked": educational_keywords
                    },
                    user_id=context.student_id,
                    session_id=context.session_id
                ))
        
        # Warn if no results found for educational query
        elif len(original_query.split()) > 3:  # Substantial query with no results
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=GuardrailSeverity.INFO,
                message="No knowledge base results found for substantial educational query",
                details={
                    "query_length": len(original_query),
                    "word_count": len(original_query.split())
                },
                user_id=context.student_id,
                session_id=context.session_id
            ))
        
        return GuardrailResult(
            passed=True,  # Knowledge retrieval issues are typically warnings, not blocks
            violations=violations,
            metadata=metadata
        )
    
    async def validate_multi_agent_coordination(
        self,
        coordination_data: Dict[str, Any],
        context: EducationalContext
    ) -> GuardrailResult:
        """
        Validate multi-agent coordination for educational appropriateness.
        
        Args:
            coordination_data: Data about multi-agent coordination
            context: Educational context
            
        Returns:
            GuardrailResult with coordination validation
        """
        violations = []
        metadata = coordination_data.copy()
        
        # Check for excessive agent switching (might indicate confusion or manipulation)
        agent_switches = coordination_data.get("agent_switches", 0)
        if agent_switches > 3:
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=GuardrailSeverity.WARNING,
                message=f"Excessive agent switching detected ({agent_switches} switches)",
                details={
                    "agent_switches": agent_switches,
                    "max_recommended": 3,
                    "possible_causes": ["unclear_query", "system_confusion", "manipulation_attempt"]
                },
                user_id=context.student_id,
                session_id=context.session_id
            ))
        
        # Check for coordination with non-educational agents
        involved_agents = coordination_data.get("involved_agents", [])
        non_educational_agents = [agent for agent in involved_agents 
                                if agent not in ["orchestrator", "gapanalyzer", "tutor", "practice_helper"]]
        
        if non_educational_agents:
            violations.append(GuardrailViolation(
                type=GuardrailType.EDUCATIONAL_CONTEXT,
                severity=GuardrailSeverity.WARNING,
                message=f"Coordination with non-educational agents: {non_educational_agents}",
                details={
                    "non_educational_agents": non_educational_agents,
                    "all_involved_agents": involved_agents
                },
                user_id=context.student_id,
                session_id=context.session_id
            ))
        
        return GuardrailResult(
            passed=len([v for v in violations if v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL]]) == 0,
            violations=violations,
            metadata=metadata
        )