"""
Chat module for LUCA frontend.

Handles communication with the Orchestrator agent.
"""

import asyncio
import aiohttp
import json
from typing import AsyncIterator, Dict, Any, Optional
from orchestrator.agent_executor import OrchestratorAgentExecutor

class OrchestratorClient:
    """Client for communicating with the Orchestrator agent."""
    
    def __init__(self):
        """Initialize the orchestrator client."""
        self.executor = OrchestratorAgentExecutor()
    
    def process_message_sync(self, message: str, session_id: str, subject: Optional[str] = None) -> Dict[str, Any]:
        """
        Process message synchronously and return final result.
        
        This method handles the async streaming internally and returns
        just the final result, which is more Streamlit-friendly.
        
        Args:
            message: User message
            session_id: Session ID
            subject: Educational subject
            
        Returns:
            Final response with progress steps
        """
        try:
            async def _process():
                context = {
                    'session_id': session_id,
                    'user_id': 'frontend_user'
                }
                
                if subject:
                    context['educational_subject'] = subject
                
                print(f"🔍 Orchestrator client processing:")
                print(f"   Message: {message}")
                print(f"   Context: {context}")
                
                progress_steps = []
                final_response = ""
                
                async for chunk in self.executor.stream(
                    request={'message': message},
                    context=context
                ):
                    print(f"📦 Client received chunk: {chunk.get('content', 'No content')[:100]}...")
                    
                    if chunk.get('is_task_complete'):
                        final_response = chunk.get('content', 'No se pudo obtener respuesta')
                        print(f"✅ Client received final response")
                        break
                    else:
                        progress_text = chunk.get('content', 'Procesando...')
                        progress_steps.append(progress_text)
                
                return {
                    'content': final_response,
                    'progress_steps': progress_steps,
                    'success': True
                }
            
            # Use asyncio.run which creates a new event loop
            return asyncio.run(_process())
            
        except Exception as e:
            print(f"❌ Orchestrator client error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'content': f'Error al procesar el mensaje: {str(e)}. Por favor, intenta nuevamente.',
                'progress_steps': ['Error en el procesamiento'],
                'success': False,
                'error': str(e)
            }
    
    async def stream_message(
        self, 
        message: str, 
        session_id: str,
        subject: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream a message to the orchestrator and get streaming response.
        
        Args:
            message: User message
            session_id: Session/conversation ID
            subject: Educational subject
            
        Yields:
            Response chunks from the orchestrator
        """
        try:
            # Prepare request context
            context = {
                'session_id': session_id,
                'user_id': 'frontend_user'
            }
            
            # Add subject if provided
            if subject:
                context['educational_subject'] = subject
            
            print(f"🔍 Frontend calling orchestrator with:")
            print(f"   Message: {message}")
            print(f"   Context: {context}")
            
            # Stream response from orchestrator
            async for chunk in self.executor.stream(
                request={'message': message},
                context=context
            ):
                print(f"📦 Frontend received chunk: {chunk.get('content', 'No content')[:100]}...")
                yield chunk
                
        except Exception as e:
            yield {
                'is_task_complete': True,
                'content': f'Error al procesar el mensaje: {str(e)}',
                'error': True
            }

class OrchestratorAPIClient:
    """Alternative client using HTTP API (if orchestrator is running as service)."""
    
    def __init__(self, base_url: str = "http://localhost:10001"):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for orchestrator API
        """
        self.base_url = base_url
    
    async def stream_message(
        self, 
        message: str, 
        session_id: str,
        subject: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream a message via HTTP API.
        
        Args:
            message: User message
            session_id: Session ID
            subject: Educational subject
            
        Yields:
            Response chunks
        """
        try:
            # Prepare request payload
            payload = {
                'message': message,
                'context': {
                    'session_id': session_id,
                    'user_id': 'frontend_user'
                }
            }
            
            if subject:
                payload['context']['educational_subject'] = subject
            
            # Make streaming request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/stream",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    
                    if response.status != 200:
                        yield {
                            'is_task_complete': True,
                            'content': 'Error de conexión con el servidor',
                            'error': True
                        }
                        return
                    
                    # Process streaming response
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode().strip())
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            yield {
                'is_task_complete': True,
                'content': f'Error de conexión: {str(e)}',
                'error': True
            }

# You can switch between direct client and API client based on your setup
def get_orchestrator_client() -> OrchestratorClient:
    """
    Get the appropriate orchestrator client.
    
    Returns:
        Configured orchestrator client
    """
    # For now, we'll use the direct client
    # In production, you might want to use the API client
    return OrchestratorClient()