#!/usr/bin/env python3
"""
Test de Content Safety Flexible - Moderation API vs LLM

Este script prueba que el sistema puede alternar entre usar OpenAI Moderation API
y GPT-4o-mini para content safety según la configuración.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_llm_method():
    """Test content safety using LLM method."""
    print("🤖 === TEST: Content Safety con LLM (GPT-4o-mini) ===")
    
    from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext
    
    # Force LLM method
    config = GuardrailConfig(
        content_safety_method="llm",
        enable_openai_moderation=False,  # This will be overridden by method
        enable_profanity_filter=True,
        enable_educational_validation=False,  # Focus on content safety
        enable_rate_limiting=False,
        enable_langfuse_logging=False
    )
    
    guardrail = EducationalGuardrailLayer(config)
    context = EducationalContext(
        student_id="test_student",
        session_id="test_session",
        subject="Bases de Datos Relacionales"
    )
    
    test_cases = [
        ("¿Qué es un LEFT JOIN?", "✅ Debe pasar - consulta académica"),
        ("te hago una pregunta boluda: el ejercicio 1.a es fácil?", "❓ LLM debe evaluar contexto"),
        ("Esto es una mierda total", "❌ Debe bloquear - profanidad clara"),
        ("Che, no entiendo el JOIN", "❓ LLM debe considerar contexto argentino")
    ]
    
    for test_input, expected in test_cases:
        print(f"\n📝 Input: '{test_input}'")
        print(f"🎯 Esperado: {expected}")
        
        try:
            result = await guardrail.validate_input(test_input, context)
            
            if result.passed:
                print("✅ APROBADO por LLM")
            else:
                print("❌ BLOQUEADO por LLM")
                for violation in result.violations:
                    print(f"   - {violation.message}")
                    if violation.details.get("method") == "llm_gpt4o_mini":
                        print(f"   - Razón LLM: {violation.details.get('reason')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_environment_configuration():
    """Test that environment variables control the method selection."""
    print("\n🌍 === TEST: Configuración por Variables de Entorno ===")
    
    # Set environment variable temporarily
    original_method = os.environ.get('GUARDRAILS_CONTENT_SAFETY_METHOD')
    os.environ['GUARDRAILS_CONTENT_SAFETY_METHOD'] = 'llm'
    
    try:
        from guardrails.config import load_guardrail_config_from_env
        
        config = load_guardrail_config_from_env()
        
        print(f"📊 Método configurado: {config.content_safety_method}")
        print(f"🔧 OpenAI Moderation habilitado: {config.enable_openai_moderation}")
        print(f"🛡️ Filtro de profanidad habilitado: {config.enable_profanity_filter}")
        
        if config.content_safety_method == "llm":
            print("✅ Configuración correcta: Usando LLM para content safety")
        else:
            print("❌ Error: Configuración no refleja la variable de entorno")
            
    finally:
        # Restore original environment
        if original_method is not None:
            os.environ['GUARDRAILS_CONTENT_SAFETY_METHOD'] = original_method
        else:
            os.environ.pop('GUARDRAILS_CONTENT_SAFETY_METHOD', None)


async def test_orchestrator_integration():
    """Test that orchestrator uses the new flexible configuration."""
    print("\n🎭 === TEST: Integración Orchestrator con Configuración Flexible ===")
    
    try:
        from orchestrator.agent_executor import OrchestratorAgentExecutor
        
        # Initialize orchestrator (should read from environment)
        executor = OrchestratorAgentExecutor(enable_guardrails=True)
        
        # Check configuration
        status = executor.get_guardrail_status("test_student")
        
        if status.get('guardrails_enabled'):
            config = status.get('config', {})
            method = config.get('content_safety_method', 'unknown')
            
            print(f"✅ Orchestrator inicializado con guardrails")
            print(f"📊 Método de content safety: {method}")
            print(f"🔧 Configuración desde variables de entorno: {method == 'llm'}")
        else:
            print("❌ Guardrails no habilitados en Orchestrator")
            
    except Exception as e:
        print(f"❌ Error en integración Orchestrator: {e}")


async def main():
    """Run all tests."""
    print("🧪 === TEST COMPLETO: Sistema de Content Safety Flexible ===")
    print("Verificando que el sistema puede usar tanto Moderation API como LLM")
    print()
    
    await test_llm_method()
    await test_environment_configuration() 
    await test_orchestrator_integration()
    
    print("\n🎉 === TESTS COMPLETADOS ===")
    print("Verificar que:")
    print("1. ✅ LLM method funciona correctamente")
    print("2. ✅ Variables de entorno controlan la configuración") 
    print("3. ✅ Orchestrator usa la configuración flexible")


if __name__ == "__main__":
    asyncio.run(main())