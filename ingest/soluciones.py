"""Paso `soluciones`: AR (si la planilla no la trae) y SQL ANSI derivado del AR, por ejercicio.

El resultado vive en content/soluciones_generadas.json, versionado, para que el docente lo revise:
- estado "pendiente": generado y sin revisar; se regenera si cambian sus entradas o con --force.
- estado "aprobada": revisado por el docente; nunca se regenera. Si cambian sus entradas pasa a
  "desactualizada" para que el docente lo revise (--force lo regenera).
"""

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Iterator

import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify

from course.rules import ALL_RULES

logger = logging.getLogger(__name__)

PENDIENTE, APROBADA, DESACTUALIZADA = "pendiente", "aprobada", "desactualizada"
MAX_EJEMPLOS = 5
CONCURRENCIA = 6


class Solucion(BaseModel):
    ar: str = Field(description="Solución en álgebra relacional, con la notación de los ejemplos")
    sql: str = Field(description="Sólo la consulta SQL ANSI derivada del AR, sin texto adicional; vacío si no se puede resolver")
    observaciones: str = Field(
        default="",
        description="Problemas detectados para el docente (consigna incompleta, error en la solución oficial); vacío si no hay",
    )


def _ejercicios(artifact: dict) -> Iterator[tuple[dict, dict, dict, str]]:
    for p in artifact["practicas"]:
        for s in p["secciones"]:
            for e in s["ejercicios"]:
                yield p, s, e, f"{p['numero']}.{s['numero']}.{e['numero']}"


def _hash_entradas(seccion: dict, ejercicio: dict) -> str:
    payload = json.dumps([seccion["enunciado"], ejercicio["enunciado"], ejercicio["respuestas"]], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def section_schema(seccion_enunciado: str | None) -> dict[str, dict[str, str]]:
    """{tabla: {columna: tipo}} from the CREATE TABLE statements in a section statement (empty if none)."""
    schema: dict[str, dict[str, str]] = {}
    for stmt in re.findall(r"CREATE TABLE.*?\)\s*;", seccion_enunciado or "", flags=re.S | re.I):
        try:
            create = sqlglot.parse_one(stmt, read="mysql")
        except sqlglot.errors.SqlglotError as e:
            logger.warning(f"No se pudo leer un CREATE TABLE de la sección; se valida solo la sintaxis: {e}")
            return {}
        schema[create.this.this.name] = {
            c.name: c.args["kind"].sql() for c in create.this.expressions if isinstance(c, exp.ColumnDef)
        }
    return schema


def validate_sql(sql: str, schema: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Syntax always; tables and columns too when the section has a schema. Dialect-agnostic: nothing is executed."""
    if not sql.strip():
        return {"ok": False, "nivel": "sintaxis", "detalle": "sin SQL (ver observaciones)"}
    try:
        sentencias = sqlglot.parse(sql)
        if not schema:
            return {"ok": True, "nivel": "sintaxis", "detalle": "sin CREATE TABLE en la sección: solo se validó la sintaxis"}
        for sentencia in sentencias:
            ctes = {c.alias_or_name for c in sentencia.find_all(exp.CTE)}
            desconocidas = {t.name for t in sentencia.find_all(exp.Table)} - set(schema) - ctes
            if desconocidas:
                return {"ok": False, "nivel": "esquema", "detalle": f"tablas inexistentes: {', '.join(sorted(desconocidas))}"}
            qualify(sentencia, schema=schema, validate_qualify_columns=True)
    except sqlglot.errors.ParseError as e:
        return {"ok": False, "nivel": "sintaxis", "detalle": str(e).splitlines()[0]}
    except sqlglot.errors.SqlglotError as e:
        return {"ok": False, "nivel": "esquema", "detalle": str(e).splitlines()[0]}
    return {"ok": True, "nivel": "esquema", "detalle": "tablas y columnas verificadas contra el esquema de la sección"}


def _ejemplos(artifact: dict, practica: dict, excluir: str) -> list[tuple[str, str]]:
    """Solved exercises to show the notation: same practice first, then the others."""
    propios, otros = [], []
    for p, _, e, key in _ejercicios(artifact):
        if key != excluir and e["respuestas"]:
            (propios if p is practica else otros).append((e["enunciado"], e["respuestas"][0]))
    return (propios + otros)[:MAX_EJEMPLOS]


def _prompt(artifact: dict, p: dict, s: dict, e: dict, key: str) -> list[tuple[str, str]]:
    system = (
        "Sos docente de Bases de Datos. Resolvés ejercicios en álgebra relacional y SQL ANSI "
        "siguiendo estrictamente estas reglas.\n\n" + ALL_RULES
    )
    if p.get("criterios_correccion"):
        system += f"\nCRITERIOS DE CORRECCIÓN DE LA PRÁCTICA\n{p['criterios_correccion']}\n"
    ejemplos = "\n".join(f"- Enunciado: {en}\n  AR: {ar}" for en, ar in _ejemplos(artifact, p, key))
    user = f"ESQUEMA Y CONSIGNA DE LA SECCIÓN\n{s['enunciado']}\n\n"
    if ejemplos:
        user += f"EJERCICIOS RESUELTOS (seguí esta notación de AR)\n{ejemplos}\n\n"
    user += f"EJERCICIO\n{e['enunciado']}\n\n"
    if e["respuestas"]:
        user += (
            f"SOLUCIÓN OFICIAL EN AR (no la cambies)\n{e['respuestas'][0]}\n\n"
            "Devolvé en `ar` esa misma solución y en `sql` la consulta SQL ANSI derivada de ella, operador por operador."
        )
    else:
        user += "Resolvé primero en AR y derivá el SQL ANSI de esa solución, operador por operador."
    user += (
        "\n\n`sql` lleva sólo la consulta, sin explicaciones. Si la consigna está incompleta o la solución oficial "
        "tiene un error (por ejemplo, no coincide con el esquema), explicalo en `observaciones` para el docente."
    )
    return [("system", system), ("user", user)]


def _load(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save(path: Path, entradas: dict[str, dict]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(entradas.items())), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


async def _generate(artifact: dict, path: Path, llm: Any, modelo: str, force: bool) -> dict[str, int]:
    entradas = _load(path)
    vigentes = set()
    pendientes = []
    stats = {"generadas": 0, "sin_cambios": 0, "aprobadas": 0, "desactualizadas": 0, "fallidas": 0, "eliminadas": 0}

    for p, s, e, key in _ejercicios(artifact):
        vigentes.add(key)
        h = _hash_entradas(s, e)
        entrada = entradas.get(key)
        if entrada and entrada["estado"] == APROBADA:
            if entrada["hash_entradas"] != h:
                entrada["estado"] = DESACTUALIZADA
                logger.warning(f"{key}: cambió el enunciado de una solución aprobada; quedó 'desactualizada' para revisar")
            stats["aprobadas"] += 1
            continue
        if entrada and entrada["estado"] == DESACTUALIZADA and not force:
            stats["desactualizadas"] += 1
            continue
        if entrada and entrada["hash_entradas"] == h and not force:
            stats["sin_cambios"] += 1
            continue
        pendientes.append((p, s, e, key, h))

    for key in sorted(set(entradas) - vigentes):
        logger.warning(f"{key}: el ejercicio ya no existe en la planilla; se elimina su solución generada")
        del entradas[key]
        stats["eliminadas"] += 1

    sem = asyncio.Semaphore(CONCURRENCIA)
    schemas: dict[int, dict] = {}

    async def resolver(p: dict, s: dict, e: dict, key: str, h: str) -> None:
        schema = schemas.setdefault(id(s), section_schema(s["enunciado"]))
        async with sem:
            try:
                messages = _prompt(artifact, p, s, e, key)
                sol: Solucion = await llm.ainvoke(messages)
                validacion = validate_sql(sol.sql, schema)
                if sol.sql.strip() and not validacion["ok"]:
                    # One correction round with the validator's error; usually a column in the wrong table.
                    sol = await llm.ainvoke(messages + [
                        ("assistant", sol.sql),
                        ("user", f"Ese SQL no es válido para el esquema: {validacion['detalle']}. Corregilo."),
                    ])
            except Exception as exc:
                logger.error(f"{key}: no se pudo generar la solución ({exc})")
                stats["fallidas"] += 1
                return
        entradas[key] = {
            "practica": p["numero"],
            "seccion": s["numero"],
            "ejercicio": e["numero"],
            "enunciado": e["enunciado"],
            "ar": None if e["respuestas"] else sol.ar,
            "origen_ar": "planilla" if e["respuestas"] else "generada",
            "sql": sol.sql.strip(),
            "observaciones": sol.observaciones.strip(),
            "estado": PENDIENTE,
            "hash_entradas": h,
            "modelo": modelo,
        }
        stats["generadas"] += 1
        _save(path, entradas)
        logger.info(f"{key}: solución generada ({stats['generadas']}/{len(pendientes)})")

    await asyncio.gather(*(resolver(*args) for args in pendientes))

    # Revalidate everything: the teacher may have edited SQL by hand.
    secciones = {key: s for _, s, _, key in _ejercicios(artifact)}
    for key, entrada in entradas.items():
        s = secciones[key]
        schema = schemas.setdefault(id(s), section_schema(s["enunciado"]))
        entrada["validacion"] = validate_sql(entrada["sql"], schema)
    _save(path, entradas)
    return stats


def generate(artifact: dict, path: Path, llm_factory: Callable[[], Any], modelo: str, force: bool = False) -> dict[str, int]:
    stats = asyncio.run(_generate(artifact, path, llm_factory(), modelo, force))
    invalidas = sum(1 for e in _load(path).values() if not e["validacion"]["ok"])
    logger.info(
        f"soluciones: {stats['generadas']} generadas, {stats['sin_cambios']} sin cambios, "
        f"{stats['aprobadas']} aprobadas, {stats['desactualizadas']} desactualizadas, "
        f"{stats['fallidas']} fallidas, {invalidas} con SQL inválido → {path}"
    )
    return stats


def merge(artifact: dict, path: Path) -> None:
    """Attach the reference solution (AR + SQL) to each exercise of the practices artifact."""
    entradas = _load(path)
    for _, _, e, key in _ejercicios(artifact):
        entrada = entradas.get(key)
        ar = list(e["respuestas"]) or ([entrada["ar"]] if entrada and entrada.get("ar") else [])
        e["solucion"] = {
            "ar": ar,
            "origen_ar": "planilla" if e["respuestas"] else ("generada" if ar else None),
            "sql": entrada["sql"] if entrada else None,
            "estado": entrada["estado"] if entrada else None,
            "sql_valido": entrada["validacion"]["ok"] if entrada and "validacion" in entrada else None,
        }


def default_llm_factory() -> Any:
    from tools.llm_config import create_default_llm

    return create_default_llm().with_structured_output(Solucion)
