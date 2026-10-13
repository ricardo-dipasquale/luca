# Ingesta de contenido (`python -m ingest`)

La ingesta es una rutina batch: toma el material de la materia en `content/` y genera lo que la aplicación usa en ejecución. La aplicación nunca lee las planillas ni los PDF directamente.

| Paso | Lee | Genera | Usa el LLM |
|---|---|---|---|
| `practicas` | `content/Programa.xlsx`, `content/Prácticas Bases de Datos.xlsx` | `artifacts/practicas.json` | No |
| `soluciones` | las prácticas ya leídas | `content/soluciones_generadas.json` | Sí (`DEFAULT_LLM_MODEL`) |
| `apuntes` | `content/apuntes/*.pdf`, `*.md` | colección `apuntes` en Chroma | Sólo embeddings (`EMBEDDING_MODEL`) |

`practicas` corre siempre, aunque se pida otro paso, porque los demás necesitan las prácticas leídas.

## Comandos habituales

```bash
python -m ingest                                  # los tres pasos; sólo regenera lo que cambió
python -m ingest --only practicas                 # corregiste la planilla (tips, criterios); no llama al LLM
python -m ingest --only soluciones                # genera soluciones de ejercicios nuevos o modificados
python -m ingest --only soluciones --regenerar-no-conformes   # cambiaron las reglas AR/SQL
python -m ingest --only apuntes                   # agregaste, cambiaste o borraste un apunte
python -m ingest --only apuntes --force           # cambiaste el modelo de embeddings o el fragmentado
```

El paso `apuntes` necesita Chroma levantado: `docker compose up -d chroma`.

> **Cuidado con `--force` sin `--only`.** `--force` se aplica a todos los pasos que corren: regenera todas las soluciones no aprobadas (107 llamadas al LLM) y además recrea la colección de apuntes. Usalo siempre junto con `--only`.

## Soluciones: cuándo se regeneran

Cada ejercicio tiene una entrada en `content/soluciones_generadas.json` (clave `práctica.sección.ejercicio`, por ejemplo `4.1.12` o `Extra.1.a`). El paso genera:

- el **AR** sólo si la planilla no trae `Respuesta`;
- el **SQL ANSI** siempre, derivado del AR operador por operador según la forma canónica de `course/rules.py`.

La entrada guarda un `hash_entradas` calculado sobre el enunciado de la sección (el esquema), el enunciado del ejercicio y la respuesta de la planilla. Qué pasa con cada entrada según su `estado`:

| `estado` | Sin cambios en la planilla | Cambió el enunciado o la respuesta | Con `--force` | Con `--regenerar-no-conformes` |
|---|---|---|---|---|
| `pendiente` | se conserva | **se regenera** | **se regenera** | **se regenera si no cumple las reglas** |
| `aprobada` | se conserva | se conserva y pasa a `desactualizada` | se conserva | se conserva |
| `desactualizada` | se conserva | se conserva | **se regenera** (como `pendiente`) | se conserva |

Además:

- Si se borra un ejercicio de la planilla, su entrada se elimina del archivo (queda en el historial de git).
- Si cambian las reglas o el prompt, nada se regenera solo porque el hash no los incluye. Usá `--regenerar-no-conformes` para rehacer únicamente las que no cumplen las reglas nuevas, o `--force` para rehacer todas las no aprobadas.
- Una entrada que falla la generación (por ejemplo, un error de la API) no se escribe; la próxima corrida la vuelve a intentar.

## Revisar y aprobar soluciones

Cada entrada tiene estos campos para la revisión:

- `validacion`: el SQL se valida con `sqlglot`, sin ejecutarlo. Si la sección trae `CREATE TABLE` (práctica 4), se verifican tablas y columnas contra ese esquema, incluidas las vistas que cree la propia solución. Si no, sólo la sintaxis.
- `forma_canonica`: si el SQL respeta la traducción canónica del AR: ∪ → `UNION`, ∩ → `INTERSECT`, − → `EXCEPT`, ÷ → doble `NOT EXISTS` con la plantilla del Taller #8, sin bloques `WITH` y sin orden en el AR.
- `observaciones`: problemas que el modelo detectó en la consigna o en la solución oficial (enunciados ambiguos o incompletos, errores de la planilla).

Si una solución generada falla `validacion` o `forma_canonica`, el modelo recibe el error y la corrige una vez antes de guardarla.

Para revisar:

1. Leé `ar`, `sql` y `observaciones`. Si hace falta, corregí el `sql` (o el `ar`) a mano en el JSON.
2. Cambiá `estado` a `"aprobada"`. Desde ese momento la ingesta no la vuelve a generar.
3. Corré `python -m ingest --only soluciones`: revalida todas las entradas, también las editadas a mano, y vuelve a armar `artifacts/practicas.json`.
4. Si una aprobada pasa a `desactualizada` (cambió su enunciado), revisala de nuevo: volvé a aprobarla, corregila o pasala a `pendiente` para que se regenere.

Commiteá `content/soluciones_generadas.json` después de revisar: es la fuente de las soluciones de referencia del agente.

## Apuntes: cuándo se reindexan

El hash SHA-256 de cada archivo queda en la metadata de sus fragmentos en Chroma:

- archivo nuevo o modificado: se borran sus fragmentos anteriores y se vuelve a embeber;
- archivo sin cambios: no se toca;
- archivo borrado de `content/apuntes`: se borran sus fragmentos.

La colección guarda el modelo de embeddings y los parámetros de fragmentado. Si cambian, la ingesta se niega a mezclar fragmentos incompatibles y pide `--only apuntes --force`, que recrea la colección desde cero.
