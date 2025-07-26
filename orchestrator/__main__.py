"""
Orchestrator Agent - Main Entry Point

CLI and server entry point for the Orchestrator Agent, supporting both
standalone execution and A2A framework integration.
"""

import asyncio
import logging
import sys
from typing import Optional

import click
from a2a import AgentExecutor, StarlettePlatform
from starlette.applications import Starlette

from .agent_executor import OrchestratorAgentExecutor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', default='localhost', help='Host to bind the server')
@click.option('--port', default=10001, help='Port to bind the server')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--test-message', help='Test the agent with a direct message')
@click.option('--session-id', help='Session ID for testing')
def main(host: str, port: int, debug: bool, test_message: Optional[str], session_id: Optional[str]):
    """
    Orchestrator Agent - Educational Conversation Manager
    
    Start the Orchestrator Agent server or run a test message.
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")
    
    if test_message:
        # Run test mode
        asyncio.run(test_agent(test_message, session_id))
    else:
        # Run server mode
        run_server(host, port, debug)


async def test_agent(message: str, session_id: Optional[str] = None):
    """
    Test the orchestrator agent with a direct message.
    
    Args:
        message: Test message to send to the agent
        session_id: Optional session ID for testing
    """
    try:
        print(f"🔬 Testing Orchestrator Agent")
        print(f"📝 Message: {message}")
        print(f"🆔 Session: {session_id or 'default_test_session'}")
        print("-" * 60)
        
        # Create executor and test
        executor = OrchestratorAgentExecutor()
        
        # Test streaming response
        print("🔄 Streaming Response:")
        async for chunk in executor.stream(
            request={'message': message},
            context={'session_id': session_id or 'test_session', 'user_id': 'test_user'}
        ):
            if chunk.get('is_task_complete'):
                print(f"✅ Final Response:")
                print(chunk.get('content', 'No content'))
                
                # Show structured response if available
                structured = chunk.get('structured_response')
                if structured:
                    print(f"\\n📊 Structured Response:")
                    print(f"   Status: {structured.get('status')}")
                    print(f"   Intent: {structured.get('intent')}")
                    print(f"   Routing: {structured.get('routing_agent')}")
                    
                    edu_ctx = structured.get('educational_context', {})
                    if edu_ctx.get('subject'):
                        print(f"   Subject: {edu_ctx.get('subject')}")
                    if edu_ctx.get('practice'):
                        print(f"   Practice: {edu_ctx.get('practice')}")
                break
            else:
                print(f"🔄 {chunk.get('content', 'Processing...')}")
        
        # Get session summary
        session_info = executor.get_session_info(session_id or 'test_session')
        if 'error' not in session_info:
            print(f"\\n📋 Session Summary:")
            print(f"   Messages: {session_info.get('message_count', 0)}")
            print(f"   Subject: {session_info.get('educational_context', {}).get('current_subject', 'None')}")
            print(f"   Topics: {', '.join(session_info.get('educational_context', {}).get('topics_discussed', []))}")
        
        print("\\n✅ Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")


def run_server(host: str, port: int, debug: bool):
    """
    Run the A2A server for the orchestrator agent.
    
    Args:
        host: Server host
        port: Server port  
        debug: Enable debug mode
    """
    try:
        logger.info(f"Starting Orchestrator Agent server on {host}:{port}")
        
        # Create agent executor
        agent_executor = OrchestratorAgentExecutor()
        
        # Create A2A agent executor wrapper
        a2a_executor = AgentExecutor(agent_executor)
        
        # Create Starlette application
        app = Starlette(debug=debug)
        
        # Create A2A platform and register routes
        platform = StarlettePlatform(app)
        platform.register_agent_executor(a2a_executor)
        
        # Add health check endpoint
        @app.route('/health')
        async def health_check(request):
            from starlette.responses import JSONResponse
            return JSONResponse({
                'status': 'healthy',
                'agent': 'orchestrator',
                'version': '1.0.0'
            })
        
        # Add session management endpoints
        @app.route('/sessions/{session_id}')
        async def get_session(request):
            from starlette.responses import JSONResponse
            session_id = request.path_params['session_id']
            session_info = agent_executor.get_session_info(session_id)
            return JSONResponse(session_info)
        
        @app.route('/sessions/cleanup', methods=['POST'])
        async def cleanup_sessions(request):
            from starlette.responses import JSONResponse
            try:
                data = await request.json()
                max_hours = data.get('max_inactive_hours', 24)
                agent_executor.cleanup_sessions(max_hours)
                return JSONResponse({'status': 'success', 'message': 'Sessions cleaned up'})
            except Exception as e:
                return JSONResponse({'status': 'error', 'message': str(e)}, status_code=400)
        
        # Add agent card endpoint
        @app.route('/agent-card')
        async def get_agent_card(request):
            from starlette.responses import JSONResponse
            return JSONResponse(agent_executor.get_agent_card())
        
        logger.info(f"Orchestrator Agent server ready!")
        logger.info(f"Agent card available at: http://{host}:{port}/agent-card")
        logger.info(f"Health check at: http://{host}:{port}/health")
        logger.info(f"A2A endpoint at: http://{host}:{port}/")
        
        # Import uvicorn and run
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info" if not debug else "debug")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def print_help():
    """Print help information."""
    print("""
🎓 Orchestrator Agent - Educational Conversation Manager

USAGE:
    python -m orchestrator [OPTIONS]

OPTIONS:
    --host HOST          Host to bind the server (default: localhost)
    --port PORT          Port to bind the server (default: 10001)
    --debug              Enable debug mode
    --test-message TEXT  Test with a direct message
    --session-id ID      Session ID for testing
    --help               Show this help message

EXAMPLES:
    # Start the server
    python -m orchestrator --host 0.0.0.0 --port 10001
    
    # Test with a message
    python -m orchestrator --test-message "¿Qué es un LEFT JOIN?"
    
    # Test with session ID
    python -m orchestrator --test-message "Necesito ayuda con la práctica 2" --session-id "student_123"

FEATURES:
    • Intent classification for educational queries
    • Multi-agent coordination (GapAnalyzer, Knowledge Retrieval)
    • Persistent conversation memory
    • Educational guidance and next-step recommendations
    • A2A framework integration
    • Session management and cleanup

ENDPOINTS:
    • GET /agent-card - Agent capabilities and metadata
    • GET /health - Health check
    • GET /sessions/{id} - Session information
    • POST /sessions/cleanup - Clean up inactive sessions
    • POST / - Main A2A agent endpoint
    """)


if __name__ == "__main__":
    main()