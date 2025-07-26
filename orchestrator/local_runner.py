"""
Local runner for Orchestrator agent debugging.

This script allows running the Orchestrator agent locally without the A2A framework
for debugging and development purposes. It provides an interactive conversation interface
for testing intent classification, multi-agent coordination, and memory management.
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional
from uuid import uuid4

from orchestrator.agent_executor import OrchestratorAgentExecutor
from orchestrator.schemas import ConversationContext, ConversationMemory, EducationalContext


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalOrchestratorRunner:
    """Local runner for debugging the Orchestrator agent."""
    
    def __init__(self, default_subject: Optional[str] = None):
        """Initialize the local runner.
        
        Args:
            default_subject: Default subject to inject into educational context
        """
        try:
            self.executor = OrchestratorAgentExecutor()
            self.session_id = str(uuid4())
            self.default_subject = default_subject
            logger.info(f"Orchestrator agent initialized successfully with default subject: {default_subject}")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator agent: {e}")
            raise
    
    def close(self):
        """Close connections and cleanup resources."""
        try:
            # Orchestrator handles its own cleanup
            logger.info("Local runner closed successfully")
        except Exception as e:
            logger.error(f"Error closing local runner: {e}")
    
    async def run_conversation(self, message: str, show_streaming: bool = True, subject: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a conversation turn with the orchestrator.
        
        Args:
            message: Student message
            show_streaming: Whether to show streaming progress
            subject: Optional subject override for this conversation
            
        Returns:
            Final response from orchestrator
        """
        # Determine the subject to use
        conversation_subject = subject or self.default_subject
        
        print(f"\n=== CONVERSACIÓN CON ORQUESTADOR ===")
        print(f"Student: {message}")
        print(f"Session: {self.session_id}")
        print(f"Subject: {conversation_subject or 'Sin materia especificada'}")
        print("-" * 50)
        
        try:
            final_response = None
            
            if show_streaming:
                print("\n=== PROGRESO DEL PROCESAMIENTO ===")
                
                # Build request context with subject
                request_context = {
                    'session_id': self.session_id, 
                    'user_id': 'debug_user'
                }
                
                # If we have a subject, inject it into the request
                if conversation_subject:
                    request_context['educational_subject'] = conversation_subject
                
                async for chunk in self.executor.stream(
                    request={'message': message},
                    context=request_context
                ):
                    if chunk.get('is_task_complete'):
                        final_response = chunk
                        print(f"\n✅ Respuesta final completada")
                        break
                    else:
                        print(f"🔄 {chunk.get('content', 'Procesando...')}")
            else:
                # Direct execution without streaming with subject context
                request_context = {'educational_subject': conversation_subject} if conversation_subject else {}
                final_response = await self.executor.handle_direct_request(message, self.session_id, **request_context)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error en conversación: {e}")
            return {"error": str(e)}
    
    def print_response_analysis(self, response: Dict[str, Any]):
        """
        Print detailed analysis of the orchestrator response.
        
        Args:
            response: Response from orchestrator
        """
        print("\n" + "=" * 60)
        print("ANÁLISIS DE RESPUESTA DEL ORQUESTADOR")
        print("=" * 60)
        
        # Main content
        content = response.get('content', 'No se pudo obtener respuesta')
        print(f"\n📝 RESPUESTA AL ESTUDIANTE:")
        print(content)
        
        # Structured analysis
        structured = response.get('structured_response', {})
        if structured:
            print(f"\n🔍 ANÁLISIS ESTRUCTURADO:")
            print(f"   Status: {structured.get('status', 'unknown')}")
            print(f"   Intent: {structured.get('intent', 'unknown')}")
            print(f"   Routing: {structured.get('routing_agent', 'unknown')}")
            
            # Educational context
            edu_ctx = structured.get('educational_context', {})
            if edu_ctx:
                print(f"\n📚 CONTEXTO EDUCATIVO:")
                print(f"   Subject: {edu_ctx.get('subject', 'None')}")
                print(f"   Practice: {edu_ctx.get('practice', 'None')}")
                print(f"   Topics: {edu_ctx.get('topics', [])}")
        
        # Session information
        session_info = self.executor.get_session_info(self.session_id)
        if 'error' not in session_info:
            print(f"\n💾 ESTADO DE SESIÓN:")
            print(f"   Messages: {session_info.get('message_count', 0)}")
            print(f"   Session ID: {session_info.get('session_id', 'unknown')}")
            print(f"   Duration: desde {session_info.get('start_time', 'unknown')}")
            
            edu_session_ctx = session_info.get('educational_context', {})
            if edu_session_ctx:
                print(f"   Current Subject: {edu_session_ctx.get('current_subject', 'None')}")
                print(f"   Current Practice: {edu_session_ctx.get('current_practice', 'None')}")
                print(f"   Topics Discussed: {edu_session_ctx.get('topics_discussed', [])}")
                print(f"   Recent Intents: {session_info.get('recent_intents', [])}")
    
    async def test_intent_classification(self, test_messages: Optional[list] = None):
        """
        Test intent classification with various message types.
        
        Args:
            test_messages: Optional list of test messages
        """
        print(f"\n=== TESTING INTENT CLASSIFICATION ===")
        print("-" * 50)
        
        if not test_messages:
            test_messages = [
                "¿Qué es normalización en bases de datos?",  # theoretical_question
                "Mi consulta SQL no funciona correctamente",  # practical_general
                "No entiendo por qué mi JOIN duplica registros en la práctica 2, ejercicio 1.d",  # practical_specific
                "¿Podrías explicar mejor lo anterior?",  # clarification
                "¿Qué otros tipos de relaciones hay?",  # exploration
                "Hola, necesito ayuda con mi tarea",  # greeting
                "¿Cómo está el clima hoy?",  # off_topic
                "¿Cómo escribo una consulta con INNER JOIN?",  # practical_general
                "No puedo resolver el ejercicio 2.a de la práctica 3"  # practical_specific
            ]
        
        results = []
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i} ---")
            print(f"Message: {message}")
            
            # Use a unique session for each test to avoid interference
            test_session = f"{self.session_id}_intent_test_{i}"
            
            try:
                response = None
                async for chunk in self.executor.stream(
                    request={'message': message},
                    context={'session_id': test_session, 'user_id': 'intent_test_user'}
                ):
                    if chunk.get('is_task_complete'):
                        response = chunk
                        break
                
                if response:
                    structured = response.get('structured_response', {})
                    intent = structured.get('intent', 'unknown')
                    routing = structured.get('routing_agent', 'unknown')
                    
                    print(f"Intent: {intent}")
                    print(f"Routing: {routing}")
                    
                    results.append({
                        'message': message,
                        'intent': intent,
                        'routing': routing,
                        'success': True
                    })
                else:
                    print("❌ No response received")
                    results.append({
                        'message': message,
                        'error': 'No response',
                        'success': False
                    })
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    'message': message,
                    'error': str(e),
                    'success': False
                })
        
        # Summary
        successful = sum(1 for r in results if r.get('success', False))
        total = len(results)
        
        print(f"\n📊 INTENT CLASSIFICATION SUMMARY:")
        print(f"   Successful: {successful}/{total} ({successful/total*100:.1f}%)")
        
        return results
    
    async def interactive_mode(self):
        """
        Run interactive conversation mode for debugging.
        """
        print("🎮 MODO INTERACTIVO DEL ORQUESTADOR")
        print("Escribe 'quit' para salir, 'session' para info de sesión")
        print("Escribe 'intent-test' para probar clasificación de intenciones")
        print("-" * 60)
        
        conversation_count = 0
        
        while True:
            try:
                message = input(f"\n[{conversation_count}] Tu mensaje: ").strip()
                
                if message.lower() in ['quit', 'exit', 'salir']:
                    break
                elif message.lower() == 'session':
                    session_info = self.executor.get_session_info(self.session_id)
                    print(f"\n📋 Session Info:")
                    print(json.dumps(session_info, indent=2, default=str))
                    continue
                elif message.lower() == 'intent-test':
                    await self.test_intent_classification()
                    continue
                elif not message:
                    continue
                
                # Process message
                response = await self.run_conversation(message, show_streaming=True)
                
                if response and 'error' not in response:
                    self.print_response_analysis(response)
                    conversation_count += 1
                else:
                    print(f"❌ Error: {response.get('error', 'Unknown error')}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print(f"\n👋 Sesión finalizada después de {conversation_count} conversaciones")
        print(f"Session ID: {self.session_id}")


async def main():
    """Main entry point for the local runner."""
    try:
        # Check if required arguments were provided
        if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
            print_help()
            return
        
        # Parse mode argument
        mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
        
        if mode == "interactive":
            # Interactive mode
            runner = None
            try:
                runner = LocalOrchestratorRunner()
                await runner.interactive_mode()
            finally:
                if runner:
                    runner.close()
                    
        elif mode == "single":
            # Single message mode - parse optional --subject parameter
            import argparse
            
            parser = argparse.ArgumentParser(description="Orchestrator single message mode", add_help=False)
            parser.add_argument('--subject', '-s', type=str, help='Educational subject for the conversation')
            parser.add_argument('message', nargs='+', help='Student message')
            
            # Parse remaining arguments
            remaining_args = sys.argv[2:]
            if not remaining_args:
                print("❌ Error: Se requiere un mensaje para el modo single")
                print_help()
                sys.exit(1)
            
            try:
                args = parser.parse_args(remaining_args)
                message = " ".join(args.message)
                subject = args.subject
            except SystemExit:
                print("❌ Error: Argumentos inválidos para modo single")
                print("Uso: python -m orchestrator.local_runner single [--subject MATERIA] MESSAGE")
                sys.exit(1)
            
            runner = None
            try:
                runner = LocalOrchestratorRunner(default_subject=subject)
                print(f"🔍 Procesando mensaje único: {message}")
                if subject:
                    print(f"📚 Materia: {subject}")
                
                response = await runner.run_conversation(message, subject=subject)
                
                if response and 'error' not in response:
                    runner.print_response_analysis(response)
                else:
                    print(f"❌ Error: {response.get('error', 'Unknown error')}")
                    
            finally:
                if runner:
                    runner.close()
                    
        elif mode == "intent-test":
            # Intent classification testing mode
            runner = None
            try:
                runner = LocalOrchestratorRunner()
                await runner.test_intent_classification()
            finally:
                if runner:
                    runner.close()
                    
        else:
            print(f"❌ Error: Modo desconocido '{mode}'")
            print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Ejecución interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error en el runner local: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def print_help():
    """Print help information."""
    print("""
🎓 Orchestrator Local Runner - Herramienta de debugging

USAGE:
    python -m orchestrator.local_runner [MODE] [OPTIONS]

MODES:
    interactive         Modo conversación interactiva (default)
    single MESSAGE      Procesar un mensaje único
    intent-test         Probar clasificación de intenciones

OPTIONS:
    -h, --help          Muestra esta ayuda

EXAMPLES:
    # Modo interactivo (default)
    python -m orchestrator.local_runner
    python -m orchestrator.local_runner interactive
    
    # Mensaje único
    python -m orchestrator.local_runner single "¿Qué es un LEFT JOIN?"
    
    # Mensaje único con materia específica
    python -m orchestrator.local_runner single --subject "Bases de Datos Relacionales" "No entiendo por qué mi LEFT JOIN duplica registros"
    
    # Test de clasificación de intenciones
    python -m orchestrator.local_runner intent-test

CARACTERÍSTICAS DEL MODO INTERACTIVO:
    • Conversación multi-turno con memoria persistente
    • Análisis detallado de respuestas y contexto
    • Comandos especiales:
      - 'session': Ver información de sesión
      - 'intent-test': Probar clasificación de intenciones
      - 'quit': Salir del modo interactivo

CARACTERÍSTICAS DE DEBUGGING:
    • Streaming de progreso en tiempo real
    • Análisis de intent classification
    • Estado de memoria de conversación
    • Coordinación multiagente observable
    • Contexto educativo persistente
    • Session management completo
    """)


if __name__ == "__main__":
    asyncio.run(main())