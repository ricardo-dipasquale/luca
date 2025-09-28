"""
Observability module for LLM calls using Langfuse.

This module provides centralized observability for all LLM interactions
across the Luca project, enabling monitoring, debugging, and analytics.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from functools import wraps
import threading

logger = logging.getLogger(__name__)

# Global Langfuse client (lazy loaded)
_langfuse_client: Optional[object] = None
_client_lock = threading.Lock()


def get_langfuse_client():
    """
    Get or create a shared Langfuse client instance.

    Returns:
        Langfuse client instance or None if not configured or disabled
    """
    global _langfuse_client

    # Check if Langfuse is explicitly disabled
    langfuse_enabled = os.getenv('LANGFUSE_ENABLED', 'true').lower() in ('true', '1', 'yes', 'on')

    if not langfuse_enabled:
        logger.info("Langfuse observability is disabled by LANGFUSE_ENABLED environment variable")
        return None

    if _langfuse_client is None:
        with _client_lock:
            if _langfuse_client is None:
                try:
                    from langfuse import Langfuse

                    # Get configuration from environment
                    host = os.getenv('LANGFUSE_HOST')
                    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
                    secret_key = os.getenv('LANGFUSE_SECRET_KEY')

                    if not all([host, public_key, secret_key]):
                        logger.warning("Langfuse not configured - missing environment variables (LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)")
                        return None

                    _langfuse_client = Langfuse(
                        host=host,
                        public_key=public_key,
                        secret_key=secret_key
                    )

                    logger.info("Langfuse client initialized successfully")

                except ImportError:
                    logger.warning("Langfuse not available - install langfuse package")
                    return None
                except Exception as e:
                    logger.error(f"Failed to initialize Langfuse client: {e}")
                    return None

    return _langfuse_client


def is_langfuse_enabled() -> bool:
    """
    Check if Langfuse observability is enabled.

    Returns:
        bool: True if Langfuse is enabled and configured, False otherwise
    """
    langfuse_enabled = os.getenv('LANGFUSE_ENABLED', 'true').lower() in ('true', '1', 'yes', 'on')

    if not langfuse_enabled:
        return False

    # Also check if we have the required configuration
    host = os.getenv('LANGFUSE_HOST')
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')

    return all([host, public_key, secret_key])


def observe_llm_call(
    name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
):
    """
    Decorator to observe LLM calls with Langfuse.
    
    Args:
        name: Name of the operation (e.g., "gap_analysis", "theoretical_content")
        session_id: Optional session ID for grouping related calls
        user_id: Optional user ID for tracking per-user usage
        metadata: Optional metadata dictionary
        tags: Optional list of tags for categorization
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = get_langfuse_client()
            
            if not client:
                # If Langfuse not available, just execute the function
                return await func(*args, **kwargs)
            
            # Create trace
            trace = client.trace(
                name=name,
                session_id=session_id or f"thread_{threading.current_thread().ident}",
                user_id=user_id,
                metadata=metadata or {},
                tags=tags or []
            )
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Mark trace as successful
                trace.update(
                    output={"result": str(result)[:1000]},  # Limit output size
                    status_message="success"
                )
                
                return result
                
            except Exception as e:
                # Mark trace as failed
                trace.update(
                    output={"error": str(e)},
                    status_message="error"
                )
                raise
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            client = get_langfuse_client()
            
            if not client:
                # If Langfuse not available, just execute the function
                return func(*args, **kwargs)
            
            # Create trace
            trace = client.trace(
                name=name,
                session_id=session_id or f"thread_{threading.current_thread().ident}",
                user_id=user_id,
                metadata=metadata or {},
                tags=tags or []
            )
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Mark trace as successful
                trace.update(
                    output={"result": str(result)[:1000]},  # Limit output size
                    status_message="success"
                )
                
                return result
                
            except Exception as e:
                # Mark trace as failed
                trace.update(
                    output={"error": str(e)},
                    status_message="error"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def observe_openai_call(
    client,
    messages: List[Dict[str, str]],
    model: str,
    operation_name: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Create an observed OpenAI chat completion call using Langfuse OpenAI integration.
    
    Args:
        client: OpenAI client instance
        messages: Chat messages
        model: Model name
        operation_name: Name of the operation for tracking
        session_id: Optional session ID
        metadata: Optional metadata
        **kwargs: Additional arguments for OpenAI API
        
    Returns:
        OpenAI response with Langfuse observability
    """
    langfuse_client = get_langfuse_client()
    
    if not langfuse_client:
        # If Langfuse not available, make regular call
        logger.debug("Langfuse not available, making unobserved OpenAI call")
        return client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    # Use Langfuse OpenAI integration for automatic tracing
    try:
        from langfuse.openai import openai as langfuse_openai
        
        # Create an observed OpenAI client (no session_id in constructor)
        observed_client = langfuse_openai.OpenAI(
            api_key=client.api_key
        )
        
        # Make the call with automatic observability, including session and metadata
        response = observed_client.chat.completions.create(
            model=model,
            messages=messages,
            langfuse_session_id=session_id or f"thread_{threading.current_thread().ident}",
            langfuse_metadata={
                "operation": operation_name,
                **(metadata or {})
            },
            **kwargs
        )
        
        logger.info(f"Successfully made observed OpenAI call for {operation_name}")
        return response
        
    except ImportError:
        logger.warning("Langfuse OpenAI integration not available, making unobserved call")
        return client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error in observed OpenAI call: {e}, falling back to unobserved")
        # Fallback to regular call
        return client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )


def observe_tool_call(
    tool_name: str,
    input_data: Dict[str, Any],
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Create observability for tool calls.
    
    Args:
        tool_name: Name of the tool being called
        input_data: Input data for the tool
        session_id: Optional session ID
        metadata: Optional metadata
        
    Returns:
        Context manager for tool call observability
    """
    client = get_langfuse_client()
    
    if not client:
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext()
    
    class ToolObservationContext:
        def __init__(self):
            # Create trace ID and start span for tool call
            self.trace_id = client.create_trace_id()
            self.session_id = session_id or f"thread_{threading.current_thread().ident}"
            
            self.span = client.start_span(
                name=f"tool_{tool_name}",
                trace_id=self.trace_id,
                session_id=self.session_id,
                input=input_data,
                metadata={
                    "tool": tool_name,
                    **(metadata or {})
                }
            )
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                client.update_current_span(
                    output={"error": str(exc_val)},
                    metadata={"status": "error"}
                )
            else:
                client.update_current_span(metadata={"status": "success"})
        
        def set_output(self, output: Any):
            """Set the output of the tool call."""
            client.update_current_span(output={"result": str(output)[:1000]})
    
    return ToolObservationContext()


def create_observed_llm():
    """
    Create an observed LLM that automatically traces all interactions with Langfuse.
    
    Returns:
        LLM with automatic Langfuse observability, or regular LLM as fallback
    """
    from tools.llm_config import LLMConfigError
    
    try:
        from langfuse.langchain import CallbackHandler
        
        client = get_langfuse_client()
        
        if not client:
            # If Langfuse not available, return regular LLM
            logger.warning("Langfuse not available, returning unobserved LLM")
            from tools.llm_config import create_default_llm
            return create_default_llm()
        
        # Create Langfuse callback handler - it will auto-configure from environment
        langfuse_handler = CallbackHandler()
        
        # Try to create LLM with callback
        from tools.llm_config import create_default_llm
        llm = create_default_llm(callbacks=[langfuse_handler])
        
        logger.info("Created observed LLM with Langfuse integration")
        return llm
        
    except ImportError as e:
        logger.warning(f"Langfuse callback handler not available: {e}, returning unobserved LLM")
        from tools.llm_config import create_default_llm
        return create_default_llm()
    except LLMConfigError as e:
        logger.warning(f"LLM configuration error: {e}, trying simple LLM creation")
        # Try creating LLM without callbacks as fallback
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1"))
            )
        except Exception as fallback_error:
            logger.error(f"Even simple LLM creation failed: {fallback_error}")
            raise LLMConfigError(f"Cannot create any LLM: {fallback_error}")
    except Exception as e:
        logger.error(f"Unexpected error creating observed LLM: {e}, falling back to simple LLM")
        # Final fallback - create basic LLM
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1"))
            )
        except Exception as fallback_error:
            logger.error(f"Final fallback LLM creation failed: {fallback_error}")
            raise


def flush_langfuse():
    """
    Flush pending Langfuse events.
    Should be called before application shutdown.
    """
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            logger.info("Langfuse events flushed successfully")
        except Exception as e:
            logger.error(f"Error flushing Langfuse events: {e}")