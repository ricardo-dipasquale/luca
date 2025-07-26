"""
Test client for Orchestrator Agent.

This script demonstrates how to test the orchestrator agent both locally
and through the A2A framework, including conversation management and
multi-turn interactions.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

from .agent_executor import OrchestratorAgentExecutor
from .schemas import ConversationContext, ConversationMemory, EducationalContext


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrchestratorTestClient:
    """Test client for Orchestrator Agent."""
    
    def __init__(self):
        """Initialize the test client."""
        try:
            self.executor = OrchestratorAgentExecutor()
            logger.info("Orchestrator test client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize test client: {e}")
            raise
    
    async def test_single_message(self, message: str, session_id: str = "test_session") -> Dict[str, Any]:
        """
        Test orchestrator with a single message.
        
        Args:
            message: Test message
            session_id: Session identifier
            
        Returns:
            Final response from orchestrator
        """
        print(f"\\n=== TESTING SINGLE MESSAGE ===")
        print(f"Message: {message}")
        print(f"Session: {session_id}")
        print("-" * 50)
        
        try:
            final_response = None
            
            # Stream the response
            async for chunk in self.executor.stream(
                request={'message': message},
                context={'session_id': session_id, 'user_id': 'test_user'}
            ):
                if chunk.get('is_task_complete'):
                    final_response = chunk
                    print(f"✅ Final: {chunk.get('content', 'No content')}")
                else:
                    print(f"🔄 Progress: {chunk.get('content', 'Processing...')}")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in single message test: {e}")
            return {"error": str(e)}
    
    async def test_conversation_flow(self, messages: List[str], session_id: str = "conversation_test") -> List[Dict[str, Any]]:
        """
        Test a multi-turn conversation.
        
        Args:
            messages: List of messages to send in sequence
            session_id: Session identifier
            
        Returns:
            List of responses
        """
        print(f"\\n=== TESTING CONVERSATION FLOW ===")
        print(f"Messages: {len(messages)}")
        print(f"Session: {session_id}")
        print("-" * 50)
        
        responses = []
        
        for i, message in enumerate(messages, 1):
            print(f"\\n--- Turn {i} ---")
            print(f"Student: {message}")
            
            try:
                # Send message and get response
                final_response = None
                async for chunk in self.executor.stream(
                    request={'message': message},
                    context={'session_id': session_id, 'user_id': 'test_user'}
                ):
                    if chunk.get('is_task_complete'):
                        final_response = chunk
                        print(f"Assistant: {chunk.get('content', 'No content')}")
                        break
                    else:
                        print(f"🔄 {chunk.get('content', 'Processing...')}")
                
                responses.append(final_response)
                
                # Show conversation state
                session_info = self.executor.get_session_info(session_id)
                if 'error' not in session_info:
                    edu_ctx = session_info.get('educational_context', {})
                    print(f"📚 Context: Subject={edu_ctx.get('current_subject')}, Practice={edu_ctx.get('current_practice')}")
                    if edu_ctx.get('topics_discussed'):
                        print(f"📝 Topics: {', '.join(edu_ctx.get('topics_discussed', []))}")
                
            except Exception as e:
                logger.error(f"Error in conversation turn {i}: {e}")
                responses.append({"error": str(e)})
        
        return responses
    
    async def test_intent_classification(self):
        """Test various types of student intents."""
        print(f"\\n=== TESTING INTENT CLASSIFICATION ===")
        print("-" * 50)
        
        test_cases = [
            ("¿Qué es un LEFT JOIN?", "theoretical_question"),
            ("Mi consulta SQL no funciona", "practical_help"),
            ("No entiendo por qué mi código da error", "gap_analysis"),
            ("¿Podrías explicar mejor lo anterior?", "clarification"),
            ("¿Qué otros tipos de JOIN existen?", "exploration"),
            ("Hola, necesito ayuda", "greeting"),
            ("¿Cómo está el clima hoy?", "off_topic")
        ]
        
        results = []
        
        for message, expected_intent in test_cases:
            print(f"\\nTesting: {message}")
            print(f"Expected: {expected_intent}")
            
            try:
                response = await self.test_single_message(message, f"intent_test_{len(results)}")
                
                # Extract intent from structured response
                structured = response.get('structured_response', {}) if response else {}
                detected_intent = structured.get('intent', 'unknown')
                
                print(f"Detected: {detected_intent}")
                
                # Check if correct
                is_correct = detected_intent == expected_intent
                print(f"Result: {'✅ PASS' if is_correct else '❌ FAIL'}")
                
                results.append({
                    'message': message,
                    'expected': expected_intent,
                    'detected': detected_intent,
                    'correct': is_correct
                })
                
            except Exception as e:
                logger.error(f"Error testing intent for '{message}': {e}")
                results.append({
                    'message': message,
                    'expected': expected_intent,
                    'error': str(e)
                })
        
        # Summary
        correct_count = sum(1 for r in results if r.get('correct'))
        total_count = len([r for r in results if 'error' not in r])
        
        print(f"\\n📊 Intent Classification Results:")
        print(f"   Correct: {correct_count}/{total_count} ({correct_count/total_count*100:.1f}%)")
        
        return results
    
    async def test_gap_analyzer_integration(self):
        """Test integration with GapAnalyzer."""
        print(f"\\n=== TESTING GAP ANALYZER INTEGRATION ===")
        print("-" * 50)
        
        # Messages that should trigger gap analysis
        gap_analysis_messages = [
            "No entiendo por qué mi consulta LEFT JOIN no devuelve los resultados esperados",
            "Mi código SQL da error y no sé qué está mal",
            "¿Por qué salen registros duplicados en mi consulta?"
        ]
        
        for message in gap_analysis_messages:
            print(f"\\nTesting: {message}")
            
            try:
                response = await self.test_single_message(message, "gap_test")
                
                # Check if GapAnalyzer was called
                structured = response.get('structured_response', {}) if response else {}
                routing_agent = structured.get('routing_agent')
                
                print(f"Routing: {routing_agent}")
                
                if routing_agent == "gap_analyzer":
                    print("✅ Successfully routed to GapAnalyzer")
                else:
                    print(f"❌ Expected gap_analyzer, got {routing_agent}")
                    
            except Exception as e:
                logger.error(f"Error testing gap integration: {e}")
    
    async def test_session_management(self):
        """Test session management functionality."""
        print(f"\\n=== TESTING SESSION MANAGEMENT ===")
        print("-" * 50)
        
        session_id = "session_mgmt_test"
        
        # Send a few messages to build up session state
        messages = [
            "Hola, estoy estudiando bases de datos",
            "Estoy trabajando en la práctica 2",
            "Tengo dudas sobre SQL JOINs"
        ]
        
        for message in messages:
            await self.test_single_message(message, session_id)
        
        # Get session info
        session_info = self.executor.get_session_info(session_id)
        
        print(f"\\n📋 Session Information:")
        print(f"   Session ID: {session_info.get('session_id')}")
        print(f"   Messages: {session_info.get('message_count')}")
        print(f"   Subject: {session_info.get('educational_context', {}).get('current_subject')}")
        print(f"   Practice: {session_info.get('educational_context', {}).get('current_practice')}")
        print(f"   Topics: {session_info.get('educational_context', {}).get('topics_discussed')}")
        print(f"   Intents: {session_info.get('recent_intents')}")
        
        return session_info
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent card information."""
        print(f"\\n=== AGENT CARD ===")
        print("-" * 50)
        
        card = self.executor.get_agent_card()
        
        print(f"Name: {card.get('name')}")
        print(f"Version: {card.get('version')}")
        print(f"Description: {card.get('description')}")
        print(f"\\nCapabilities:")
        for capability in card.get('capabilities', []):
            print(f"  • {capability}")
        
        print(f"\\nUse Cases:")
        for use_case in card.get('use_cases', []):
            print(f"  • {use_case}")
        
        return card


async def run_comprehensive_tests():
    """Run comprehensive test suite."""
    try:
        print("🧪 Starting Orchestrator Agent Tests")
        print("=" * 60)
        
        client = OrchestratorTestClient()
        
        # Test 1: Single message
        await client.test_single_message("¿Qué es normalización en bases de datos?")
        
        # Test 2: Conversation flow
        conversation = [
            "Hola, necesito ayuda con bases de datos",
            "Estoy trabajando en la práctica 2 de SQL",
            "No entiendo cómo funciona el LEFT JOIN",
            "¿Podrías darme un ejemplo práctico?"
        ]
        await client.test_conversation_flow(conversation)
        
        # Test 3: Intent classification
        await client.test_intent_classification()
        
        # Test 4: GapAnalyzer integration
        await client.test_gap_analyzer_integration()
        
        # Test 5: Session management
        await client.test_session_management()
        
        # Test 6: Agent card
        client.get_agent_card()
        
        print("\\n🎉 All tests completed!")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        print(f"❌ Test suite failed: {e}")


async def run_interactive_test():
    """Run interactive test mode."""
    try:
        print("🎮 Interactive Orchestrator Test Mode")
        print("Type 'quit' to exit, 'session' for session info")
        print("-" * 50)
        
        client = OrchestratorTestClient()
        session_id = "interactive_session"
        
        while True:
            try:
                message = input("\\nYou: ").strip()
                
                if message.lower() in ['quit', 'exit']:
                    break
                elif message.lower() == 'session':
                    session_info = client.executor.get_session_info(session_id)
                    print(f"Session: {json.dumps(session_info, indent=2, default=str)}")
                    continue
                elif not message:
                    continue
                
                # Send message to orchestrator
                print("Assistant: ", end="", flush=True)
                
                async for chunk in client.executor.stream(
                    request={'message': message},
                    context={'session_id': session_id, 'user_id': 'interactive_user'}
                ):
                    if chunk.get('is_task_complete'):
                        print(chunk.get('content', 'No response'))
                        break
                    else:
                        print(f"[{chunk.get('content', 'Processing...')}]", end=" ", flush=True)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("\\n👋 Goodbye!")
        
    except Exception as e:
        logger.error(f"Interactive test failed: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(run_interactive_test())
    else:
        asyncio.run(run_comprehensive_tests())