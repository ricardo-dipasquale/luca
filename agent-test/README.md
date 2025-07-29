# LUCA Agent Testing Framework

Sistema completo de testing para agentes educativos de LUCA con integración a Langfuse.

## 🚀 Características

- **Gestión de Suites**: Crear y administrar suites de pruebas en JSON
- **Ejecución Multi-Agente**: Testear Orchestrator y GapAnalyzer 
- **Métricas Avanzadas**: Recolección automática de métricas de agentes
- **Integración Langfuse**: Subida de datasets y tracking de ejecuciones
- **CLI Completo**: Interfaz de línea de comandos intuitiva
- **Reportes y Análisis**: Generación de reportes y análisis de tendencias

## 📦 Instalación

```bash
# Navegar al directorio del proyecto
cd /home/ricardo/git/luca

# Instalar dependencias adicionales
pip install langfuse click pydantic

# Verificar instalación
python -m agent-test.cli --help
```

## 🛠️ Configuración

### Variables de Entorno

```bash
# Langfuse (opcional)
export LANGFUSE_HOST="http://localhost:3000"
export LANGFUSE_PUBLIC_KEY="pk-lf-your-key"
export LANGFUSE_SECRET_KEY="sk-lf-your-key"

# Neo4j (ya configurado)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"

# OpenAI (ya configurado)
export OPENAI_API_KEY="your_openai_key"
```

## 📚 Uso Básico

### 1. Gestión de Suites

```bash
# Crear nueva suite
python -m agent-test.cli suite create mi_suite --agent=orchestrator --description="Suite de prueba"

# Agregar pregunta
python -m agent-test.cli suite add-question mi_suite \
  --question="¿Qué es un LEFT JOIN?" \
  --expected="Explicación de LEFT JOIN con ejemplos" \
  --subject="Bases de Datos" \
  --difficulty=medium

# Listar suites
python -m agent-test.cli suite list

# Ver detalles de suite
python -m agent-test.cli suite show mi_suite
```

### 2. Integración con Langfuse

```bash
# Subir suite como dataset
python -m agent-test.cli dataset upload mi_suite --name="Suite Básica BD"

# Listar datasets en Langfuse
python -m agent-test.cli dataset list
```

### 3. Ejecución de Pruebas

```bash
# Ejecutar suite individual
python -m agent-test.cli run mi_suite --iterations=1

# Ejecutar con agente específico
python -m agent-test.cli run mi_suite --agent=orchestrator

# Ejecutar todas las suites
python -m agent-test.cli run-all
```

### 4. Análisis de Resultados

```bash
# Listar ejecuciones recientes
python -m agent-test.cli results list

# Ver detalles de ejecución
python -m agent-test.cli results show <run_id>

# Filtrar por suite
python -m agent-test.cli results list --suite=mi_suite --limit=5
```

## 📊 Suites de Ejemplo

El sistema incluye suites de ejemplo:

### Orchestrator Básico
```bash
python -m agent-test.cli suite show orchestrator_basic_qa
python -m agent-test.cli run orchestrator_basic_qa
```

### GapAnalyzer Prácticas
```bash
python -m agent-test.cli suite show gapanalyzer_practice_analysis
python -m agent-test.cli run gapanalyzer_practice_analysis
```

## 📈 Métricas Recolectadas

### Orchestrator Agent
- **Intent Detection**: Intents detectados y confianza
- **Routing Decisions**: Decisiones de enrutamiento a GapAnalyzer
- **Knowledge Graph Usage**: Consultas y resultados del KG
- **Response Quality**: Longitud, ejemplos, notación matemática
- **Educational Content**: Tipo de explicación, profundidad conceptual

### GapAnalyzer Agent
- **Gap Analysis**: Gaps identificados y tipos
- **Content Retrieval**: Contenido relevante encontrado
- **Pedagogical Elements**: Scaffolding, hints, sugerencias
- **Explanation Depth**: Nivel de profundidad en explicaciones

### Métricas Generales
- **Performance**: Tiempo de ejecución, tasa de éxito
- **Response Quality**: Completitud, claridad, relevancia
- **Educational Value**: Valor pedagógico de las respuestas

## 🏗️ Estructura del Proyecto

```
agent-test/
├── cli.py                    # CLI principal
├── __main__.py              # Entry point
├── schemas.py               # Esquemas Pydantic
├── config/
│   └── config.yaml         # Configuración
├── core/
│   ├── suite_manager.py    # Gestión de suites
│   ├── test_runner.py      # Ejecutor de pruebas
│   ├── metrics_collector.py # Recolección de métricas  
│   ├── results_manager.py  # Gestión de resultados
│   └── langfuse_integration.py # Integración Langfuse
├── suites/                 # Archivos de suites JSON
├── results/                # Resultados de ejecuciones
│   ├── runs/              # Resultados individuales
│   ├── summaries/         # Resúmenes por suite
│   └── exports/           # Exportaciones
└── README.md
```

## 🔧 Comandos Avanzados

### Validación de Suites
```bash
# Validar suite antes de ejecución
python -c "
from agent_test.core.suite_manager import SuiteManager
manager = SuiteManager()
result = manager.validate_suite('mi_suite')
print(result)
"
```

### Exportación de Resultados
```bash
# Exportar múltiples runs a CSV
python -c "
from agent_test.core.results_manager import ResultsManager
manager = ResultsManager()
runs = manager.list_runs(limit=5)
run_ids = [r['run_id'] for r in runs]
export_path = manager.export_results(run_ids, format='csv')
print(f'Exportado a: {export_path}')
"
```

### Análisis de Tendencias
```bash
# Analizar tendencias de performance
python -c "
from agent_test.core.results_manager import ResultsManager
manager = ResultsManager()
trends = manager.get_performance_trends('mi_suite', days=7)
print(trends)
"
```

## 🐛 Troubleshooting

### Error de Importación
```bash
# Verificar que estás en el directorio correcto
pwd  # Debería ser /home/ricardo/git/luca

# Verificar estructura de archivos
ls -la agent-test/
```

### Error de Langfuse
```bash
# Verificar conexión
python -c "
from agent_test.core.langfuse_integration import check_langfuse_availability
print('Langfuse disponible:', check_langfuse_availability())
"
```

### Error de Agentes
```bash
# Testear agentes individualmente
python -m orchestrator.local_runner single "Test message"
python -m gapanalyzer.local_runner 1 1.a "Test query"
```

## 🤝 Desarrollo

### Agregar Nuevas Métricas

1. Editar `schemas.py` para agregar campos a `OrchestratorMetrics` o `GapAnalyzerMetrics`
2. Implementar recolección en `metrics_collector.py`
3. Actualizar patrones de detección si es necesario

### Agregar Nuevos Tipos de Agente

1. Agregar al enum `AgentType` en `schemas.py`
2. Implementar ejecución en `test_runner.py`
3. Agregar métricas específicas en `metrics_collector.py`

### Nuevos Formatos de Exportación

1. Editar `results_manager.py` método `export_results()`
2. Implementar nueva función de exportación
3. Actualizar CLI para soportar el nuevo formato

## 📝 TODO / Mejoras Futuras

- [ ] Interfaz web para visualizar resultados
- [ ] Evaluaciones automáticas con LLM
- [ ] Comparación automática con respuestas esperadas
- [ ] Alertas automáticas por degradación de performance
- [ ] Integración con CI/CD para testing continuo
- [ ] Dashboard de métricas en tiempo real
- [ ] Soporte para múltiples proyectos/equipos

## 📄 Licencia

Parte del proyecto LUCA - Sistema educativo con IA.