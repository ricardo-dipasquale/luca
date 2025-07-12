"""
Centralized LangChain Tools Package for Luca Agents.

This package provides a shared library of LangChain tools that can be used
across all agents in the Luca project. Tools are organized by category and
follow consistent patterns for easy reuse.

Architecture Benefits:
- Code reuse across multiple agents
- Consistent tool interfaces and error handling
- Centralized maintenance and testing
- Easy tool discovery and documentation
- Shared configuration and connection management

Tool Categories:
- kg_tools: Knowledge Graph interaction tools
- utility_tools: General utility functions
- external_tools: Third-party API integrations

Usage:
    from tools import get_kg_tools, get_utility_tools
    from tools.registry import ToolRegistry
    
    # Get all KG tools
    kg_tools = get_kg_tools()
    
    # Get specific tools by name
    registry = ToolRegistry()
    search_tool = registry.get_tool("search_knowledge_graph")
    
    # Use in agent
    agent = create_react_agent(model, tools=kg_tools + utility_tools)
"""

from .kg_tools import get_kg_tools
from .utility_tools import get_utility_tools
from .registry import ToolRegistry
from .llm_config import create_default_llm, get_default_llm_config, LLMConfigError

__all__ = [
    'get_kg_tools',
    'get_utility_tools', 
    'ToolRegistry',
    'create_default_llm',
    'get_default_llm_config',
    'LLMConfigError'
]