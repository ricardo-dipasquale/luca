"""
LLM configuration utilities for Luca agents.

This module provides standardized LLM configuration using environment variables,
ensuring consistent model setup across all agents while maintaining flexibility
for different use cases.
"""

import os
import logging
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel


logger = logging.getLogger(__name__)


class LLMConfigError(Exception):
    """Exception for LLM configuration errors."""
    pass


def get_default_llm_config() -> Dict[str, Any]:
    """
    Get default LLM configuration from environment variables.
    
    Returns:
        Dictionary with LLM configuration parameters
        
    Raises:
        LLMConfigError: If required environment variables are missing
    """
    config = {
        "model": os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
        "provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        "temperature": float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1")),
        "api_key": None,
        "max_tokens": int(os.getenv("DEFAULT_LLM_MAX_TOKENS", "4096")),
        "timeout": int(os.getenv("DEFAULT_LLM_TIMEOUT", "60"))
    }
    
    # Get provider-specific API key
    if config["provider"] == "openai":
        config["api_key"] = os.getenv("OPENAI_API_KEY")
        if not config["api_key"]:
            raise LLMConfigError("OPENAI_API_KEY environment variable is required for OpenAI provider")
    
    elif config["provider"] == "anthropic":
        config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if not config["api_key"]:
            raise LLMConfigError("ANTHROPIC_API_KEY environment variable is required for Anthropic provider")
    
    else:
        raise LLMConfigError(f"Unsupported LLM provider: {config['provider']}. Supported providers: openai, anthropic")
    
    return config


def create_default_llm(**kwargs) -> BaseLanguageModel:
    """
    Create a default LLM instance using environment configuration.
    
    Args:
        **kwargs: Override parameters for LLM configuration
        
    Returns:
        Configured LLM instance compatible with LangChain/LangGraph
        
    Raises:
        LLMConfigError: If configuration is invalid or provider not supported
    """
    try:
        config = get_default_llm_config()
        
        # Override with provided kwargs
        config.update(kwargs)
        
        provider = config["provider"].lower()
        
        if provider == "openai":
            return ChatOpenAI(
                model=config["model"],
                api_key=config["api_key"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                timeout=config["timeout"]
            )
        
        else:
            raise LLMConfigError(f"Unsupported LLM provider: {provider}. Only 'openai' is currently supported.")
    
    except Exception as e:
        logger.error(f"Failed to create LLM: {e}")
        raise LLMConfigError(f"LLM creation failed: {e}") from e


def create_openai_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Create an OpenAI LLM with default configuration.
    
    Args:
        model: OpenAI model name (defaults to DEFAULT_LLM_MODEL)
        temperature: Model temperature (defaults to DEFAULT_LLM_TEMPERATURE)
        **kwargs: Additional parameters for ChatOpenAI
        
    Returns:
        Configured ChatOpenAI instance
    """
    config = get_default_llm_config()
    
    return ChatOpenAI(
        model=model or config["model"],
        api_key=config["api_key"],
        temperature=temperature if temperature is not None else config["temperature"],
        max_tokens=config["max_tokens"],
        timeout=config["timeout"],
        **kwargs
    )




def get_available_models() -> Dict[str, list]:
    """
    Get information about available models for each provider.
    
    Returns:
        Dictionary mapping providers to their available models
    """
    return {
        "openai": [
            "gpt-4o",           # Most capable model
            "gpt-4o-mini",      # Efficient, fast model (recommended default)
            "gpt-4-turbo",      # High performance model
            "gpt-3.5-turbo",    # Legacy efficient model
        ]
    }


def validate_model_compatibility(provider: str, model: str) -> bool:
    """
    Validate that a model is compatible with LangChain/LangGraph.
    
    Args:
        provider: LLM provider name
        model: Model name to validate
        
    Returns:
        True if model is supported, False otherwise
    """
    available = get_available_models()
    provider_models = available.get(provider.lower(), [])
    
    return model in provider_models


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the currently configured default model.
    
    Returns:
        Dictionary with model information and compatibility status
    """
    try:
        config = get_default_llm_config()
        
        is_compatible = validate_model_compatibility(
            config["provider"], 
            config["model"]
        )
        
        return {
            "provider": config["provider"],
            "model": config["model"],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "is_compatible": is_compatible,
            "api_key_configured": bool(config["api_key"]),
            "recommended_for": get_model_recommendations(config["model"])
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "is_compatible": False
        }


def get_model_recommendations(model: str) -> list:
    """
    Get recommendations for model usage.
    
    Args:
        model: Model name
        
    Returns:
        List of recommended use cases
    """
    recommendations = {
        "gpt-4o-mini": [
            "Educational tutoring",
            "Practice exercises",
            "General Q&A",
            "Cost-effective development"
        ],
        "gpt-4o": [
            "Complex reasoning tasks",
            "Advanced problem solving",
            "Research assistance",
            "Production applications"
        ],
        "gpt-4-turbo": [
            "Fast response requirements",
            "Balanced cost/performance",
            "Multi-turn conversations"
        ],
        "gpt-3.5-turbo": [
            "Legacy applications",
            "Simple Q&A tasks",
            "Budget-conscious development"
        ]
    }
    
    return recommendations.get(model, ["General purpose"])


# Example usage and compatibility verification
if __name__ == "__main__":
    """
    Example usage of LLM configuration utilities.
    """
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Get model info
        info = get_model_info()
        print(f"Current model configuration: {info}")
        
        # Create default LLM
        llm = create_default_llm()
        print(f"Created LLM: {type(llm).__name__}")
        
        # Test compatibility
        models = get_available_models()
        print(f"Available models: {models}")
        
        # Verify gpt-4o-mini compatibility
        is_compatible = validate_model_compatibility("openai", "gpt-4o-mini")
        print(f"gpt-4o-mini compatibility: {is_compatible}")
        
    except LLMConfigError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")