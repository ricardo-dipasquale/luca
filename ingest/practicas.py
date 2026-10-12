"""Excel de programa y prácticas → artifacts/practicas.json (sin embeddings)."""

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


class IngestValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("La planilla tiene errores:\n" + "\n".join(f"  - {e}" for e in errors))
        self.errors = errors


@dataclass
class _Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def _as_list(value: Any) -> list:
    """Cells hold either a Python-literal list ("['a', 'b']") or a single plain value."""
    if _blank(value):
        return []
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return [value.strip()]
    return value if isinstance(value, list) else [value]


def _as_answers(value: Any) -> list[str]:
    if _blank(value):
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return [str(value)]
    # A JSON scalar (e.g. '"texto"') must stay one answer, not be iterated char by char.
    return [str(a) for a in parsed] if isinstance(parsed, list) else [str(parsed)]


def _as_id(value: Any) -> str:
    """Section/exercise ids: pandas reads 1 as 1.0 when the column has blanks."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _row(sheet: str, idx: int) -> str:
    return f"hoja '{sheet}', fila {idx + 2}"


def _text(value: Any) -> str | None:
    return None if _blank(value) else str(value).strip()


def _parse_programa(path: Path) -> dict:
    xls = pd.ExcelFile(path)
    cab = xls.parse("Cabecera")
    first = cab.iloc[0]
    temas_by_unit: dict[int, list[dict]] = {}
    for _, row in xls.parse("Temas").iterrows():
        temas_by_unit.setdefault(int(row["NumeroUnidadTematica"]), []).append(
            {"descripcion": str(row["Tema"]).strip(), "apuntes": [str(a) for a in _as_list(row.get("Apunte Relacionado"))]}
        )
    return {
        "nombre": str(first["Materia"]).strip(),
        "carrera": _text(first.get("Carrera")),
        "profesores": [str(p) for p in _as_list(first.get("Profesor"))],
        "objetivos": [str(o).strip() for o in xls.parse("Objetivos")["Objetivo"] if not _blank(o)],
        "unidades": [
            {"numero": int(r["Numero"]), "titulo": str(r["Titulo"]).strip(), "temas": temas_by_unit.get(int(r["Numero"]), [])}
            for _, r in xls.parse("UnidadesTematicas").iterrows()
        ],
    }


def _parse_practicas(path: Path, report: _Report) -> list[dict]:
    xls = pd.ExcelFile(path)
    practicas: dict[int, dict] = {}

    for idx, row in xls.parse("Cabecera").iterrows():
        props = {str(c).lower().replace(" ", "_"): row[c] for c in row.index}
        numero = int(props["numeropractica"])
        criterios = props.get("criterioscorreccion", props.get("criterios_correccion"))
        practicas[numero] = {
            "numero": numero,
            "titulo": _text(props.get("titulo")),
            "descripcion": _text(props.get("descripcion")),
            "objetivos": _text(props.get("objetivos")),
            "criterios_correccion": _text(criterios),
            "teoria_relacionada": [str(t) for t in _as_list(props.get("teoria_relacionada"))],
            "tips": [],
            "secciones": [],
        }
        if _blank(criterios):
            report.warnings.append(f"Práctica {numero} sin criterios de corrección ({_row('Cabecera', idx)})")

    for idx, row in xls.parse("TipsNivelPractica").iterrows():
        numero = int(row["NumeroPractica"])
        if numero not in practicas:
            report.errors.append(f"Tip para la práctica {numero}, que no está en Cabecera ({_row('TipsNivelPractica', idx)})")
        elif not _blank(row["Tip"]):
            practicas[numero]["tips"].append(str(row["Tip"]).strip())

    secciones: dict[tuple[int, str], dict] = {}
    for idx, row in xls.parse("Enunciado").iterrows():
        where = _row("Enunciado", idx)
        numero = int(row["NumeroPractica"])
        if numero not in practicas:
            report.errors.append(f"Fila de la práctica {numero}, que no está en Cabecera ({where})")
            continue
        sec_id = _as_id(row["Seccion"])
        tips = [str(t) for t in _as_list(row.get("Tips Nivel Ejercicio"))]

        if str(row["Tipo"]).strip().upper() == "S":
            if (numero, sec_id) in secciones:
                report.errors.append(f"Sección {numero}.{sec_id} repetida ({where})")
                continue
            seccion = {"numero": sec_id, "enunciado": _text(row["Enunciado"]), "tips": tips, "ejercicios": []}
            secciones[(numero, sec_id)] = seccion
            practicas[numero]["secciones"].append(seccion)
            continue

        seccion = secciones.get((numero, sec_id))
        if seccion is None:
            report.errors.append(f"Ejercicio de la sección {numero}.{sec_id}, que no tiene fila Tipo=S antes ({where})")
            continue
        ej_id = _as_id(row["Ejercicio"])
        if any(e["numero"] == ej_id for e in seccion["ejercicios"]):
            report.errors.append(f"Ejercicio {numero}.{sec_id}.{ej_id} repetido ({where})")
            continue
        respuestas = _as_answers(row["Respuesta"])
        if not respuestas:
            report.warnings.append(f"Ejercicio {numero}.{sec_id}.{ej_id} sin respuesta esperada ({where})")
        seccion["ejercicios"].append(
            {"numero": ej_id, "enunciado": _text(row["Enunciado"]), "respuestas": respuestas, "tips": tips}
        )

    return [practicas[n] for n in sorted(practicas)]


def build_practicas(programa_path: Path, practicas_path: Path) -> tuple[dict, list[str]]:
    """Returns (artifact, warnings). Raises IngestValidationError if the sheets are inconsistent."""
    report = _Report()
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "materia": _parse_programa(programa_path),
        "practicas": _parse_practicas(practicas_path, report),
    }
    if report.errors:
        raise IngestValidationError(report.errors)
    return artifact, report.warnings


def run(programa_path: Path, practicas_path: Path, output_path: Path) -> None:
    artifact, warnings = build_practicas(programa_path, practicas_path)
    for w in warnings:
        logger.warning(w)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    n_ej = sum(len(s["ejercicios"]) for p in artifact["practicas"] for s in p["secciones"])
    logger.info(
        f"practicas: {len(artifact['practicas'])} prácticas, {n_ej} ejercicios, "
        f"{len(warnings)} advertencias → {output_path}"
    )
