#!/usr/bin/env python3
"""
Demo del Sistema de Guardrails para LUCA

Este script demuestra el funcionamiento del sistema de guardrails educativos
implementado para LUCA, incluyendo validación de contenido, contexto educativo,
rate limiting y integración con Langfuse.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def demo_content_safety():
    """Demostrar validación de seguridad de contenido."""
    print("\n🛡️ === DEMO: Validación de Seguridad de Contenido ===")
    
    from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext
    
    # Configuración sin OpenAI Moderation y Langfuse para la demo
    config = GuardrailConfig(
        enable_openai_moderation=False,  # Evitar costos de API en demo
        enable_profanity_filter=True,
        enable_educational_validation=True,
        enable_rate_limiting=False,  # Deshabilitado para demo
        enable_langfuse_logging=False  # Deshabilitar Langfuse para evitar errores de API
    )
    
    guardrail = EducationalGuardrailLayer(config)
    context = EducationalContext(
        student_id="demo_student",
        session_id="demo_session",
        subject="Bases de Datos"
    )
    
    # Test cases
    test_cases = [
        ("¿Qué es un LEFT JOIN?", "✅ Consulta educativa válida"),
        ("Explícame normalización de bases de datos", "✅ Consulta académica apropiada"),
        ("Haceme la tarea completa", "⚠️ Solicitud de hacer tarea completa"),
        ("Che boludo, no entiendo nada", "⚠️ Lenguaje inapropiado detectado"),
        ("Hablemos de fútbol", "⚠️ Tema fuera del contexto académico"),
    ]
    
    for test_input, expected in test_cases:
        print(f"\n📝 Input: '{test_input}'")
        print(f"🎯 Esperado: {expected}")
        
        try:
            result = await guardrail.validate_input(test_input, context)
            
            if result.passed:
                print("✅ APROBADO - Sin violaciones")
            elif result.should_block:
                print("❌ BLOQUEADO - Violaciones críticas:")
                for violation in result.violations:
                    print(f"   - {violation.message}")
            else:
                print("⚠️ ADVERTENCIA - Violaciones menores:")
                for violation in result.violations:
                    print(f"   - {violation.message}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")


async def demo_educational_context():
    """Demostrar validación de contexto educativo."""
    print("\n📚 === DEMO: Validación de Contexto Educativo ===")
    
    from guardrails.educational_context import EducationalContextGuardrail
    from guardrails import GuardrailConfig, EducationalContext
    
    config = GuardrailConfig(
        enable_educational_validation=True,
        strict_academic_mode=False,  # Modo flexible para demo
        allow_general_knowledge=True,
        enable_langfuse_logging=False  # Deshabilitar Langfuse para evitar errores de API
    )
    
    edu_guardrail = EducationalContextGuardrail(config)
    context = EducationalContext(
        student_id="demo_student",
        session_id="demo_session", 
        subject="Programación"
    )
    
    test_cases = [
        ("¿Cómo funciona un algoritmo de ordenamiento?", "Consulta académica"),
        ("Necesito ayuda con Java y bases de datos", "Consulta técnica válida"),
        ("¿Qué película me recomendás?", "Contenido de entretenimiento"),
        ("¿Cómo cocino pasta?", "Completamente fuera de tema"),
    ]
    
    for test_input, category in test_cases:
        print(f"\n📝 Input: '{test_input}' ({category})")
        
        try:
            result = await edu_guardrail.validate(test_input, context)
            
            academic_score = result.metadata.get('keyword_analysis', {}).get('academic_score', 0)
            print(f"📊 Puntuación académica: {academic_score:.2f}")
            
            if result.violations:
                print("⚠️ Observaciones:")
                for violation in result.violations:
                    print(f"   - {violation.message}")
            else:
                print("✅ Contexto educativo apropiado")
                
        except Exception as e:
            print(f"❌ Error: {e}")


async def demo_rate_limiting():
    """Demostrar sistema de rate limiting."""
    print("\n⏱️ === DEMO: Sistema de Rate Limiting ===")
    
    from guardrails.rate_limiting import RateLimitingGuardrail
    from guardrails import GuardrailConfig, EducationalContext
    
    # Límites bajos para demostración
    config = GuardrailConfig(
        enable_rate_limiting=True,
        max_requests_per_minute=3,  # Muy bajo para demo
        max_requests_per_hour=10,
        max_requests_per_day=20,
        enable_langfuse_logging=False  # Deshabilitar Langfuse para evitar errores de API
    )
    
    rate_guardrail = RateLimitingGuardrail(config)
    context = EducationalContext(
        student_id="demo_student_rate_limit",
        session_id="demo_session"
    )
    
    # Simular múltiples requests
    for i in range(5):
        print(f"\n🔄 Request {i+1}/5")
        
        try:
            result = await rate_guardrail.validate("Test message", context)
            
            if result.passed:
                print("✅ Request permitido")
            else:
                print("❌ Request bloqueado:")
                for violation in result.violations:
                    print(f"   - {violation.message}")
                    
            # Mostrar estado actual
            usage_stats = result.metadata.get('usage_stats', {})
            print(f"📊 Uso actual: {usage_stats.get('requests_last_minute', 0)}/3 por minuto")
                
        except Exception as e:
            print(f"❌ Error: {e}")


async def demo_orchestrator_integration():
    """Demostrar integración con el Orchestrator."""
    print("\n🎭 === DEMO: Integración con Orchestrator ===")
    
    try:
        from orchestrator.agent_executor import OrchestratorAgentExecutor
        
        # Crear executor con guardrails habilitados
        print("🚀 Inicializando Orchestrator con Guardrails...")
        executor = OrchestratorAgentExecutor(enable_guardrails=True)
        
        # Verificar estado de guardrails
        status = executor.get_guardrail_status("demo_student")
        print(f"🛡️ Guardrails habilitados: {status.get('guardrails_enabled', False)}")
        
        if status.get('guardrails_enabled'):
            print("✅ Sistema de guardrails completamente integrado con Orchestrator")
            
            # Mostrar configuración
            config = status.get('config', {})
            print(f"📋 Configuración activa:")
            print(f"   - Moderación OpenAI: {config.get('enable_openai_moderation', False)}")
            print(f"   - Filtro de profanidad: {config.get('enable_profanity_filter', False)}")
            print(f"   - Validación educativa: {config.get('enable_educational_validation', False)}")
            print(f"   - Rate limiting: {config.get('enable_rate_limiting', False)}")
            print(f"   - Logging Langfuse: {config.get('enable_langfuse_logging', False)}")
        else:
            print("⚠️ Guardrails no disponibles - funcionando sin protecciones")
            
    except ImportError as e:
        print(f"❌ No se pudo importar Orchestrator: {e}")
    except Exception as e:
        print(f"❌ Error en integración con Orchestrator: {e}")


def demo_langfuse_integration():
    """Demostrar integración con Langfuse."""
    print("\n📊 === DEMO: Integración con Langfuse ===")
    
    import os
    
    # Verificar configuración de Langfuse
    langfuse_vars = ['LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY']
    langfuse_configured = all(os.getenv(var) for var in langfuse_vars)
    
    print(f"🔗 Langfuse configurado: {langfuse_configured}")
    
    if langfuse_configured:
        print(f"📡 Host: {os.getenv('LANGFUSE_HOST', 'No configurado')}")
        print("✅ Las validaciones de guardrails se logearán automáticamente en Langfuse")
        print("📈 Incluye: violaciones, métricas de uso, análisis de contenido")
        
        try:
            from tools.observability import get_langfuse_client
            client = get_langfuse_client()
            if client:
                print("✅ Cliente Langfuse disponible para observabilidad")
            else:
                print("⚠️ Cliente Langfuse no inicializado")
        except Exception as e:
            print(f"⚠️ Error verificando Langfuse: {e}")
    else:
        print("⚠️ Variables de entorno de Langfuse no configuradas")
        print("💡 Configura LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY")


async def main():
    """Ejecutar todas las demos."""
    print("🎬 === DEMO COMPLETO: Sistema de Guardrails LUCA ===")
    print("Este demo muestra las capacidades del sistema de guardrails educativos")
    print("implementado para proteger y mejorar las interacciones con estudiantes.")
    
    try:
        await demo_content_safety()
        await demo_educational_context()
        await demo_rate_limiting()
        await demo_orchestrator_integration()
        demo_langfuse_integration()
        
        print("\n🎉 === DEMO COMPLETADO ===")
        print("✅ Sistema de guardrails implementado y funcionando")
        print("🛡️ Protecciones activas para contenido, contexto y uso")
        print("📊 Observabilidad completa con Langfuse")
        print("🎭 Integración transparente con agentes existentes")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())