"""Excel de programa y prácticas → artifacts/practicas.json (sin embeddings)."""

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2


class IngestValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("La planilla tiene errores:\n" + "\n".join(f"  - {e}" for e in errors))
        self.errors = errors


@dataclass
class _Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _grouped: dict[tuple[str, str], list[int]] = field(default_factory=dict)

    def row_error(self, message: str, sheet: str, idx: int) -> None:
        """Same problem on many rows (e.g. a whole practice missing in Cabecera) → one line with a row range."""
        self._grouped.setdefault((message, sheet), []).append(idx + 2)

    def all_errors(self) -> list[str]:
        grouped = [f"{msg} (hoja '{sheet}', {_row_ranges(rows)})" for (msg, sheet), rows in self._grouped.items()]
        return grouped + self.errors


def _row_ranges(rows: list[int]) -> str:
    spans: list[list[int]] = []
    for r in sorted(rows):
        if spans and r == spans[-1][1] + 1:
            spans[-1][1] = r
        else:
            spans.append([r, r])
    text = ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)
    return f"fila {text}" if len(rows) == 1 else f"filas {text}"


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


def _practice_id(value: Any) -> int | str:
    """Practices are numbered, but the sheets may also name one (e.g. "Extra")."""
    text = _as_id(value)
    return int(text) if text.isdigit() else text


def _rows(xls: pd.ExcelFile, sheet: str):
    """Rows with at least one value; hand-edited sheets use blank rows as separators."""
    for idx, row in xls.parse(sheet).iterrows():
        if not all(_blank(v) for v in row):
            yield idx, row


def _row(sheet: str, idx: int) -> str:
    return f"hoja '{sheet}', fila {idx + 2}"


def _text(value: Any) -> str | None:
    return None if _blank(value) else str(value).strip()


def _parse_programa(path: Path) -> dict:
    xls = pd.ExcelFile(path)
    cab = xls.parse("Cabecera")
    first = cab.iloc[0]
    temas_by_unit: dict[int, list[dict]] = {}
    for _, row in _rows(xls, "Temas"):
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
            for _, r in _rows(xls, "UnidadesTematicas")
        ],
    }


def _parse_practicas(path: Path, report: _Report) -> list[dict]:
    xls = pd.ExcelFile(path)
    practicas: dict[int | str, dict] = {}

    for idx, row in _rows(xls, "Cabecera"):
        props = {str(c).lower().replace(" ", "_"): row[c] for c in row.index}
        numero = _practice_id(props["numeropractica"])
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

    for idx, row in _rows(xls, "TipsNivelPractica"):
        numero = _practice_id(row["NumeroPractica"])
        if numero not in practicas:
            report.row_error(f"La práctica {numero} tiene tips pero no fila en Cabecera", "TipsNivelPractica", idx)
        elif not _blank(row["Tip"]):
            practicas[numero]["tips"].append(str(row["Tip"]).strip())

    secciones: dict[tuple[int | str, str], dict] = {}
    for idx, row in _rows(xls, "Enunciado"):
        where = _row("Enunciado", idx)
        numero = _practice_id(row["NumeroPractica"])
        if numero not in practicas:
            report.row_error(f"La práctica {numero} tiene ejercicios pero no fila en Cabecera", "Enunciado", idx)
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
            report.row_error(f"La sección {numero}.{sec_id} tiene ejercicios pero no fila Tipo=S antes", "Enunciado", idx)
            continue
        ej_id = _as_id(row["Ejercicio"])
        if any(e["numero"] == ej_id for e in seccion["ejercicios"]):
            report.errors.append(f"Ejercicio {numero}.{sec_id}.{ej_id} repetido ({where})")
            continue
        seccion["ejercicios"].append({
            "numero": ej_id,
            "enunciado": _text(row["Enunciado"]),
            "respuestas": _as_answers(row["Respuesta"]),
            "tips": tips,
        })

    for p in practicas.values():
        for s in p["secciones"]:
            for e in s["ejercicios"]:
                # Nothing to guide the agent: it must infer the answer from the practice's rules,
                # the other exercises and the related notes.
                e["deducir_respuesta"] = not (e["respuestas"] or e["tips"] or s["tips"] or p["tips"])

    # Numbered practices first, in order; named ones (e.g. "Extra") after.
    return [practicas[n] for n in sorted(practicas, key=lambda n: (isinstance(n, str), str(n).zfill(6)))]


_APUNTE_SUFFIXES = (".pdf", ".md")


def _link_apuntes(materia: dict, practicas: list[dict], report: _Report) -> None:
    """Teoria Relacionada may name program topics (→ their notes) or note files directly."""
    apuntes_por_tema = {t["descripcion"]: t["apuntes"] for u in materia["unidades"] for t in u["temas"]}
    for p in practicas:
        apuntes: list[str] = []
        for ref in p["teoria_relacionada"]:
            if ref in apuntes_por_tema:
                nuevos = apuntes_por_tema[ref]
            elif ref.lower().endswith(_APUNTE_SUFFIXES):
                nuevos = [ref]
            else:
                report.warnings.append(f"Práctica {p['numero']}: '{ref}' de Teoria Relacionada no es un tema del programa ni un apunte (.pdf/.md)")
                continue
            apuntes += [a for a in nuevos if a not in apuntes]
        p["apuntes_relacionados"] = apuntes


def _check_apuntes_exist(materia: dict, practicas: list[dict], apuntes_dir: Path, report: _Report) -> None:
    existentes = {p.name for p in apuntes_dir.iterdir()} if apuntes_dir.is_dir() else set()
    del_programa = {a for u in materia["unidades"] for t in u["temas"] for a in t["apuntes"]}
    for faltante in sorted(del_programa - existentes):
        report.warnings.append(f"El apunte '{faltante}' (columna Apunte Relacionado de Temas) no está en {apuntes_dir}")
    for p in practicas:
        for faltante in [a for a in p["apuntes_relacionados"] if a not in existentes and a not in del_programa]:
            report.warnings.append(f"Práctica {p['numero']}: el apunte '{faltante}' de Teoria Relacionada no está en {apuntes_dir}")


def build_practicas(
    programa_path: Path, practicas_path: Path, apuntes_dir: Path | None = None
) -> tuple[dict, list[str]]:
    """Returns (artifact, warnings). Raises IngestValidationError if the sheets are inconsistent."""
    report = _Report()
    materia = _parse_programa(programa_path)
    practicas = _parse_practicas(practicas_path, report)
    _link_apuntes(materia, practicas, report)
    if apuntes_dir is not None:
        _check_apuntes_exist(materia, practicas, apuntes_dir, report)
    artifact = {"schema_version": SCHEMA_VERSION, "materia": materia, "practicas": practicas}
    if errors := report.all_errors():
        raise IngestValidationError(errors)
    return artifact, report.warnings


def run(programa_path: Path, practicas_path: Path, output_path: Path, apuntes_dir: Path | None = None) -> None:
    artifact, warnings = build_practicas(programa_path, practicas_path, apuntes_dir)
    for w in warnings:
        logger.warning(w)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    ejercicios = [e for p in artifact["practicas"] for s in p["secciones"] for e in s["ejercicios"]]
    con_respuesta = sum(1 for e in ejercicios if e["respuestas"])
    a_deducir = sum(1 for e in ejercicios if e["deducir_respuesta"])
    logger.info(
        f"practicas: {len(artifact['practicas'])} prácticas, {len(ejercicios)} ejercicios "
        f"({con_respuesta} con respuesta, {len(ejercicios) - con_respuesta - a_deducir} solo con tips, "
        f"{a_deducir} a deducir), {len(warnings)} advertencias → {output_path}"
    )
