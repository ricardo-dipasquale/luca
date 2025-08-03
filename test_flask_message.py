#!/usr/bin/env python3
"""
Test del mensaje específico de la aplicación Flask

Probar el mensaje exacto que se reportó en los logs de Flask.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_flask_message():
    """Test the exact message from Flask logs."""
    print("🧪 === TEST: Mensaje Específico de Flask ===")
    
    from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext
    
    # Production-like configuration
    config = GuardrailConfig(
        enable_openai_moderation=False,  # Keep disabled for testing
        enable_profanity_filter=True,    # This is what we're testing
        enable_educational_validation=True,
        enable_rate_limiting=True,
        enable_langfuse_logging=False    # Keep disabled for clean output
    )
    
    guardrail = EducationalGuardrailLayer(config)
    
    # Exact context from Flask logs
    context = EducationalContext(
        student_id="flask_user",
        session_id="c22fc8c1-6a82-40b9-b187-fc97020e39c8",
        subject="Bases de Datos Relacionales",
        institution="UCA"
    )
    
    # Exact message from Flask logs
    flask_message = "te hago una pregunta boluda: el ejercicio 1.a de la práctica 2 es fácil?"
    
    print(f"📝 Mensaje de Flask: '{flask_message}'")
    print("🎯 Con zero tolerance, este mensaje DEBE ser bloqueado")
    print()
    
    result = await guardrail.validate_input(flask_message, context)
    
    if result.passed:
        print("❌ ERROR: El mensaje fue PERMITIDO cuando debería ser BLOQUEADO")
        print("🔍 El mensaje contenía 'boluda' que es profanidad")
    else:
        print("✅ ÉXITO: El mensaje fue BLOQUEADO correctamente")
        print("🛡️ Zero tolerance policy funcionando")
        
        print("\n📊 Detalles de violaciones:")
        for violation in result.violations:
            print(f"   - Tipo: {violation.type.value}")
            print(f"   - Severidad: {violation.severity.value}")
            print(f"   - Mensaje: {violation.message}")
            if hasattr(violation, 'details') and violation.details:
                print(f"   - Detalles: Zero tolerance = {violation.details.get('zero_tolerance', False)}")
    
    print(f"\n⏱️ Tiempo de ejecución: {result.execution_time_ms:.2f}ms")
    print(f"🛡️ Guardrails ejecutados: {result.metadata.get('guardrails_executed', [])}")


if __name__ == "__main__":
    asyncio.run(test_flask_message())