"""
Guardrails Schemas - Data models for guardrail system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class GuardrailSeverity(Enum):
    """Severity levels for guardrail violations."""
    INFO = "info"           # Informational, logged but allowed
    WARNING = "warning"     # Warning issued, but request processed
    BLOCK = "block"         # Request blocked completely
    CRITICAL = "critical"   # Severe violation, user flagged


class GuardrailType(Enum):
    """Types of guardrail checks."""
    CONTENT_SAFETY = "content_safety"
    EDUCATIONAL_CONTEXT = "educational_context"
    RATE_LIMITING = "rate_limiting"
    PROFANITY_FILTER = "profanity_filter"
    OFF_TOPIC = "off_topic"
    ACADEMIC_INTEGRITY = "academic_integrity"
    RESPONSE_VALIDATION = "response_validation"


@dataclass
class GuardrailViolation:
    """Represents a guardrail violation."""
    type: GuardrailType
    severity: GuardrailSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id
        }


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    passed: bool
    violations: List[GuardrailViolation] = field(default_factory=list)
    processed_input: Optional[str] = None  # Modified input if sanitization occurred
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    
    @property
    def should_block(self) -> bool:
        """Whether the request should be blocked."""
        return any(v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL, GuardrailSeverity.WARNING] 
                  for v in self.violations)
    
    @property
    def has_warnings(self) -> bool:
        """Whether there are warnings."""
        return any(v.severity == GuardrailSeverity.WARNING for v in self.violations)
    
    @property
    def critical_violations(self) -> List[GuardrailViolation]:
        """Get critical violations."""
        return [v for v in self.violations if v.severity == GuardrailSeverity.CRITICAL]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage.""" 
        return {
            "passed": self.passed,
            "should_block": self.should_block,
            "has_warnings": self.has_warnings,
            "violations": [v.to_dict() for v in self.violations],
            "processed_input": self.processed_input,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms
        }


@dataclass 
class EducationalContext:
    """Educational context for guardrail validation."""
    student_id: Optional[str] = None
    session_id: Optional[str] = None
    subject: Optional[str] = None
    current_topic: Optional[str] = None
    academic_level: str = "university"  # university, postgraduate, etc.
    institution: str = "UCA"
    language: str = "es"  # Spanish
    curriculum_domains: List[str] = field(default_factory=lambda: [
        "Ingeniería", "Matemáticas", "Programación", "Bases de Datos", 
        "Algoritmos", "Estructuras de Datos", "Redes", "Sistemas Operativos"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "student_id": self.student_id,
            "session_id": self.session_id,
            "subject": self.subject,
            "current_topic": self.current_topic,
            "academic_level": self.academic_level,
            "institution": self.institution,
            "language": self.language,
            "curriculum_domains": self.curriculum_domains
        }


@dataclass
class GuardrailConfig:
    """Configuration for guardrail system."""
    # Content Safety
    enable_openai_moderation: bool = True
    enable_profanity_filter: bool = True
    content_safety_threshold: float = 0.7
    content_safety_method: str = "llm"  # "moderation_api" or "llm"
    
    # Educational Context
    enable_educational_validation: bool = True
    strict_academic_mode: bool = False  # If True, blocks all non-academic content
    allow_general_knowledge: bool = True  # Allow general knowledge questions
    
    # Rate Limiting
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 30
    max_requests_per_hour: int = 200
    max_requests_per_day: int = 1000
    
    # Response Validation
    enable_response_validation: bool = True
    validate_educational_value: bool = True
    
    # Logging and Observability
    enable_langfuse_logging: bool = True
    log_all_interactions: bool = True
    log_blocked_attempts: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_openai_moderation": self.enable_openai_moderation,
            "enable_profanity_filter": self.enable_profanity_filter,
            "content_safety_threshold": self.content_safety_threshold,
            "enable_educational_validation": self.enable_educational_validation,
            "strict_academic_mode": self.strict_academic_mode,
            "allow_general_knowledge": self.allow_general_knowledge,
            "enable_rate_limiting": self.enable_rate_limiting,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_requests_per_hour": self.max_requests_per_hour,
            "max_requests_per_day": self.max_requests_per_day,
            "enable_response_validation": self.enable_response_validation,
            "validate_educational_value": self.validate_educational_value,
            "enable_langfuse_logging": self.enable_langfuse_logging,
            "log_all_interactions": self.log_all_interactions,
            "log_blocked_attempts": self.log_blocked_attempts
        }