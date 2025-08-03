#!/usr/bin/env python3
"""
Test de Integración con Flask - Zero Tolerance

Este script simula exactamente cómo funciona el sistema de guardrails
cuando se integra con la aplicación Flask en producción.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging similar to Flask
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_flask_integration():
    """Test integration exactly as it works in Flask app."""
    print("🌐 === TEST: Integración Flask con Zero Tolerance ===")
    
    try:
        # Import exactly as Flask does
        from orchestrator.agent_executor import OrchestratorAgentExecutor
        
        print("🚀 Inicializando OrchestratorAgentExecutor con guardrails...")
        
        # Initialize with guardrails enabled (default Flask configuration)
        executor = OrchestratorAgentExecutor(enable_guardrails=True)
        
        # Get guardrail status
        status = executor.get_guardrail_status("flask_user")
        print(f"🛡️ Guardrails habilitados: {status.get('guardrails_enabled', False)}")
        
        if not status.get('guardrails_enabled'):
            print("❌ ERROR: Guardrails no están habilitados")
            return
        
        # Exact context from Flask logs
        flask_context = {
            'session_id': 'c22fc8c1-6a82-40b9-b187-fc97020e39c8',
            'user_id': 'flask_user', 
            'educational_subject': 'Bases de Datos Relacionales'
        }
        
        # The problematic message from Flask logs
        flask_request = {
            'message': 'te hago una pregunta boluda: el ejercicio 1.a de la práctica 2 es fácil?'
        }
        
        print(f"📝 Procesando mensaje: '{flask_request['message']}'")
        print("🎯 Con zero tolerance, este mensaje debe ser bloqueado")
        print()
        
        # Test the streaming interface (as Flask uses it)
        print("🔄 Iniciando streaming validation...")
        
        chunks_received = []
        async for chunk in executor.stream(flask_request, flask_context):
            chunks_received.append(chunk)
            
            # Check if guardrails blocked the request
            if chunk.get('guardrail_blocked'):
                print("✅ ÉXITO: Request bloqueado por guardrails")
                print(f"🛡️ Razón: {chunk.get('guardrail_message', 'Violación de políticas de contenido')}")
                break
            elif chunk.get('content'):
                print(f"📦 Chunk recibido: {chunk['content'][:50]}...")
        
        # Analyze results
        blocked = any(chunk.get('guardrail_blocked') for chunk in chunks_received)
        
        if blocked:
            print("\n✅ RESULTADO: Zero tolerance funcionando correctamente")
            print("🚫 El mensaje con profanidad fue bloqueado antes de llegar al agente")
        else:
            print("\n❌ PROBLEMA: El mensaje no fue bloqueado")
            print("⚠️ Esto significa que el zero tolerance no está funcionando en producción")
            
            # Show what was received instead
            print("\n📊 Chunks recibidos:")
            for i, chunk in enumerate(chunks_received[:3]):  # Show first 3 chunks
                print(f"   {i+1}. {chunk}")
        
        print(f"\n📊 Total chunks recibidos: {len(chunks_received)}")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_flask_integration())