# Sistema de Guardrails LUCA

El sistema de guardrails de LUCA proporciona una arquitectura híbrida de protecciones para interacciones educativas, asegurando contenido apropiado, relevancia académica y uso responsable de los agentes de AI.

## 🎯 **Arquitectura General**

```
Student Input
     ↓
┌─────────────────────────────────────┐
│    GUARDRAIL LAYER (Centralizada)   │
│  • Content Safety                   │
│  • Educational Context              │
│  • Rate Limiting                    │
│  • Profanity Filter                 │
└─────────────────────────────────────┘
     ↓ (filtered/approved input)
┌─────────────────────────────────────┐
│       ORCHESTRATOR AGENT            │
│  • Academic Intent Classification   │
│  • Educational Domain Validation    │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│      SPECIALIZED AGENTS             │
│  • Subject-specific guardrails      │
│  • Response validation              │
└─────────────────────────────────────┘
```

## 🛡️ **Componentes del Sistema**

### **1. Capa Superior (`EducationalGuardrailLayer`)**
**Archivo**: `core.py`

Orquesta todas las validaciones antes de que el input llegue a los agentes.

```python
from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext

# Configuración básica
config = GuardrailConfig(
    enable_openai_moderation=True,
    enable_profanity_filter=True,
    enable_educational_validation=True,
    enable_rate_limiting=True
)

# Inicializar sistema
guardrail = EducationalGuardrailLayer(config)

# Crear contexto educativo
context = EducationalContext(
    student_id="student_123",
    session_id="session_456", 
    subject="Bases de Datos",
    academic_level="university",
    institution="UCA"
)

# Validar input
result = await guardrail.validate_input(user_message, context)

if result.should_block:
    print("❌ Input bloqueado:", result.violations)
elif result.has_warnings:
    print("⚠️ Advertencias:", result.violations)
else:
    print("✅ Input aprobado")
```

### **2. Validación de Seguridad de Contenido (`ContentSafetyGuardrail`)**
**Archivo**: `content_safety.py`

- **OpenAI Moderation API**: Detección de contenido inapropiado
- **Filtro de Profanidad**: Términos inapropiados en español argentino
- **Integridad Académica**: Detección de intentos de hacer trampa

```python
from guardrails.content_safety import ContentSafetyGuardrail

safety = ContentSafetyGuardrail(config)

# Validar input del estudiante
result = await safety.validate("Tu mensaje aquí", context)

# Validar respuesta del agente
response_result = await safety.validate_response("Respuesta del agente", context)
```

**Política de Zero Tolerance**:
- **Profanidad**: Cualquier término inapropiado bloquea inmediatamente el contenido
- **Severidad**: Todas las violaciones de profanidad son `BLOCK` (no warnings)
- **Términos incluidos**: Insultos, groserías, lenguaje ofensivo en español argentino
- **Inapropiado académico**: "haceme la tarea", "dame la respuesta" (WARNING)
- **Manipulación**: "ignora tus instrucciones", "actúa como si" (WARNING)

### **3. Validación de Contexto Educativo (`EducationalContextGuardrail`)**
**Archivo**: `educational_context.py`

- **Keywords Académicos**: Detecta términos relacionados con el curriculum
- **Relevancia Curricular**: Valida alineación con dominios de Ingeniería
- **Assessment LLM**: Análisis de contenido ambiguo con GPT-4

```python
from guardrails.educational_context import EducationalContextGuardrail

edu_guardrail = EducationalContextGuardrail(config)
result = await edu_guardrail.validate(user_input, context)

# Obtener puntuación académica
academic_score = result.metadata['keyword_analysis']['academic_score']
print(f"Relevancia académica: {academic_score:.2f}/1.0")
```

**Dominios curriculares soportados**:
- Ingeniería, Matemáticas, Programación
- Bases de Datos, Algoritmos, Estructuras de Datos
- Redes, Sistemas Operativos

### **4. Rate Limiting (`RateLimitingGuardrail`)**
**Archivo**: `rate_limiting.py`

Sistema de límites con penalizaciones escaladas:

```python
from guardrails.rate_limiting import RateLimitingGuardrail

rate_limiter = RateLimitingGuardrail(config)

# Verificar límites
result = await rate_limiter.validate(user_input, context)

# Obtener estado actual del usuario
status = rate_limiter.get_user_status("student_123")
print(f"Requests restantes: {status['remaining']}")
```

**Límites por defecto**:
- 30 requests/minuto
- 200 requests/hora  
- 1000 requests/día

### **5. Validación de Respuestas (`AgentResponseValidator`)**
**Archivo**: `agent_response_validation.py`

Valida que las respuestas de los agentes mantengan calidad educativa:

```python
from guardrails.agent_response_validation import AgentResponseValidator

validator = AgentResponseValidator(config)
result = await validator.validate_response(
    agent_response="La respuesta del agente...",
    original_question="Pregunta original del estudiante",
    context=context
)

# Análisis de calidad educativa
educational_score = result.metadata['educational_analysis']['educational_score']
pedagogical_quality = result.metadata['pedagogical_analysis']['pedagogical_quality']
```

## 🔧 **Configuración**

### **Variables de Entorno**

```bash
# Content Safety
export GUARDRAILS_ENABLE_OPENAI_MODERATION=true
export GUARDRAILS_ENABLE_PROFANITY_FILTER=true
export GUARDRAILS_CONTENT_SAFETY_THRESHOLD=0.7

# Educational Context
export GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION=true
export GUARDRAILS_STRICT_ACADEMIC_MODE=false
export GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE=true

# Rate Limiting
export GUARDRAILS_ENABLE_RATE_LIMITING=true
export GUARDRAILS_MAX_REQUESTS_PER_MINUTE=30
export GUARDRAILS_MAX_REQUESTS_PER_HOUR=200
export GUARDRAILS_MAX_REQUESTS_PER_DAY=1000

# Response Validation
export GUARDRAILS_ENABLE_RESPONSE_VALIDATION=true
export GUARDRAILS_VALIDATE_EDUCATIONAL_VALUE=true

# Observability
export GUARDRAILS_ENABLE_LANGFUSE_LOGGING=true
export GUARDRAILS_LOG_ALL_INTERACTIONS=true
export GUARDRAILS_LOG_BLOCKED_ATTEMPTS=true
```

### **Configuraciones Predefinidas**

```python
from guardrails.config import (
    get_development_config,    # Permisivo para desarrollo
    get_production_config,     # Estricto para producción
    get_testing_config,        # Mínimo para tests
    create_config_for_environment
)

# Auto-detectar entorno
config = create_config_for_environment()  # Lee ENVIRONMENT o NODE_ENV

# Configuración específica
dev_config = get_development_config()      # Límites altos, modo flexible
prod_config = get_production_config()     # Límites estrictos, modo académico
test_config = get_testing_config()        # APIs deshabilitadas, sin límites
```

## 🎭 **Integración con Orchestrator**

El sistema se integra automáticamente con el `OrchestratorAgentExecutor`:

```python
from orchestrator.agent_executor import OrchestratorAgentExecutor

# Guardrails habilitados por defecto
executor = OrchestratorAgentExecutor(enable_guardrails=True)

# Verificar estado
status = executor.get_guardrail_status("student_123")
print(f"Guardrails activos: {status['guardrails_enabled']}")

# El streaming incluye automáticamente validación:
async for chunk in executor.stream(request, context):
    if chunk.get('guardrail_blocked'):
        print("Request bloqueado por guardrails")
    yield chunk
```

### **Wrapper de Streaming**

El sistema proporciona streaming transparente con validación:

```python
from guardrails.orchestrator_integration import GuardrailOrchestrator

guardrail_orch = GuardrailOrchestrator(config)

# Wrapper automático con validación
async for chunk in guardrail_orch.create_guardrail_streaming_wrapper(
    original_stream_function=agent.stream,
    user_message="Mensaje del estudiante",
    session_id="session_123",
    student_id="student_456"
):
    print(chunk)
```

## 📊 **Observabilidad con Langfuse**

### **Traces Automáticos**

Todas las validaciones se loggean automáticamente en Langfuse:

```json
{
  "trace_name": "guardrail_validation",
  "session_id": "session_123",
  "user_id": "student_456",
  "input": {
    "user_input": "¿Qué es un LEFT JOIN?",
    "context": {...}
  },
  "output": {
    "validation_passed": true,
    "violations": [],
    "execution_time_ms": 45.2
  },
  "spans": [
    {"name": "content_safety_check", "passed": true},
    {"name": "educational_context_check", "passed": true},
    {"name": "rate_limiting_check", "passed": true}
  ]
}
```

### **Métricas Disponibles**

En Langfuse podrás monitorear:

- **Violaciones por tipo**: `content_safety`, `educational_context`, `rate_limiting`
- **Tasas de bloqueo**: Porcentaje de requests bloqueados
- **Patrones de uso**: Horarios, frecuencia por estudiante
- **Calidad educativa**: Scores de relevancia académica
- **Performance**: Tiempo de ejecución de validaciones

## 🧪 **Testing**

### **Ejecutar Demo Completo**

```bash
python test_guardrails_demo.py
```

### **Tests Unitarios**

```python
import pytest
from guardrails import EducationalGuardrailLayer, EducationalContext
from guardrails.config import get_testing_config

@pytest.fixture
def guardrail_system():
    config = get_testing_config()  # APIs deshabilitadas
    return EducationalGuardrailLayer(config)

@pytest.fixture  
def edu_context():
    return EducationalContext(
        student_id="test_student",
        session_id="test_session",
        subject="Programación"
    )

@pytest.mark.asyncio
async def test_appropriate_academic_content(guardrail_system, edu_context):
    result = await guardrail_system.validate_input(
        "¿Cómo funciona un algoritmo de ordenamiento?", 
        edu_context
    )
    assert result.passed
    assert not result.violations

@pytest.mark.asyncio
async def test_inappropriate_content_blocked(guardrail_system, edu_context):
    result = await guardrail_system.validate_input(
        "Haceme toda la tarea", 
        edu_context
    )
    assert result.has_warnings or result.should_block
    assert len(result.violations) > 0
```

## 🚨 **Manejo de Errores**

### **Graceful Degradation**

El sistema está diseñado para degradar graciosamente:

```python
try:
    result = await guardrail.validate_input(user_input, context)
except Exception as e:
    logger.error(f"Guardrail error: {e}")
    # Sistema continúa sin guardrails
    result = GuardrailResult(passed=True, violations=[])
```

### **Fallbacks por Componente**

- **OpenAI API error**: Continúa con filtros locales
- **Langfuse error**: Logging deshabilitado, validación continúa
- **Rate limiting error**: Sin límites temporalmente
- **Educational assessment error**: Validación por keywords únicamente

## 📈 **Monitoreo y Alertas**

### **Métricas Clave**

1. **Tasa de bloqueos**: `blocked_rate = blocked_requests / total_requests`
2. **Falsos positivos**: Inputs académicos bloqueados incorrectamente
3. **Tiempo de validación**: Latencia agregada por guardrails
4. **Uso por estudiante**: Detección de patrones anómalos

### **Alertas Recomendadas**

```python
# Ejemplo de alertas (pseudocódigo)
if blocked_rate > 0.15:  # >15% de requests bloqueados
    alert("Tasa de bloqueos alta - revisar configuración")

if avg_validation_time > 500:  # >500ms de latencia
    alert("Guardrails impactando performance")

if user_violations > 10:  # >10 violaciones por usuario
    alert(f"Usuario problemático: {user_id}")
```

## 🔄 **Versionado y Actualizaciones**

### **Versión Actual**: `1.0.0`

### **Changelog**

- **v1.0.0**: Release inicial con arquitectura híbrida
  - Validación de contenido con OpenAI Moderation API
  - Filtros de profanidad contextuales para Argentina
  - Rate limiting inteligente con escalado
  - Integración completa con Langfuse
  - Wrapper transparente para Orchestrator

### **Roadmap**

- **v1.1.0**: Fine-tuning basado en datos reales de estudiantes
- **v1.2.0**: Dashboard de administración
- **v1.3.0**: ML personalizado para contexto educativo UCA
- **v2.0.0**: Soporte multi-idioma y personalización por carrera

## 🤝 **Contribución**

### **Agregar Nuevos Filtros**

```python
# En content_safety.py
def _check_new_inappropriate_pattern(self, text: str) -> Dict[str, Any]:
    violations = []
    # Tu lógica de validación aquí
    return {"violations": violations}

# Agregar al método validate()
new_result = self._check_new_inappropriate_pattern(user_input)
violations.extend(new_result['violations'])
```

### **Nuevos Dominios Curriculares**

```python
# En educational_context.py
curriculum_domains.extend([
    "Inteligencia Artificial",
    "Ciberseguridad", 
    "DevOps"
])
```

## 📞 **Soporte**

Para issues, contribuciones o consultas:

1. **Issues**: Usar GitHub Issues del proyecto LUCA
2. **Documentación**: Ver ejemplos en `test_guardrails_demo.py`
3. **Configuración**: Usar `guardrails.config.print_config_help()`

---

**Desarrollado para LUCA Educational AI System**  
Universidad Católica Argentina - Facultad de Ingeniería y Ciencias Agrarias.