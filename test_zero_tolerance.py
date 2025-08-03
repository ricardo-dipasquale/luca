#!/usr/bin/env python3
"""
Test del Zero Tolerance Policy para Profanidad

Este script prueba que el sistema de guardrails bloquee inmediatamente
cualquier contenido con profanidad, sin excepciones.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_zero_tolerance():
    """Test zero tolerance policy for profanity."""
    print("🚫 === TEST: Zero Tolerance Policy para Profanidad ===")
    
    from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext
    
    # Configuration with profanity filter enabled
    config = GuardrailConfig(
        enable_openai_moderation=False,  # Focus on local profanity filter
        enable_profanity_filter=True,
        enable_educational_validation=False,  # Disable to focus on profanity
        enable_rate_limiting=False,
        enable_langfuse_logging=False
    )
    
    guardrail = EducationalGuardrailLayer(config)
    context = EducationalContext(
        student_id="test_student",
        session_id="test_session",
        subject="Bases de Datos"
    )
    
    # Test cases with different levels of profanity
    test_cases = [
        ("¿Qué es un LEFT JOIN?", "✅ Contenido limpio - debe pasar"),
        ("Este ejercicio está difícil", "✅ Contenido académico - debe pasar"),
        ("Che boludo, no entiendo", "❌ Una palabra inapropiada - debe bloquear"),
        ("Esto es una mierda", "❌ Profanidad - debe bloquear"),
        ("No entiendo este carajo de ejercicio", "❌ Profanidad en contexto - debe bloquear"),
        ("Boludo pelotudo", "❌ Múltiple profanidad - debe bloquear"),
        ("El LEFT JOIN es como el boludo de los joins", "❌ Profanidad mezclada - debe bloquear")
    ]
    
    print("\n🧪 Probando Zero Tolerance Policy:")
    print("=" * 60)
    
    for test_input, expected in test_cases:
        print(f"\n📝 Input: '{test_input}'")
        print(f"🎯 Esperado: {expected}")
        
        try:
            result = await guardrail.validate_input(test_input, context)
            
            if result.passed:
                print("✅ APROBADO - Input permitido")
                if "❌" in expected:
                    print("⚠️  ERROR: Este contenido debería haber sido bloqueado!")
            else:
                print("❌ BLOQUEADO - Input bloqueado")
                if "✅" in expected:
                    print("⚠️  ERROR: Este contenido debería haber sido permitido!")
                
                print("🛡️ Violaciones detectadas:")
                for violation in result.violations:
                    print(f"   - Tipo: {violation.type.value}")
                    print(f"   - Severidad: {violation.severity.value}")
                    print(f"   - Mensaje: {violation.message}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 TEST COMPLETADO - Verificar que TODA profanidad fue bloqueada")


if __name__ == "__main__":
    asyncio.run(test_zero_tolerance())