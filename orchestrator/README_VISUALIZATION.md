# Orchestrator Workflow Visualization

Este directorio contiene herramientas para visualizar el flujo de trabajo LangGraph del agente Orchestrator.

## Archivos Generados

- **`orchestrator_workflow.png`** - Diagrama visual del workflow en formato PNG
- **`orchestrator_workflow.jpg`** - Diagrama visual del workflow en formato JPG  
- **`visualize_workflow.py`** - Script para generar las visualizaciones

## Uso del Visualizador

### Comandos Básicos

```bash
# Generar PNG (por defecto)
python orchestrator/visualize_workflow.py

# Generar JPG
python orchestrator/visualize_workflow.py --format jpg

# Solo mostrar información del workflow (sin generar imagen)
python orchestrator/visualize_workflow.py --info-only

# Modo verbose para debugging
python orchestrator/visualize_workflow.py --verbose
```

### Como Módulo

```bash
# Ejecutar como módulo de Python
python -m orchestrator.visualize_workflow --format png
```

### Opciones Avanzadas

```bash
# Especificar ruta de salida personalizada
python orchestrator/visualize_workflow.py --output ./docs/workflow_diagram.png

# Combinación de opciones
python orchestrator/visualize_workflow.py --format jpg --output ./diagrams/ --verbose
```

## Estructura del Workflow

El workflow de Orchestrator está compuesto por los siguientes nodos:

### 🔄 Nodos Principales

1. **`classify_intent`** - Analiza mensaje del estudiante y clasifica intención educativa
2. **`route_to_agent`** - Decide qué agente especializado o enfoque usar
3. **`execute_agent_calls`** - Ejecuta llamadas a agentes apropiados (GapAnalyzer, KG, respuesta directa)
4. **`synthesize_response`** - Combina respuestas de agentes en respuesta educativa coherente
5. **`update_memory`** - Actualiza memoria de conversación y contexto educativo
6. **`handle_error`** - Maneja errores del workflow con fallbacks educativos

### 🎯 Clasificación de Intenciones

- **`theoretical_question`** - Preguntas conceptuales que requieren recuperación de conocimiento
- **`practical_general`** - Preguntas prácticas generales no vinculadas a ejercicios específicos del KG
- **`practical_specific`** - Ayuda específica con ejercicio/práctica mapeada en KG que requiere análisis de gaps
- **`exploration`** - Preguntas curiosas sobre temas relacionados
- **`greeting/goodbye`** - Interacciones sociales
- **`off_topic`** - Contenido no educativo que requiere redirección

### 🤖 Agentes Especializados

- **`gap_analyzer`** - Análisis de gaps educativos y evaluación de aprendizaje
- **`knowledge_retrieval`** - Búsqueda en grafo de conocimiento y contenido teórico
- **`direct_response`** - Respuestas simples e interacciones sociales

### 🔀 Lógica Condicional

- **Clasificación de intención** → Ruta basada en necesidades del estudiante y confianza
- **Ruteo de agentes** → Selecciona agente óptimo para intenciones específicas
- **Manejo de errores** → Recuperación robusta con orientación educativa
- **Gestión de contexto** → Mantiene continuidad de conversación educativa

### 📊 Características

- ✅ Coordinación multi-agente con roles educativos especializados
- ✅ Ruteo basado en intención para asistencia educativa óptima
- ✅ Memoria de conversación con persistencia de contexto educativo
- ✅ Síntesis de respuestas de múltiples fuentes de conocimiento
- ✅ Observabilidad completa con integración Langfuse
- ✅ Continuidad de conversación basada en threads
- ✅ Orientación educativa y sugerencias de próximos pasos

## Flujo de Datos

### Entrada
```python
ConversationContext(
    session_id="...",
    user_id="...",
    current_message="...",
    memory=ConversationMemory(
        educational_context=EducationalContext(
            current_subject="...",
            current_practice=...,
            topics_discussed=[...]
        )
    )
)
```

### Salida
```python
OrchestratorResponse(
    status="success",
    message="...",
    educational_guidance="...",
    intent_classification=IntentClassificationResult(...),
    routing_decision=AgentRoutingDecision(...),
    response_synthesis=ResponseSynthesis(...),
    conversation_context=ConversationContext(...)
)
```

## Gestión de Memoria

### 💾 Componentes de Memoria

- **Tracking de sesión** - Seguimiento de conversación basado en sesión
- **Contexto educativo** - Materia, práctica, temas discutidos
- **Historial de intención y ruteo** - Decisiones pasadas para coherencia
- **Soporte multi-turno** - Conversaciones prolongadas y contextuales

## Dependencias para Visualización

El script funciona con diferentes backends de visualización:

### LangGraph Nativo (Recomendado)
```bash
# Ya incluido con langgraph
pip install langgraph
```

### Mermaid CLI (Opcional)
```bash
# Para conversión de diagramas mermaid a imagen
npm install -g @mermaid-js/mermaid-cli
```

## Troubleshooting

### Error: "Module not found"
```bash
# Ejecutar desde el directorio raíz del proyecto
cd /home/ricardo/git/luca
python orchestrator/visualize_workflow.py
```

### Sin imagen generada
Si solo se genera un archivo `.mmd`, instalar mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i orchestrator_workflow.mmd -o orchestrator_workflow.png
```

### Error de conexión Neo4j
El visualizador puede funcionar sin conexión a Neo4j. Los errores de conexión no afectan la generación del diagrama.

## Integración en Documentación

Las imágenes generadas pueden ser incluidas en documentación:

```markdown
![Orchestrator Workflow](./orchestrator/orchestrator_workflow.png)
```

## Desarrollo

Para modificar la visualización, editar el método `generate_mermaid_diagram()` en `visualize_workflow.py`.

### Ejemplo de Personalización

```python
def generate_custom_mermaid_diagram():
    return """
    graph TD
        A[Tu Nodo Personalizado] --> B[Siguiente Nodo]
        B --> C{Decisión}
        C -->|Sí| D[Acción Si]
        C -->|No| E[Acción No]
    """
```

## Debugging del Workflow

### Usar con Local Runner

```bash
# Generar visualización
python orchestrator/visualize_workflow.py --info-only

# Ejecutar local runner para debugging
python -m orchestrator.local_runner interactive

# Debuggear con VSCode
# Usar configuración "Orchestrator Interactive Mode" en launch.json
```

### Observabilidad

El workflow incluye observabilidad completa:
- **Langfuse Integration** - Tracking automático de llamadas LLM
- **Session Management** - Continuidad de conversación
- **Error Handling** - Logging detallado de errores
- **Performance Metrics** - Timing y uso de tokens

## Referencias

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Mermaid Diagram Syntax](https://mermaid.js.org/syntax/)
- [Proyecto Luca - CLAUDE.md](../CLAUDE.md)
- [Orchestrator Local Runner](./local_runner.py)