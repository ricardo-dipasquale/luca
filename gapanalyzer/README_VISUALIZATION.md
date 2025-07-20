# GapAnalyzer Workflow Visualization

Este directorio contiene herramientas para visualizar el flujo de trabajo LangGraph del agente GapAnalyzer.

## Archivos Generados

- **`gap_analysis_workflow.png`** - Diagrama visual del workflow en formato PNG
- **`gap_analysis_workflow.jpg`** - Diagrama visual del workflow en formato JPG  
- **`visualize_workflow.py`** - Script para generar las visualizaciones

## Uso del Visualizador

### Comandos Básicos

```bash
# Generar PNG (por defecto)
python gapanalyzer/visualize_workflow.py

# Generar JPG
python gapanalyzer/visualize_workflow.py --format jpg

# Solo mostrar información del workflow (sin generar imagen)
python gapanalyzer/visualize_workflow.py --info-only

# Modo verbose para debugging
python gapanalyzer/visualize_workflow.py --verbose
```

### Como Módulo

```bash
# Ejecutar como módulo de Python
python -m gapanalyzer.visualize_workflow --format png
```

### Opciones Avanzadas

```bash
# Especificar ruta de salida personalizada
python gapanalyzer/visualize_workflow.py --output ./docs/workflow_diagram.png

# Combinación de opciones
python gapanalyzer/visualize_workflow.py --format jpg --output ./diagrams/ --verbose
```

## Estructura del Workflow

El workflow de GapAnalyzer está compuesto por los siguientes nodos:

### 🔄 Nodos Principales

1. **`validate_context`** - Valida y prepara el contexto educativo
2. **`analyze_gaps`** - Identifica gaps de aprendizaje usando LLM
3. **`evaluate_gaps`** - Evalúa relevancia pedagógica e impacto
4. **`prioritize_gaps`** - Prioriza gaps y genera recomendaciones
5. **`feedback_analysis`** - (Opcional) Mejora la calidad del análisis
6. **`generate_response`** - Crea la respuesta estructurada final
7. **`handle_error`** - Maneja errores del workflow

### 🔀 Lógica Condicional

- **Validación de contexto** → Continúa o maneja error
- **Bucle de feedback** → Basado en confianza y número de iteraciones
- **Manejo de errores** → Recuperación robusta ante fallos

### 📊 Características

- ✅ Análisis multi-iteración para mejorar calidad
- ✅ Análisis estructurado de gaps con severidad y categoría
- ✅ Evaluación pedagógica con scoring de confianza
- ✅ Recomendaciones específicas y accionables
- ✅ Observabilidad completa con integración Langfuse
- ✅ Continuidad de conversación con manejo de threads

## Flujo de Datos

### Entrada
```python
StudentContext(
    student_question="...",
    conversation_history=[...],
    subject_name="...",
    practice_context="...",
    exercise_context="...",
    solution_context="...",
    tips_context="..."
)
```

### Salida
```python
GapAnalysisResult(
    student_context=...,
    educational_context=...,
    identified_gaps=[...],
    prioritized_gaps=[...],
    summary="...",
    confidence_score=0.85,
    recommendations=[...]
)
```

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
python gapanalyzer/visualize_workflow.py
```

### Sin imagen generada
Si solo se genera un archivo `.mmd`, instalar mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i gap_analysis_workflow.mmd -o gap_analysis_workflow.png
```

### Error de conexión Neo4j
El visualizador puede funcionar sin conexión a Neo4j. Los errores de conexión no afectan la generación del diagrama.

## Integración en Documentación

Las imágenes generadas pueden ser incluidas en documentación:

```markdown
![GapAnalyzer Workflow](./gapanalyzer/gap_analysis_workflow.png)
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

## Referencias

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Mermaid Diagram Syntax](https://mermaid.js.org/syntax/)
- [Proyecto Luca - CLAUDE.md](../CLAUDE.md)