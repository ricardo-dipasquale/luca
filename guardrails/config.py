"""
Guardrails Configuration Management.
"""

import os
import logging
from typing import Dict, Any, Optional
from .schemas import GuardrailConfig

logger = logging.getLogger(__name__)


def load_guardrail_config_from_env() -> GuardrailConfig:
    """
    Load guardrail configuration from environment variables.
    
    Returns:
        GuardrailConfig with settings from environment or defaults
    """
    
    def env_bool(key: str, default: bool) -> bool:
        """Parse boolean from environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def env_int(key: str, default: int) -> int:
        """Parse integer from environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def env_float(key: str, default: float) -> float:
        """Parse float from environment variable."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    # Content safety method selection
    content_safety_method = os.getenv('GUARDRAILS_CONTENT_SAFETY_METHOD', 'llm')
    enable_openai_moderation = content_safety_method == 'moderation_api' or env_bool('GUARDRAILS_ENABLE_OPENAI_MODERATION', False)
    
    config = GuardrailConfig(
        # Content Safety
        enable_openai_moderation=enable_openai_moderation,
        enable_profanity_filter=env_bool('GUARDRAILS_ENABLE_PROFANITY_FILTER', True),
        content_safety_threshold=env_float('GUARDRAILS_CONTENT_SAFETY_THRESHOLD', 0.7),
        content_safety_method=content_safety_method,
        
        # Educational Context
        enable_educational_validation=env_bool('GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION', True),
        strict_academic_mode=env_bool('GUARDRAILS_STRICT_ACADEMIC_MODE', False),
        allow_general_knowledge=env_bool('GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE', True),
        
        # Rate Limiting
        enable_rate_limiting=env_bool('GUARDRAILS_ENABLE_RATE_LIMITING', True),
        max_requests_per_minute=env_int('GUARDRAILS_MAX_REQUESTS_PER_MINUTE', 30),
        max_requests_per_hour=env_int('GUARDRAILS_MAX_REQUESTS_PER_HOUR', 200),
        max_requests_per_day=env_int('GUARDRAILS_MAX_REQUESTS_PER_DAY', 1000),
        
        # Response Validation
        enable_response_validation=env_bool('GUARDRAILS_ENABLE_RESPONSE_VALIDATION', True),
        validate_educational_value=env_bool('GUARDRAILS_VALIDATE_EDUCATIONAL_VALUE', True),
        
        # Logging and Observability
        enable_langfuse_logging=env_bool('GUARDRAILS_ENABLE_LANGFUSE_LOGGING', True),
        log_all_interactions=env_bool('GUARDRAILS_LOG_ALL_INTERACTIONS', True),
        log_blocked_attempts=env_bool('GUARDRAILS_LOG_BLOCKED_ATTEMPTS', True)
    )
    
    logger.info("Guardrail configuration loaded from environment variables")
    return config


def get_development_config() -> GuardrailConfig:
    """
    Get development configuration with relaxed settings.
    
    Returns:
        GuardrailConfig suitable for development
    """
    return GuardrailConfig(
        # More permissive for development
        enable_openai_moderation=False,  # Use LLM method for development
        enable_profanity_filter=True,
        content_safety_threshold=0.8,  # Higher threshold = more permissive
        content_safety_method="llm",  # Use LLM method for development
        
        enable_educational_validation=True,
        strict_academic_mode=False,  # Allow flexibility
        allow_general_knowledge=True,
        
        # Higher rate limits for development
        enable_rate_limiting=True,
        max_requests_per_minute=60,
        max_requests_per_hour=500,
        max_requests_per_day=2000,
        
        enable_response_validation=True,
        validate_educational_value=False,  # Disabled for dev to avoid blocking
        
        enable_langfuse_logging=True,
        log_all_interactions=True,
        log_blocked_attempts=True
    )


def get_production_config() -> GuardrailConfig:
    """
    Get production configuration with strict settings.
    
    Returns:
        GuardrailConfig suitable for production
    """
    return GuardrailConfig(
        # Strict settings for production
        enable_openai_moderation=False,  # Use LLM method for production (from env)
        enable_profanity_filter=True,
        content_safety_threshold=0.6,  # Lower threshold = more strict
        content_safety_method="llm",  # Use LLM method for production
        
        enable_educational_validation=True,
        strict_academic_mode=True,  # Enforce academic focus
        allow_general_knowledge=False,  # Only curriculum-related content
        
        # Standard rate limits for production
        enable_rate_limiting=True,
        max_requests_per_minute=20,
        max_requests_per_hour=100,
        max_requests_per_day=500,
        
        enable_response_validation=True,
        validate_educational_value=True,
        
        enable_langfuse_logging=True,
        log_all_interactions=True,
        log_blocked_attempts=True
    )


def get_testing_config() -> GuardrailConfig:
    """
    Get testing configuration with minimal restrictions.
    
    Returns:
        GuardrailConfig suitable for testing
    """
    return GuardrailConfig(
        # Minimal restrictions for testing
        enable_openai_moderation=False,  # Disabled to avoid API costs in tests
        enable_profanity_filter=True,
        content_safety_threshold=0.9,
        content_safety_method="llm",  # Use LLM method for testing
        
        enable_educational_validation=True,
        strict_academic_mode=False,
        allow_general_knowledge=True,
        
        # Very high limits for testing
        enable_rate_limiting=False,  # Disabled for testing
        max_requests_per_minute=1000,
        max_requests_per_hour=10000,
        max_requests_per_day=50000,
        
        enable_response_validation=False,  # Disabled to speed up tests
        validate_educational_value=False,
        
        enable_langfuse_logging=False,  # Disabled to avoid test noise
        log_all_interactions=False,
        log_blocked_attempts=True  # Keep this for debugging test failures
    )


def create_config_for_environment(env: str = None) -> GuardrailConfig:
    """
    Create configuration based on environment.
    
    Args:
        env: Environment name (development, production, testing) or None for auto-detect
        
    Returns:
        GuardrailConfig appropriate for the environment
    """
    if env is None:
        # Auto-detect environment
        env = os.getenv('ENVIRONMENT', os.getenv('NODE_ENV', 'development')).lower()
    
    env = env.lower()
    
    if env in ('prod', 'production'):
        logger.info("Loading production guardrail configuration")
        return get_production_config()
    elif env in ('test', 'testing'):
        logger.info("Loading testing guardrail configuration")  
        return get_testing_config()
    elif env in ('dev', 'development'):
        logger.info("Loading development guardrail configuration")
        return get_development_config()
    else:
        logger.info("Loading guardrail configuration from environment variables")
        return load_guardrail_config_from_env()


# Environment variable documentation
GUARDRAIL_ENV_VARS = {
    # Content Safety
    'GUARDRAILS_CONTENT_SAFETY_METHOD': 'Content safety method: "moderation_api" or "llm"',
    'GUARDRAILS_ENABLE_OPENAI_MODERATION': 'Enable OpenAI Moderation API (true/false)',
    'GUARDRAILS_ENABLE_PROFANITY_FILTER': 'Enable profanity filtering (true/false)',
    'GUARDRAILS_CONTENT_SAFETY_THRESHOLD': 'Content safety threshold (0.0-1.0)',
    
    # Educational Context
    'GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION': 'Enable educational validation (true/false)',
    'GUARDRAILS_STRICT_ACADEMIC_MODE': 'Strict academic mode (true/false)',
    'GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE': 'Allow general knowledge questions (true/false)',
    
    # Rate Limiting
    'GUARDRAILS_ENABLE_RATE_LIMITING': 'Enable rate limiting (true/false)',
    'GUARDRAILS_MAX_REQUESTS_PER_MINUTE': 'Max requests per minute (integer)',
    'GUARDRAILS_MAX_REQUESTS_PER_HOUR': 'Max requests per hour (integer)',
    'GUARDRAILS_MAX_REQUESTS_PER_DAY': 'Max requests per day (integer)',
    
    # Response Validation
    'GUARDRAILS_ENABLE_RESPONSE_VALIDATION': 'Enable response validation (true/false)',
    'GUARDRAILS_VALIDATE_EDUCATIONAL_VALUE': 'Validate educational value (true/false)',
    
    # Logging
    'GUARDRAILS_ENABLE_LANGFUSE_LOGGING': 'Enable Langfuse logging (true/false)',
    'GUARDRAILS_LOG_ALL_INTERACTIONS': 'Log all interactions (true/false)',
    'GUARDRAILS_LOG_BLOCKED_ATTEMPTS': 'Log blocked attempts (true/false)'
}


def print_config_help():
    """Print help information about guardrail configuration."""
    print("Guardrails Configuration Environment Variables:")
    print("=" * 50)
    for var, description in GUARDRAIL_ENV_VARS.items():
        print(f"{var:<45} {description}")
    print("\nEnvironment Detection:")
    print("ENVIRONMENT or NODE_ENV can be set to: development, production, testing")
    print("\nExample .envrc configuration:")
    print("export GUARDRAILS_ENABLE_OPENAI_MODERATION=true")
    print("export GUARDRAILS_STRICT_ACADEMIC_MODE=false")
    print("export GUARDRAILS_MAX_REQUESTS_PER_MINUTE=30")