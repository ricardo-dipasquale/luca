#!/usr/bin/env python3
"""
Test del Sistema de Guardrails en Entorno de Producción

Este script simula el uso del sistema de guardrails tal como lo haría
la aplicación Flask en producción.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to see what happens
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_production_guardrails():
    """Test guardrails system as used in production."""
    print("🧪 === TEST: Sistema de Guardrails en Producción ===")
    
    try:
        from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext
        
        # Production-like configuration (with Langfuse enabled)
        config = GuardrailConfig(
            enable_openai_moderation=False,  # Disable for testing (no API key needed)
            enable_profanity_filter=True,
            enable_educational_validation=True,
            enable_rate_limiting=True,
            enable_langfuse_logging=True,  # Enable Langfuse logging
            enable_response_validation=True,
            max_requests_per_minute=10,
            max_requests_per_hour=100
        )
        
        # Initialize guardrail system
        print("🚀 Inicializando sistema de guardrails...")
        guardrail = EducationalGuardrailLayer(config)
        
        # Test context similar to Flask app
        context = EducationalContext(
            student_id="flask_user",
            session_id="c22fc8c1-6a82-40b9-b187-fc97020e39c8",
            subject="Bases de Datos Relacionales",
            institution="UCA"
        )
        
        # Test the exact message from the Flask log
        test_message = "te hago una pregunta boluda: el ejercicio 1.a de la práctica 2 es fácil?"
        print(f"📝 Testing message: '{test_message}'")
        
        # Validate input
        result = await guardrail.validate_input(test_message, context)
        
        if result.passed:
            print("✅ APROBADO - Input validation passed")
        else:
            print("❌ BLOQUEADO - Input validation failed")
            for violation in result.violations:
                print(f"   - {violation.message}")
        
        print(f"⏱️ Execution time: {result.execution_time_ms:.2f}ms")
        print(f"🛡️ Guardrails executed: {result.metadata.get('guardrails_executed', [])}")
        
        # Test response validation
        mock_response = "El ejercicio 1.a de la práctica 2 es sobre consultas básicas con SELECT. Es relativamente sencillo si entendés los conceptos fundamentales de SQL..."
        
        print(f"\n📄 Testing response validation...")
        response_result = await guardrail.validate_response(mock_response, test_message, context)
        
        if response_result.passed:
            print("✅ APROBADO - Response validation passed")
        else:
            print("❌ BLOQUEADO - Response validation failed")
            for violation in response_result.violations:
                print(f"   - {violation.message}")
        
        print(f"⏱️ Response validation time: {response_result.execution_time_ms:.2f}ms")
        
        print("\n🎉 === TEST COMPLETADO ===")
        print("✅ Sistema de guardrails funcionando correctamente en entorno de producción")
        
    except Exception as e:
        print(f"❌ Error en test de producción: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_production_guardrails())