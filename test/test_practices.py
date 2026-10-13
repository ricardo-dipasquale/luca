"""Parity of ingest/practicas + course/practices against a snapshot of the old Neo4j KG output."""

import json
from pathlib import Path

import pandas as pd
import pytest

from course.practices import PracticeRepository
from ingest.__main__ import main as ingest_main
from ingest.practicas import IngestValidationError, build_practicas, run

SNAPSHOT = json.loads((Path(__file__).parent / "fixtures" / "kg_snapshot.json").read_text())
PROGRAMA_COLS = {
    "Cabecera": ["Materia", "Carrera", "Profesor"],
    "Objetivos": ["Objetivo"],
    "UnidadesTematicas": ["Numero", "Titulo"],
    "Temas": ["Tema", "NumeroUnidadTematica", "Apunte Relacionado"],
}
ENUNCIADO_COLS = ["Tipo", "NumeroPractica", "Seccion", "Ejercicio", "Enunciado", "Respuesta", "Tips Nivel Ejercicio"]


def _write_xlsx(path: Path, sheets: dict[str, list[dict]], columns: dict[str, list[str]]) -> Path:
    with pd.ExcelWriter(path) as w:
        for name, rows in sheets.items():
            pd.DataFrame(rows, columns=columns.get(name)).to_excel(w, sheet_name=name, index=False)
    return path


def _programa(tmp_path: Path, topics: list[str], apuntes: dict[str, str] | None = None) -> Path:
    apuntes = apuntes or {}
    return _write_xlsx(tmp_path / "Programa.xlsx", {
        "Cabecera": [{"Materia": SNAPSHOT["subjects"][0]["name"], "Carrera": "Ingeniería", "Profesor": "['A', 'B']"}],
        "Objetivos": [{"Objetivo": "Objetivo 1"}],
        "UnidadesTematicas": [{"Numero": 1, "Titulo": "Unidad 1"}],
        "Temas": [{"Tema": t, "NumeroUnidadTematica": 1, "Apunte Relacionado": apuntes.get(t)} for t in topics],
    }, PROGRAMA_COLS)


def _practicas_from_snapshot(tmp_path: Path) -> Path:
    """Rebuild the practices workbook, in the layout db/create_kg.py read, from the KG snapshot."""
    cabecera, tips_practica, enunciado = [], [], []
    for num, p in SNAPSHOT["practices"].items():
        d = p["details"]
        cabecera.append({"NumeroPractica": int(num), "Titulo": d["name"], "Descripcion": d["description"],
                         "Objetivos": d["objectives"], "Teoria Relacionada": str(d["topics"])})
        tips_practica += [{"NumeroPractica": int(num), "Tip": t["tip_text"]} for t in p["tips_practice_only"]]
        seen_sections = set()
        for ex in p["exercises"].values():
            e = ex["details"]
            sec = e["section_number"]
            if sec not in seen_sections:
                seen_sections.add(sec)
                sec_tips = [t["tip_text"] for t in p["section_tips"][sec] if t["level"] == "section"]
                enunciado.append({"Tipo": "S", "NumeroPractica": int(num), "Seccion": int(sec),
                                  "Enunciado": e["section_statement"],
                                  "Tips Nivel Ejercicio": str(sec_tips) if sec_tips else None})
            ex_tips = [t["tip_text"] for t in ex["tips"] if t["level"] == "exercise"]
            answers = e["answers"]
            enunciado.append({"Tipo": "E", "NumeroPractica": int(num), "Seccion": int(sec),
                              "Ejercicio": e["exercise_number"], "Enunciado": e["exercise_statement"],
                              "Respuesta": answers[0] if len(answers) == 1 else json.dumps(answers),
                              "Tips Nivel Ejercicio": str(ex_tips) if ex_tips else None})
    return _write_xlsx(tmp_path / "Prácticas Bases de Datos.xlsx", {
        "Cabecera": cabecera, "TipsNivelPractica": tips_practica, "Enunciado": enunciado,
    }, {"Enunciado": ENUNCIADO_COLS})


def _sorted_tips(tips: list[dict]) -> list[tuple]:
    return sorted((t["level"], t["section_number"] or "", t["exercise_number"] or "", t["tip_text"]) for t in tips)


def _assert_parity(repo: PracticeRepository) -> None:
    assert [s["name"] for s in repo.get_subjects()] == [s["name"] for s in SNAPSHOT["subjects"]]
    for num, p in SNAPSHOT["practices"].items():
        n = int(num)
        got, want = repo.get_practice_details(n), p["details"]
        assert {**got, "topics": sorted(got["topics"])} == {**want, "topics": sorted(want["topics"])}
        assert _sorted_tips(repo.get_practice_tips(n)) == _sorted_tips(p["tips_practice_only"])
        for sec, tips in p["section_tips"].items():
            assert _sorted_tips(repo.get_practice_tips(n, sec)) == _sorted_tips(tips), f"tips sección {sec}"
        for key, ex in p["exercises"].items():
            sec, ej = key.split(".", 1)
            assert repo.get_exercise_details(n, sec, ej) == ex["details"], key
            assert _sorted_tips(repo.get_practice_tips(n, sec, ej)) == _sorted_tips(ex["tips"]), key


@pytest.fixture
def repo_from_snapshot(tmp_path: Path) -> PracticeRepository:
    topics = next(iter(SNAPSHOT["practices"].values()))["details"]["topics"]
    out = tmp_path / "practicas.json"
    run(_programa(tmp_path, topics), _practicas_from_snapshot(tmp_path), out)
    return PracticeRepository(out)


def test_parity_with_kg_snapshot(repo_from_snapshot):
    _assert_parity(repo_from_snapshot)


def test_unknown_ids_return_none(repo_from_snapshot):
    assert repo_from_snapshot.get_practice_details(99) is None
    assert repo_from_snapshot.get_exercise_details(2, "1", "zz") is None
    assert repo_from_snapshot.get_exercise_details(2, "99", "a") is None
    assert repo_from_snapshot.get_practice_tips(99) == []


def test_missing_artifact_points_to_ingest(tmp_path):
    with pytest.raises(FileNotFoundError, match="python -m ingest"):
        PracticeRepository(tmp_path / "nope.json")


def _practicas_xlsx(tmp_path: Path, enunciado: list[dict], tips: list[dict] = (), teoria: str = "[]") -> Path:
    return _write_xlsx(tmp_path / "p.xlsx", {
        "Cabecera": [{"NumeroPractica": 1, "Titulo": "T", "Descripcion": "D", "Objetivos": "O", "Teoria Relacionada": teoria}],
        "TipsNivelPractica": list(tips) or [{"NumeroPractica": 1, "Tip": "tip"}],
        "Enunciado": enunciado,
    }, {"Enunciado": ENUNCIADO_COLS})


def _ejercicios(artifact: dict) -> dict[str, dict]:
    return {f"{s['numero']}.{e['numero']}": e
            for s in artifact["practicas"][0]["secciones"] for e in s["ejercicios"]}


def test_exercise_without_section_reports_sheet_and_row(tmp_path):
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 2, "Ejercicio": "a", "Enunciado": "E", "Respuesta": "R"},
    ])
    with pytest.raises(IngestValidationError, match=r"hoja 'Enunciado', fila 3"):
        build_practicas(_programa(tmp_path, []), xlsx)


def test_tip_for_unknown_practice_is_an_error(tmp_path):
    xlsx = _practicas_xlsx(tmp_path, [{"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"}],
                           tips=[{"NumeroPractica": 7, "Tip": "x"}])
    with pytest.raises(IngestValidationError, match="práctica 7"):
        build_practicas(_programa(tmp_path, []), xlsx)


def test_cell_normalization_and_warnings(tmp_path):
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1.0, "Enunciado": "S1"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1.0, "Ejercicio": "a", "Enunciado": "E", "Respuesta": '"una sola"'},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1.0, "Ejercicio": "b", "Enunciado": "E", "Respuesta": None},
    ])
    artifact, warnings = build_practicas(_programa(tmp_path, []), xlsx)
    seccion = artifact["practicas"][0]["secciones"][0]
    assert seccion["numero"] == "1"
    assert seccion["ejercicios"][0]["respuestas"] == ["una sola"]
    assert any("criterios de corrección" in w for w in warnings)


def test_deducir_respuesta_only_without_answer_and_without_any_tip(tmp_path):
    no_practice_tips = [{"NumeroPractica": 1, "Tip": None}]
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1, "Ejercicio": "a", "Enunciado": "E", "Respuesta": "R"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1, "Ejercicio": "b", "Enunciado": "E"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1, "Ejercicio": "c", "Enunciado": "E", "Tips Nivel Ejercicio": "pista"},
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 2, "Enunciado": "S2", "Tips Nivel Ejercicio": "tip de sección"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 2, "Ejercicio": "a", "Enunciado": "E"},
    ], tips=no_practice_tips)
    artifact, _ = build_practicas(_programa(tmp_path, []), xlsx)
    flags = {k: e["deducir_respuesta"] for k, e in _ejercicios(artifact).items()}
    assert flags == {"1.a": False, "1.b": True, "1.c": False, "2.a": False}


def test_practice_tip_counts_as_guidance(tmp_path):
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"},
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1, "Ejercicio": "a", "Enunciado": "E"},
    ])
    artifact, _ = build_practicas(_programa(tmp_path, []), xlsx)
    assert _ejercicios(artifact)["1.a"]["deducir_respuesta"] is False


def test_apuntes_relacionados_follow_teoria_relacionada(tmp_path):
    programa = _programa(tmp_path, ["Álgebra", "SQL", "Otro"], apuntes={
        "Álgebra": "['algebra.pdf', 'comun.pdf']", "SQL": "['sql.pdf', 'comun.pdf']", "Otro": "otro.pdf",
    })
    xlsx = _practicas_xlsx(tmp_path, [{"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"}],
                           teoria="['Álgebra', 'SQL', 'Inexistente']")
    artifact, warnings = build_practicas(programa, xlsx)
    assert artifact["practicas"][0]["apuntes_relacionados"] == ["algebra.pdf", "comun.pdf", "sql.pdf"]
    assert any("'Inexistente'" in w for w in warnings)


def test_blank_rows_are_skipped_and_named_practices_need_cabecera(tmp_path):
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"},
        {},
        {"Tipo": "S", "NumeroPractica": "Extra", "Seccion": 1, "Enunciado": "S1"},
    ])
    with pytest.raises(IngestValidationError) as exc:
        build_practicas(_programa(tmp_path, []), xlsx)
    assert exc.value.errors == ["La práctica Extra tiene ejercicios pero no fila en Cabecera (hoja 'Enunciado', fila 4)"]


def test_repeated_row_errors_are_grouped_into_ranges(tmp_path):
    ej = lambda e: {"Tipo": "E", "NumeroPractica": 4, "Seccion": 1, "Ejercicio": e, "Enunciado": "E"}
    xlsx = _practicas_xlsx(tmp_path, [
        {"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"},
        ej("1"), ej("2"), ej("3"),
        {"Tipo": "E", "NumeroPractica": 1, "Seccion": 1, "Ejercicio": "a", "Enunciado": "E"},
        ej("4"),
    ])
    with pytest.raises(IngestValidationError) as exc:
        build_practicas(_programa(tmp_path, []), xlsx)
    assert exc.value.errors == ["La práctica 4 tiene ejercicios pero no fila en Cabecera (hoja 'Enunciado', filas 3-5, 7)"]


def test_named_practice_with_cabecera_is_ingested_after_numbered_ones(tmp_path):
    path = _write_xlsx(tmp_path / "p.xlsx", {
        "Cabecera": [{"NumeroPractica": "Extra", "Titulo": "X"}, {"NumeroPractica": 2, "Titulo": "Dos"}],
        "TipsNivelPractica": [{"NumeroPractica": 2, "Tip": "t"}],
        "Enunciado": [{"Tipo": "S", "NumeroPractica": "Extra", "Seccion": 1, "Enunciado": "S"}],
    }, {"Enunciado": ENUNCIADO_COLS})
    artifact, _ = build_practicas(_programa(tmp_path, []), path)
    assert [p["numero"] for p in artifact["practicas"]] == [2, "Extra"]


def test_teoria_relacionada_can_name_note_files_directly(tmp_path):
    (tmp_path / "apuntes").mkdir()
    (tmp_path / "apuntes" / "taller.pdf").touch()
    programa = _programa(tmp_path, ["Álgebra"], apuntes={"Álgebra": "['algebra.pdf']"})
    xlsx = _practicas_xlsx(tmp_path, [{"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"}],
                           teoria="['Álgebra', 'taller.pdf', 'falta.pdf']")
    artifact, warnings = build_practicas(programa, xlsx, apuntes_dir=tmp_path / "apuntes")
    assert artifact["practicas"][0]["apuntes_relacionados"] == ["algebra.pdf", "taller.pdf", "falta.pdf"]
    assert any("'falta.pdf' de Teoria Relacionada no está" in w for w in warnings)


def test_missing_apunte_files_are_reported(tmp_path):
    (tmp_path / "apuntes").mkdir()
    (tmp_path / "apuntes" / "algebra.pdf").touch()
    programa = _programa(tmp_path, ["Álgebra"], apuntes={"Álgebra": "['algebra.pdf', 'no-existe.pdf']"})
    xlsx = _practicas_xlsx(tmp_path, [{"Tipo": "S", "NumeroPractica": 1, "Seccion": 1, "Enunciado": "S1"}])
    _, warnings = build_practicas(programa, xlsx, apuntes_dir=tmp_path / "apuntes")
    assert [w for w in warnings if "apunte" in w] == [
        f"El apunte 'no-existe.pdf' (columna Apunte Relacionado de Temas) no está en {tmp_path / 'apuntes'}"
    ]


def test_cli_fails_clearly_without_sources(tmp_path, caplog):
    assert ingest_main(["--content", str(tmp_path), "--artifacts", str(tmp_path / "out")]) == 1
    assert "Copiá los originales" in caplog.text
