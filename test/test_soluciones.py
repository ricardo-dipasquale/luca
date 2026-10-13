import json
from pathlib import Path

import pytest

from ingest import soluciones
from ingest.soluciones import APROBADA, DESACTUALIZADA, Solucion

DDL = "Resolver para: CREATE TABLE oficina (codigo VARCHAR(10) NOT NULL, ciudad VARCHAR(30), PRIMARY KEY (codigo));"


def _artifact(seccion=DDL, enunciado_b="Ciudades de las oficinas") -> dict:
    return {"practicas": [{
        "numero": 1, "criterios_correccion": "Usar junta, no producto.",
        "secciones": [{"numero": "1", "enunciado": seccion, "ejercicios": [
            {"numero": "a", "enunciado": "Códigos de oficina", "respuestas": ["π_{codigo}(oficina)"]},
            {"numero": "b", "enunciado": enunciado_b, "respuestas": []},
        ]}],
    }]}


class FakeLLM:
    def __init__(self, sql="SELECT DISTINCT ciudad FROM oficina", fail_on=None):
        self.calls: list[str] = []
        self.sql, self.fail_on = sql, fail_on

    async def ainvoke(self, messages):
        user = messages[-1][1]
        self.calls.append(user)
        if self.fail_on and self.fail_on in user:
            raise RuntimeError("rate limit")
        return Solucion(ar="π_{ciudad}(oficina)", sql=self.sql)


def _run(artifact, path, llm, force=False):
    return soluciones.generate(artifact, path, lambda: llm, modelo="test-model", force=force)


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "soluciones_generadas.json"


def _entries(path: Path) -> dict:
    return json.loads(path.read_text())


def test_generates_sql_for_official_ar_and_ar_plus_sql_when_missing(path):
    llm = FakeLLM()
    _run(_artifact(), path, llm)
    e = _entries(path)
    assert e["1.1.a"]["ar"] is None and e["1.1.a"]["origen_ar"] == "planilla"
    assert e["1.1.b"]["ar"] == "π_{ciudad}(oficina)" and e["1.1.b"]["origen_ar"] == "generada"
    assert all(x["estado"] == "pendiente" and x["modelo"] == "test-model" for x in e.values())
    official_prompt = next(c for c in llm.calls if "Códigos de oficina" in c)
    assert "SOLUCIÓN OFICIAL EN AR (no la cambies)\nπ_{codigo}(oficina)" in official_prompt


def test_prompt_carries_rules_criteria_and_solved_examples(path):
    captured = []

    class Capture(FakeLLM):
        async def ainvoke(self, messages):
            captured.append(messages)
            return await super().ainvoke(messages)

    _run(_artifact(), path, Capture())
    system, user = next(m for m in captured if "Ciudades" in m[-1][1])
    assert "doble NOT EXISTS" in system[1] and "Usar junta, no producto." in system[1]
    assert "Enunciado: Códigos de oficina\n  AR: π_{codigo}(oficina)" in user[1]


def test_unchanged_inputs_are_not_regenerated(path):
    _run(_artifact(), path, FakeLLM())
    llm = FakeLLM()
    stats = _run(_artifact(), path, llm)
    assert llm.calls == [] and stats["sin_cambios"] == 2


def test_changed_pending_entry_is_regenerated(path):
    _run(_artifact(), path, FakeLLM())
    llm = FakeLLM()
    _run(_artifact(enunciado_b="Ciudades de España"), path, llm)
    assert len(llm.calls) == 1 and "Ciudades de España" in llm.calls[0]


def test_approved_entries_are_never_overwritten(path):
    _run(_artifact(), path, FakeLLM())
    entries = _entries(path)
    entries["1.1.b"].update(estado=APROBADA, sql="SELECT DISTINCT ciudad FROM oficina ORDER BY ciudad")
    path.write_text(json.dumps(entries))

    llm = FakeLLM(sql="SELECT 'otra cosa'")
    _run(_artifact(), path, llm, force=True)
    assert not any("Ciudades" in c for c in llm.calls)
    assert _entries(path)["1.1.b"]["sql"].endswith("ORDER BY ciudad")

    _run(_artifact(enunciado_b="Ciudades de España"), path, FakeLLM())
    assert _entries(path)["1.1.b"]["estado"] == DESACTUALIZADA


def test_sql_is_validated_against_the_section_schema(path):
    _run(_artifact(), path, FakeLLM(sql="SELECT DISTINCT pais FROM oficina"))
    v = _entries(path)["1.1.b"]["validacion"]
    assert v["ok"] is False and v["nivel"] == "esquema" and "pais" in v["detalle"]

    _run(_artifact(), path, FakeLLM(), force=True)
    assert _entries(path)["1.1.b"]["validacion"] == {
        "ok": True, "nivel": "esquema", "detalle": "tablas y columnas verificadas contra el esquema de la sección"}


def test_without_ddl_only_syntax_is_checked(path):
    _run(_artifact(seccion="OFICINA (codigo, ciudad)"), path, FakeLLM(sql="SELECT * FROM ("))
    assert _entries(path)["1.1.b"]["validacion"]["nivel"] == "sintaxis"
    assert _entries(path)["1.1.b"]["validacion"]["ok"] is False


def test_hand_edited_sql_is_revalidated(path):
    _run(_artifact(), path, FakeLLM())
    entries = _entries(path)
    entries["1.1.b"].update(estado=APROBADA, sql="SELECT nada FROM oficina")
    path.write_text(json.dumps(entries))
    _run(_artifact(), path, FakeLLM())
    assert _entries(path)["1.1.b"]["validacion"]["ok"] is False


def test_one_failure_does_not_lose_the_rest(path):
    stats = _run(_artifact(), path, FakeLLM(fail_on="Ciudades"))
    assert stats["fallidas"] == 1 and stats["generadas"] == 1
    assert set(_entries(path)) == {"1.1.a"}


def test_entries_of_removed_exercises_are_dropped(path):
    _run(_artifact(), path, FakeLLM())
    art = _artifact()
    art["practicas"][0]["secciones"][0]["ejercicios"].pop()
    stats = _run(art, path, FakeLLM())
    assert stats["eliminadas"] == 1 and set(_entries(path)) == {"1.1.a"}


def test_merge_attaches_reference_solution(path):
    _run(_artifact(), path, FakeLLM())
    art = _artifact()
    soluciones.merge(art, path)
    a, b = art["practicas"][0]["secciones"][0]["ejercicios"]
    assert a["solucion"]["ar"] == ["π_{codigo}(oficina)"] and a["solucion"]["origen_ar"] == "planilla"
    assert b["solucion"]["ar"] == ["π_{ciudad}(oficina)"] and b["solucion"]["origen_ar"] == "generada"
    assert b["solucion"]["sql"] == "SELECT DISTINCT ciudad FROM oficina" and b["solucion"]["sql_valido"] is True


def test_merge_without_generated_file_leaves_sql_empty(path):
    art = _artifact()
    soluciones.merge(art, path)
    b = art["practicas"][0]["secciones"][0]["ejercicios"][1]
    assert b["solucion"] == {"ar": [], "origen_ar": None, "sql": None, "estado": None, "sql_valido": None, "sql_canonico": None}


def test_ansi_functions_unsupported_by_sqlite_are_accepted():
    schema = soluciones.section_schema("CREATE TABLE pago (fecha_pago date NOT NULL, total NUMERIC(15,2));")
    sql = "SELECT EXTRACT(YEAR FROM fecha_pago) AS anio, SUM(total) FROM pago GROUP BY EXTRACT(YEAR FROM fecha_pago)"
    assert soluciones.validate_sql(sql, schema)["ok"] is True


def test_unknown_table_is_reported():
    schema = soluciones.section_schema(DDL)
    v = soluciones.validate_sql("SELECT * FROM empleado", schema)
    assert v == {"ok": False, "nivel": "esquema", "detalle": "tablas inexistentes: empleado"}


def test_observations_are_kept_apart_from_sql(path):
    class Incompleta(FakeLLM):
        async def ainvoke(self, messages):
            return Solucion(ar="", sql="", observaciones="La consigna no indica el prefijo.")

    _run(_artifact(), path, Incompleta())
    b = _entries(path)["1.1.b"]
    assert b["observaciones"] == "La consigna no indica el prefijo."
    assert b["validacion"] == {"ok": False, "nivel": "sintaxis", "detalle": "sin SQL (ver observaciones)"}


def test_invalid_sql_gets_one_correction_round_with_the_error(path):
    class FirstWrong(FakeLLM):
        async def ainvoke(self, messages):
            self.calls.append(messages)
            wrong = len(self.calls) == 1
            return Solucion(ar="π_{ciudad}(oficina)", sql="SELECT pais FROM oficina" if wrong else "SELECT ciudad FROM oficina")

    art = _artifact()
    art["practicas"][0]["secciones"][0]["ejercicios"].pop(0)
    llm = FirstWrong()
    _run(art, path, llm)
    assert len(llm.calls) == 2
    assert "Column 'pais' could not be resolved" in llm.calls[1][-1][1]
    assert _entries(path)["1.1.b"]["validacion"]["ok"] is True


def test_no_correction_round_when_sql_is_valid(path):
    llm = FakeLLM()
    _run(_artifact(), path, llm)
    assert len(llm.calls) == 2  # one per exercise


def test_non_canonical_translation_triggers_the_correction_round(path):
    class NotExistsFirst(FakeLLM):
        async def ainvoke(self, messages):
            self.calls.append(messages)
            first = len(self.calls) == 1
            sql = ("SELECT codigo FROM oficina o WHERE NOT EXISTS (SELECT 1 FROM oficina x WHERE x.codigo = o.codigo)"
                   if first else "SELECT codigo FROM oficina EXCEPT SELECT codigo FROM oficina WHERE ciudad = 'X'")
            return Solucion(ar="π_{codigo}(oficina) − π_{codigo}(σ_{ciudad='X'}(oficina))", sql=sql)

    art = _artifact()
    art["practicas"][0]["secciones"][0]["ejercicios"].pop(0)
    llm = NotExistsFirst()
    _run(art, path, llm)
    assert len(llm.calls) == 2 and "− se traduce con EXCEPT" in llm.calls[1][-1][1]
    assert _entries(path)["1.1.b"]["forma_canonica"]["ok"] is True


def test_views_extend_the_schema_for_later_statements():
    schema = soluciones.section_schema(DDL)
    ok = "CREATE VIEW A AS SELECT codigo FROM oficina WHERE ciudad = 'X'; SELECT DISTINCT codigo FROM A"
    assert soluciones.validate_sql(ok, schema)["ok"] is True
    bad = "CREATE VIEW A AS SELECT codigo FROM oficina; SELECT ciudad FROM A"
    v = soluciones.validate_sql(bad, schema)
    assert v["ok"] is False and "ciudad" in v["detalle"]


def test_regenerar_no_conformes_only_touches_failing_pending_entries(path):
    con_with = "WITH A AS (SELECT ciudad FROM oficina) SELECT DISTINCT ciudad FROM A"
    _run(_artifact(), path, FakeLLM(sql=con_with))
    entries = _entries(path)
    entries["1.1.a"].update(estado=APROBADA)  # also uses WITH, but approved: must stay
    path.write_text(json.dumps(entries))

    llm = FakeLLM()
    soluciones.generate(_artifact(), path, lambda: llm, modelo="test-model", no_conformes=True)
    after = _entries(path)
    assert [c for c in llm.calls if "EJERCICIO\nCiudades" in c] and not [c for c in llm.calls if "EJERCICIO\nCódigos" in c]
    assert after["1.1.a"]["sql"] == con_with
    assert after["1.1.b"]["sql"] == "SELECT DISTINCT ciudad FROM oficina"

    llm = FakeLLM()
    soluciones.generate(_artifact(), path, lambda: llm, modelo="test-model", no_conformes=True)
    assert llm.calls == []
