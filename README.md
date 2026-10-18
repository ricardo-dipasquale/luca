# LUCA: tutor de Bases de Datos

LUCA acompaña a los alumnos de Bases de Datos (UCA) en las prácticas de álgebra relacional y SQL. El alumno elige un ejercicio en el panel de prácticas y conversa con el tutor: el tutor analiza su planteo, señala qué le falta y lo orienta paso a paso, **sin darle la solución**. En consulta libre responde preguntas teóricas con citas de los apuntes de la materia, o acompaña un ejercicio que trae el propio alumno.

Premisas pedagógicas que el tutor respeta siempre:

- Todo problema se piensa primero en **álgebra relacional** y el SQL se deduce del AR operador por operador, con una **forma canónica** por operador (∪ → `UNION`, ∩ → `INTERSECT`, − → `EXCEPT`, ÷ → doble `NOT EXISTS` según el Taller #8).
- SQL **ANSI**, sin bloques `WITH`: los resultados intermedios van como vistas.
- El AR no expresa orden: el `ORDER BY` va sólo en SQL. `MES()`, `AÑO()`, `LIKE` y la aritmética en AR se aceptan como abuso de notación.
- Guía concreta pero de a uno o dos pasos; sin intento del alumno, una pista u opciones para analizar.

## Cómo funciona

```
content/  ──python -m ingest──►  artifacts/practicas.json        (prácticas: enunciados, tips, criterios, soluciones)
(planillas,                      content/soluciones_generadas.json (AR + SQL generados y validados, revisables)
 apuntes)                        Chroma                            (apuntes fragmentados y embebidos)

navegador ──► Flask ──► guardrails ──► agente tutor (LangGraph) ──► LLM (OpenAI)
                │                          │
                └── SQLite ◄───────────────┘  usuarios, conversaciones, memoria del tutor
```

- **Ingesta batch** (`ingest/`): lee las planillas y los apuntes, genera las soluciones que faltan (AR y SQL) y las valida. La aplicación nunca lee las fuentes directamente. Detalle en [ingest/README.md](ingest/README.md).
- **Agente tutor** (`agent/`): un único grafo LangGraph. Con un ejercicio seleccionado trabaja contra su solución de referencia (confidencial) y un control determinista impide que la respuesta la revele. En consulta libre distingue teoría (respuesta directa con citas) de ejercicio propio (deduce en privado una solución de referencia).
- **Conocimiento del curso** (`course/`): reglas de AR → SQL, control de forma canónica, repositorio de prácticas y búsqueda en los apuntes (Chroma).
- **Guardrails** (`guardrails/`): seguridad del contenido, relevancia académica, límite de uso y validación de las respuestas.
- **Persistencia** (`storage/`): SQLite en un único archivo (`data/luca.db`).

## Puesta en marcha (desarrollo)

Requisitos: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker.

```bash
uv sync                                  # dependencias (incluye pytest y ruff)
cp .envrc.example .envrc                 # completar OPENAI_API_KEY y FLASK_SECRET_KEY; direnv allow
docker compose up -d chroma              # base vectorial de los apuntes (puerto 8001)
uv run python -m ingest                  # prácticas, soluciones y apuntes
uv run python scripts/import_usuarios.py --file usuarios-luca.xlsx   # o crear un usuario a mano:
uv run python -c "from storage import db; db.upsert_user('alguien@uca.edu.ar', 'clave', 'Nombre')"
uv run python frontend/run.py            # http://localhost:5000
```

Con Docker, después de la ingesta: `docker compose up -d` levanta Chroma y la aplicación (desarrollo).

Para publicar en un servidor: `docker-compose.prod.yml` (Caddy con TLS, secretos como archivos, contenedores endurecidos). Guía paso a paso en [deploy/README.md](deploy/README.md).

## Contenido de la materia

Todo el material vive en `content/` y se versiona:

| Archivo | Qué es |
|---|---|
| `Programa.xlsx` | Materia, objetivos, unidades y temas (con sus apuntes) |
| `Prácticas Bases de Datos.xlsx` | Prácticas: cabecera (criterios de corrección, teoría relacionada), tips y enunciados con respuestas en AR |
| `apuntes/*.pdf`, `*.md` | Apuntes que el tutor cita |
| `soluciones_generadas.json` | AR y SQL generados por la ingesta, para revisar y aprobar |

Al cambiar cualquiera de ellos, correr `python -m ingest` (ver [ingest/README.md](ingest/README.md) para qué se regenera y cómo aprobar soluciones).

## Administración

```bash
uv run python scripts/import_usuarios.py --file usuarios-luca.xlsx [--dry-run] [--reset-passwords]   # alta de usuarios
uv run python scripts/export_conversaciones.py [--output conversaciones.xlsx] [--user EMAIL]
uv run python scripts/generate_ssl_certs.py      # certificado autofirmado para HTTPS local
```

Las cuentas listadas en `LUCA_ADMINS` ven el botón «Usuarios», que lleva a `/admin`: alta individual (con contraseña provisoria escrita o generada), subida de la planilla, blanqueo de contraseñas y la lista de usuarios. Para el resto de las cuentas, `/admin` no existe (404). La cuenta de administración se crea como cualquier otra (planilla o `db.upsert_user`).

La planilla de usuarios lleva el nombre en la 1.ª columna, el email (`@uca.edu.ar`) en la 3.ª y la contraseña (8 caracteres o más) en la 4.ª. Las contraseñas se guardan con hash. Plantilla para completar: [frontend/static/plantilla_usuarios.xlsx](frontend/static/plantilla_usuarios.xlsx) (también se descarga desde `/admin`).

Las contraseñas que carga la administración (planilla, script o `/admin`) son **provisorias**: al entrar, LUCA pide cambiarla antes de dejar usar el chat. Después cada estudiante puede cambiarla cuando quiera (botón «Contraseña», junto a «Salir»); al cambiarla se cierran sus otras sesiones. Volver a importar la planilla no pisa esas contraseñas: para blanquear la de alguien que la olvidó, usar el alta individual con «blanquear», o `--reset-passwords` con una planilla que tenga sólo esas filas.

## Tests

```bash
uv run pytest
```

Los tests usan un LLM simulado y Chroma en memoria: no llaman a OpenAI ni necesitan servicios levantados.

## Estructura

```
agent/       tutor (grafo, prompts, control de filtración, ejecutor con guardrails)
course/      reglas AR → SQL, forma canónica, prácticas, búsqueda en apuntes
ingest/      ingesta batch (prácticas, soluciones, apuntes)
storage/     SQLite
guardrails/  seguridad y validación
frontend/    Flask y plantillas
tools/       configuración del LLM y carga de Docker secrets
deploy/      Caddyfile y guía de publicación
content/     material de la materia
scripts/     administración
test/        tests
```

## Seguridad

Los secretos (`OPENAI_API_KEY`, `FLASK_SECRET_KEY`, certificados, claves SSH) nunca van al repositorio ni a la imagen de Docker: `.gitignore` y `.dockerignore` los excluyen. En producción se montan como Docker secrets y sólo el proxy publica puertos; el detalle de cada medida está en [deploy/README.md](deploy/README.md).
