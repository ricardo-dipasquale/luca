# CLAUDE.md

Guía para Claude Code en este repositorio. Visión general y puesta en marcha: [README.md](README.md). Ingesta y regeneración de soluciones: [ingest/README.md](ingest/README.md).

## Comandos

```bash
uv sync                                   # entorno (.venv)
uv run pytest                             # tests (LLM simulado; no llaman a OpenAI)
uv run ruff check .
docker compose up -d chroma               # requerido por la ingesta de apuntes y por la app
uv run python -m ingest [--only practicas|soluciones|apuntes] [--force] [--regenerar-no-conformes]
uv run python frontend/run.py --port 5000 [--no-debug]
```

Variables de entorno: `.env.example`. El usuario usa direnv (`.envrc`): nunca leer, imprimir ni copiar `.envrc`, `.env`, `*.pem` ni `ssl/`.

## Arquitectura

- `ingest/` (batch, fuera de la app): `practicas.py` (Excel → `artifacts/practicas.json`), `soluciones.py` (LLM genera AR faltante + SQL; valida con sqlglot y forma canónica; resultado revisable en `content/soluciones_generadas.json`), `apuntes.py` (PDF/MD → Chroma, incremental por hash).
- `course/`: `rules.py` (reglas AR → SQL, única fuente para prompts de ingesta y tutor), `canonical.py` (control de forma canónica sobre el AST), `practices.py` (`PracticeRepository`: `get_exercise`, `tree` sin soluciones), `rag.py` (`ApuntesRetriever`).
- `agent/`: `graph.py` (LangGraph: preparar → [deducir] → buscar → tutor | teoría), `prompts.py`, `leak.py` (detección determinista de filtración de la solución), `executor.py` (guardrails + agente; lo usa Flask).
- `storage/db.py`: SQLite (usuarios con hash, conversaciones, mensajes con `exercise_id`). La memoria del tutor (checkpoints) vive en el mismo archivo.
- `frontend/flask_app.py`: `/chat` (exercise_id opcional; el id de la conversación es el hilo de memoria), `/practicas`, conversaciones. `templates/chat.html`: panel de prácticas, banner del ejercicio activo.
- `guardrails/`: entrada (seguridad, rate limit, relevancia académica) y salida (valor educativo; sólo registra).
- `tools/llm_config.py`: creación del LLM (`create_default_llm`).

## Premisas que no se pueden romper

1. **El tutor nunca revela la solución** de un ejercicio (ni AR ni SQL completos, ni reconstruida por partes). `agent/leak.py` lo verifica; si se cambia el prompt del tutor, correr la evaluación con LLM real (casos: sin intento, intento incorrecto/correcto, SQL no canónico, pedido de la respuesta, teoría, ejercicio propio) y confirmar cero filtraciones.
2. **`tree()` / `/practicas` nunca exponen respuestas, tips, criterios ni soluciones** al navegador (hay test).
3. **SQL canónico deducido del AR**: ∪ → UNION, ∩ → INTERSECT, − → EXCEPT, ÷ → doble NOT EXISTS con la plantilla del Taller #8 (A AS A1 / A AS A2, B / A AS A3). SQL ANSI, **sin WITH** (intermedios como `CREATE VIEW`). El AR no expresa orden. MES(), AÑO(), LIKE y aritmética en AR son abuso de notación permitido. Las reglas viven en `course/rules.py`; si se agrega una premisa, reflejarla también en `course/canonical.py` cuando sea verificable y regenerar con `--regenerar-no-conformes`.
4. **Soluciones aprobadas por el docente** (`estado: aprobada` en `content/soluciones_generadas.json`) nunca se regeneran ni se editan programáticamente.
5. **Ownership**: toda ruta que reciba un `conversation_id` verifica `db.conversation_owner(...) == session['user_email']`.
6. **Nada de HTML sin sanitizar** en el chat: texto del alumno con `textContent`, respuestas del tutor con `DOMPurify.sanitize(marked.parse(...))`.

## Detalles no obvios

- Flask corre cada pedido en su propio `asyncio.run()`. Por eso: el cliente HTTP async de los LLM no reutiliza conexiones (`_async_http_client` en `tools/llm_config.py`) y el checkpointer SQLite (`AsyncSqliteSaver`) se abre por pedido en `TutorAgent.stream`. Un recurso async compartido entre pedidos falla con "Event loop is closed".
- `gpt-6-luna` sólo acepta temperature=1 y `max_completion_tokens`: usar `temperature_for` / `chat_completion_params` de `tools/llm_config.py`, no pasar esos parámetros a mano.
- Flask consume el stream completo del ejecutor: la validación de salida de los guardrails corre después de la respuesta final.
- La app falla al arrancar si falta `artifacts/practicas.json` o la colección de Chroma: es intencional (correr `python -m ingest`).

## Convenciones

- Textos para alumnos y docentes en español de Argentina, sin asumir género. Código, nombres internos y comentarios en inglés salvo dominio (práctica, ejercicio, apunte).
- Tests: LLM y retriever simulados (ver `test/test_agent.py`), Chroma `EphemeralClient`, SQLite en `tmp_path`. Ningún test debe llamar a OpenAI.
- Antes de commitear, revisar el diff en busca de claves (`sk-...`, `PRIVATE KEY`). El usuario sufrió el robo de su key de OpenAI.
