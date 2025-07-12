#!/usr/bin/env python3
"""
Example agent demonstrating centralized tools and LLM configuration.

This example shows how to create an agent using:
1. Centralized LLM configuration from environment variables
2. Centralized tools from the tools package
3. Integration with the KG abstraction layer

Run this example to verify your setup is working correctly.
"""

import logging
import asyncio
from typing import List

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from tools import (
    create_default_llm, 
    get_kg_tools, 
    get_utility_tools,
    get_default_llm_config,
    LLMConfigError
)
from tools.registry import ToolRegistry


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LucaExampleAgent:
    """
    Example Luca agent demonstrating best practices for:
    - LLM configuration using environment variables
    - Centralized tool usage
    - Agent creation with LangGraph
    """
    
    def __init__(self, agent_type: str = "tutor"):
        """
        Initialize the example agent.
        
        Args:
            agent_type: Type of agent for tool selection
        """
        self.agent_type = agent_type
        self.llm = None
        self.agent = None
        self.tools = []
        
        self._setup_llm()
        self._setup_tools()
        self._create_agent()
    
    def _setup_llm(self):
        """Setup LLM using environment configuration."""
        try:
            # Get LLM configuration info
            config_info = get_default_llm_config()
            logger.info(f"LLM Configuration: {config_info['provider']} - {config_info['model']}")
            
            # Create LLM instance
            self.llm = create_default_llm()
            logger.info(f"Created LLM: {type(self.llm).__name__}")
            
        except LLMConfigError as e:
            logger.error(f"LLM configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error setting up LLM: {e}")
            raise
    
    def _setup_tools(self):
        """Setup tools using the centralized registry."""
        try:
            registry = ToolRegistry()
            
            # Get tools appropriate for this agent type
            self.tools = registry.get_tools_for_agent(self.agent_type)
            
            tool_names = [tool.name for tool in self.tools]
            logger.info(f"Loaded {len(self.tools)} tools: {tool_names}")
            
            # Log tool categories
            kg_tools = registry.get_tools_by_category(registry.ToolCategory.KNOWLEDGE_GRAPH)
            utility_tools = registry.get_tools_by_category(registry.ToolCategory.UTILITY)
            
            logger.info(f"Available KG tools: {len(kg_tools)}")
            logger.info(f"Available utility tools: {len(utility_tools)}")
            
        except Exception as e:
            logger.error(f"Error setting up tools: {e}")
            raise
    
    def _create_agent(self):
        """Create the LangGraph agent with LLM and tools."""
        try:
            system_prompt = f"""You are a helpful AI tutor for the Luca learning platform.

You have access to a knowledge graph containing course materials, practices, and exercises.
You can help students by:
- Searching for relevant topics and content
- Providing practice exercises and solutions
- Explaining concepts and relationships between topics
- Processing and formatting information

Agent Type: {self.agent_type}
Available Tools: {len(self.tools)} tools

Always be helpful, educational, and encouraging in your responses.
"""
            
            self.agent = create_react_agent(
                self.llm,
                tools=self.tools,
                prompt=system_prompt
            )
            
            logger.info("Agent created successfully")
            
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise
    
    async def chat(self, message: str) -> str:
        """
        Chat with the agent.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        try:
            # Create input for the agent
            inputs = {"messages": [HumanMessage(content=message)]}
            
            # Stream the response
            response_parts = []
            async for chunk in self.agent.astream(inputs):
                if "messages" in chunk:
                    for msg in chunk["messages"]:
                        if hasattr(msg, 'content') and msg.content:
                            response_parts.append(msg.content)
            
            # Return the last message content
            if response_parts:
                return response_parts[-1]
            else:
                return "I couldn't generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Sorry, I encountered an error: {e}"
    
    def chat_sync(self, message: str) -> str:
        """
        Synchronous chat interface.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        try:
            # Create input for the agent
            inputs = {"messages": [HumanMessage(content=message)]}
            
            # Get synchronous response
            result = self.agent.invoke(inputs)
            
            # Extract the last message
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                return last_message.content
            else:
                return "I couldn't generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"Error in sync chat: {e}")
            return f"Sorry, I encountered an error: {e}"
    
    def get_tool_info(self) -> dict:
        """Get information about available tools."""
        registry = ToolRegistry()
        return {
            "agent_type": self.agent_type,
            "total_tools": len(self.tools),
            "tool_names": [tool.name for tool in self.tools],
            "all_available_tools": registry.list_tools()
        }


async def main():
    """Main example function."""
    print("🚀 Luca Example Agent Demo")
    print("=" * 50)
    
    try:
        # Create example agent
        print("Creating agent...")
        agent = LucaExampleAgent(agent_type="tutor")
        
        # Show configuration
        print(f"\n📋 Agent Configuration:")
        tool_info = agent.get_tool_info()
        print(f"Agent Type: {tool_info['agent_type']}")
        print(f"Tools Available: {tool_info['total_tools']}")
        print(f"Tool Names: {', '.join(tool_info['tool_names'][:5])}...")
        
        # Example interactions
        test_messages = [
            "Hello! Can you help me learn about databases?",
            "What subjects are available in the course?",
            "Can you search for information about 'relational model'?",
            "Calculate 15 * 3 + 7",
            "What's the current date and time?"
        ]
        
        print(f"\n💬 Example Conversations:")
        print("-" * 30)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. User: {message}")
            try:
                response = agent.chat_sync(message)
                # Truncate long responses for demo
                if len(response) > 200:
                    response = response[:200] + "..."
                print(f"   Agent: {response}")
            except Exception as e:
                print(f"   Error: {e}")
            
            if i >= 3:  # Limit to first 3 for demo
                break
        
        print(f"\n✅ Demo completed successfully!")
        print(f"\n📝 Next Steps:")
        print("1. Modify .envrc to use different models")
        print("2. Add more tools to the tools package")
        print("3. Create specialized agents for different use cases")
        print("4. Test with your knowledge graph data")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Demo error: {e}", exc_info=True)


def run_sync_demo():
    """Run a simple synchronous demo."""
    print("🔄 Quick Sync Demo")
    
    try:
        agent = LucaExampleAgent(agent_type="general")
        
        response = agent.chat_sync("Hello! What can you help me with?")
        print(f"Agent: {response}")
        
    except Exception as e:
        print(f"Demo error: {e}")


if __name__ == "__main__":
    # Run async demo
    asyncio.run(main())
    
    # Uncomment for quick sync demo:
    # run_sync_demo()