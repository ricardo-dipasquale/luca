"""
Tool registry and factory pattern for centralized tool management.

This module provides a registry system for discovering, configuring, and
accessing tools across different agents in the Luca project.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from enum import Enum

from .kg_tools import get_kg_tools
from .utility_tools import get_utility_tools


logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of available tools."""
    KNOWLEDGE_GRAPH = "kg"
    UTILITY = "utility"
    EXTERNAL = "external"
    ALL = "all"


@dataclass
class ToolInfo:
    """Information about a registered tool."""
    name: str
    category: ToolCategory
    description: str
    tool_function: Callable
    requires_connection: bool = False
    is_safe: bool = True  # Whether tool is safe for all agents


class ToolRegistry:
    """
    Registry for managing and providing access to LangChain tools.
    
    This registry allows agents to discover available tools, get tools by
    category or name, and manage tool configurations.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, ToolInfo] = {}
        self._initialize_tools()
    
    def _initialize_tools(self) -> None:
        """Initialize the registry with available tools."""
        logger.info("Initializing tool registry")
        
        # Register KG tools
        kg_tools = get_kg_tools()
        for tool in kg_tools:
            self._register_tool(
                tool=tool,
                category=ToolCategory.KNOWLEDGE_GRAPH,
                requires_connection=True
            )
        
        # Register utility tools
        utility_tools = get_utility_tools()
        for tool in utility_tools:
            self._register_tool(
                tool=tool,
                category=ToolCategory.UTILITY,
                requires_connection=False
            )
        
        logger.info(f"Registered {len(self._tools)} tools")
    
    def _register_tool(
        self,
        tool: Callable,
        category: ToolCategory,
        requires_connection: bool = False,
        is_safe: bool = True
    ) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: The tool function
            category: Category of the tool
            requires_connection: Whether tool requires external connections
            is_safe: Whether tool is safe for all agents
        """
        tool_name = tool.name
        description = tool.description or "No description available"
        
        tool_info = ToolInfo(
            name=tool_name,
            category=category,
            description=description,
            tool_function=tool,
            requires_connection=requires_connection,
            is_safe=is_safe
        )
        
        self._tools[tool_name] = tool_info
        logger.debug(f"Registered tool: {tool_name} ({category.value})")
    
    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """
        Get a specific tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Tool function if found, None otherwise
        """
        tool_info = self._tools.get(tool_name)
        return tool_info.tool_function if tool_info else None
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Callable]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of tool functions in the category
        """
        if category == ToolCategory.ALL:
            return [info.tool_function for info in self._tools.values()]
        
        return [
            info.tool_function 
            for info in self._tools.values() 
            if info.category == category
        ]
    
    def get_safe_tools(self) -> List[Callable]:
        """
        Get all tools marked as safe for general use.
        
        Returns:
            List of safe tool functions
        """
        return [
            info.tool_function 
            for info in self._tools.values() 
            if info.is_safe
        ]
    
    def get_tools_for_agent(
        self,
        agent_type: str,
        include_categories: Optional[List[ToolCategory]] = None,
        exclude_tools: Optional[List[str]] = None
    ) -> List[Callable]:
        """
        Get tools appropriate for a specific agent type.
        
        Args:
            agent_type: Type of agent (e.g., "tutor", "practice_helper", "general")
            include_categories: Categories to include (default: all)
            exclude_tools: Specific tools to exclude by name
            
        Returns:
            List of appropriate tool functions
        """
        if include_categories is None:
            include_categories = [ToolCategory.KNOWLEDGE_GRAPH, ToolCategory.UTILITY]
        
        exclude_tools = exclude_tools or []
        
        tools = []
        for info in self._tools.values():
            # Check category
            if info.category not in include_categories:
                continue
            
            # Check exclusions
            if info.name in exclude_tools:
                continue
            
            # Agent-specific logic
            if agent_type == "practice_helper":
                # Practice helpers might want all KG tools
                tools.append(info.tool_function)
            elif agent_type == "tutor":
                # Tutors might want safe tools only
                if info.is_safe:
                    tools.append(info.tool_function)
            elif agent_type == "general":
                # General agents get safe, non-connection tools
                if info.is_safe and not info.requires_connection:
                    tools.append(info.tool_function)
            else:
                # Default: safe tools only
                if info.is_safe:
                    tools.append(info.tool_function)
        
        logger.info(f"Selected {len(tools)} tools for agent type: {agent_type}")
        return tools
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all available tools with their information.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dictionary mapping tool names to their information
        """
        tools_info = {}
        
        for tool_name, tool_info in self._tools.items():
            if category and tool_info.category != category:
                continue
            
            tools_info[tool_name] = {
                "category": tool_info.category.value,
                "description": tool_info.description,
                "requires_connection": tool_info.requires_connection,
                "is_safe": tool_info.is_safe
            }
        
        return tools_info
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary or None if not found
        """
        tool_info = self._tools.get(tool_name)
        if not tool_info:
            return None
        
        return {
            "name": tool_info.name,
            "category": tool_info.category.value,
            "description": tool_info.description,
            "requires_connection": tool_info.requires_connection,
            "is_safe": tool_info.is_safe,
            "schema": getattr(tool_info.tool_function, 'args_schema', None)
        }
    
    def validate_tools_available(self, required_tools: List[str]) -> Dict[str, bool]:
        """
        Validate that required tools are available.
        
        Args:
            required_tools: List of tool names to check
            
        Returns:
            Dictionary mapping tool names to availability status
        """
        availability = {}
        for tool_name in required_tools:
            availability[tool_name] = tool_name in self._tools
        
        return availability
    
    def get_tool_dependencies(self) -> Dict[str, List[str]]:
        """
        Get tool dependencies (which tools require connections, etc.).
        
        Returns:
            Dictionary mapping dependency types to tool names
        """
        dependencies = {
            "requires_kg_connection": [],
            "requires_external_api": [],
            "safe_offline": []
        }
        
        for tool_name, tool_info in self._tools.items():
            if tool_info.category == ToolCategory.KNOWLEDGE_GRAPH:
                dependencies["requires_kg_connection"].append(tool_name)
            elif tool_info.category == ToolCategory.EXTERNAL:
                dependencies["requires_external_api"].append(tool_name)
            
            if not tool_info.requires_connection:
                dependencies["safe_offline"].append(tool_name)
        
        return dependencies


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        ToolRegistry: Global registry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


# Convenience functions for common use cases
def get_all_tools() -> List[Callable]:
    """Get all available tools."""
    return get_registry().get_tools_by_category(ToolCategory.ALL)


def get_kg_tools_from_registry() -> List[Callable]:
    """Get all knowledge graph tools."""
    return get_registry().get_tools_by_category(ToolCategory.KNOWLEDGE_GRAPH)


def get_utility_tools_from_registry() -> List[Callable]:
    """Get all utility tools."""
    return get_registry().get_tools_by_category(ToolCategory.UTILITY)


def get_tutor_tools() -> List[Callable]:
    """Get tools appropriate for tutor agents."""
    return get_registry().get_tools_for_agent("tutor")


def get_practice_helper_tools() -> List[Callable]:
    """Get tools appropriate for practice helper agents."""
    return get_registry().get_tools_for_agent("practice_helper")


def get_safe_tools() -> List[Callable]:
    """Get all tools marked as safe."""
    return get_registry().get_safe_tools()