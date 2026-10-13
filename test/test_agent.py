import asyncio
import json
import uuid
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from agent import prompts
from agent.executor import TutorExecutor
from agent.graph import Clasificacion, TutorAgent, TutorTurn
from agent.leak import leaked_fragment
from course.practices import PracticeRepository
from course.rag import Fragmento
from ingest.soluciones import Solucion

SQL_REF = "SELECT DISTINCT Nombre FROM CLIENTES WHERE Ciudad = 'Buenos Aires'"
AR_REF = "π_{Nombre} (σ_{Ciudad= ′Buenos Aires′} (CLIENTES))"
EJERCICIO = {
    "id": "1.1.a",
    "practica": {"numero": 1, "titulo": "Práctica 1", "descripcion": "d", "objetivos": "o",
                 "criterios_correccion": "Es más grave confundir semántica que sintaxis."},
    "seccion_enunciado": "CLIENTES (NroCliente (clave), Nombre, Ciudad)",
    "enunciado": "Nombre de los clientes de Buenos Aires.",
    "tips": {"practica": ["Pensá en AR primero."], "seccion": [], "ejercicio": ["Alcanza con una selección."]},
    "solucion_ar": [AR_REF],
    "solucion_sql": SQL_REF,
    "apuntes": ["taller.pdf"],
}


class FakePractices:
    def get_exercise(self, exercise_id):
        return EJERCICIO if exercise_id == "1.1.a" else None


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query, k=4, apuntes=None, min_similitud=None):
        self.calls.append({"query": query, "apuntes": apuntes})
        return [Fragmento(texto="σ elige filas que cumplen un predicado.", apunte="taller.pdf", pagina=7, similitud=0.6)]


class FakeLLM:
    def __init__(self, tutor=(), clasificacion="teoria", solucion=None, teoria="La selección filtra filas (taller.pdf, p. 7)."):
        self.calls: list[tuple[str, list]] = []
        self.tutor = list(tutor) or [TutorTurn(calidad="sin_intento", respuesta="¿Qué operación filtra filas?")]
        self.clasificacion, self.solucion, self.teoria = clasificacion, solucion, teoria

    def with_structured_output(self, schema):
        llm = self

        class Runnable:
            async def ainvoke(self, messages):
                llm.calls.append((schema.__name__, messages))
                if schema is TutorTurn:
                    return llm.tutor.pop(0) if len(llm.tutor) > 1 else llm.tutor[0]
                if schema is Clasificacion:
                    return Clasificacion(tipo=llm.clasificacion)
                return llm.solucion

        return Runnable()

    async def ainvoke(self, messages):
        self.calls.append(("texto", messages))
        return AIMessage(self.teoria)

    def kinds(self):
        return [k for k, _ in self.calls]


def _agent(llm, retriever=None):
    return TutorAgent(llm=llm, retriever=retriever or FakeRetriever(), practices=FakePractices())


def _run(agent, message, exercise_id=None, session="s1"):
    async def collect():
        return [c async for c in agent.stream(message, session, exercise_id)]
    return asyncio.run(collect())


def _system_text(messages) -> str:
    return "\n".join(m.content for m in messages if m.type == "system")


def test_selected_exercise_skips_classifier_and_carries_its_context():
    llm, retriever = FakeLLM(), FakeRetriever()
    chunks = _run(_agent(llm, retriever), "No sé por dónde arrancar", "1.1.a")
    assert llm.kinds() == ["TutorTurn"]
    assert retriever.calls == [{"query": "No sé por dónde arrancar", "apuntes": ["taller.pdf"]}]
    contexto = _system_text(llm.calls[0][1])
    for esperado in ("Es más grave confundir semántica", "Alcanza con una selección.", "CONFIDENCIAL", SQL_REF,
                     "[taller.pdf, p. 7]", "doble NOT EXISTS"):
        assert esperado in contexto
    final = chunks[-1]
    assert final["is_task_complete"] and final["content"] == "¿Qué operación filtra filas?"
    assert final["structured_response"]["modo"] == "ejercicio"
    assert final["structured_response"]["analisis"] == {"calidad": "sin_intento", "gaps": []}
    assert final["structured_response"]["fuentes"] == ["taller.pdf, p. 7"]
    assert [c["content"] for c in chunks[:-1]] == ["Buscando en los apuntes…", "Analizando tu consulta…"]


def test_leaked_solution_is_rewritten():
    llm = FakeLLM(tutor=[
        TutorTurn(calidad="sin_intento", respuesta=f"Probá con:\n```sql\n{SQL_REF};\n```"),
        TutorTurn(calidad="sin_intento", respuesta="¿Qué operador elige filas según una condición?"),
    ])
    final = _run(_agent(llm), "dame la respuesta", "1.1.a")[-1]
    assert llm.kinds() == ["TutorTurn", "TutorTurn"]
    assert prompts.REESCRITURA.split("(")[0] in llm.calls[1][1][-1].content
    assert final["content"] == "¿Qué operador elige filas según una condición?"
    assert final["structured_response"]["filtracion_corregida"] is True


def test_persistent_leak_falls_back_to_a_safe_answer():
    llm = FakeLLM(tutor=[TutorTurn(calidad="sin_intento", respuesta=f"La respuesta es {AR_REF}")])
    final = _run(_agent(llm), "dame la respuesta", "1.1.a")[-1]
    assert final["content"] == prompts.RESPUESTA_SEGURA


def test_repeating_the_students_correct_attempt_is_not_a_leak():
    llm = FakeLLM(tutor=[TutorTurn(calidad="correcta", respuesta=f"¡Bien! `{SQL_REF}` es correcto. ¿Cuál es su AR?")])
    final = _run(_agent(llm), f"Mi solución: {SQL_REF}", "1.1.a")[-1]
    assert llm.kinds() == ["TutorTurn"] and final["structured_response"]["filtracion_corregida"] is False


def test_free_theory_question_searches_all_notes_and_answers_directly():
    llm, retriever = FakeLLM(clasificacion="teoria"), FakeRetriever()
    final = _run(_agent(llm, retriever), "¿Qué es una selección?")[-1]
    assert llm.kinds() == ["Clasificacion", "texto"]
    assert retriever.calls[0]["apuntes"] is None
    assert final["content"] == "La selección filtra filas (taller.pdf, p. 7)." and final["structured_response"]["modo"] == "teoria"


def test_own_exercise_is_solved_privately_once_and_followed_up():
    sol = Solucion(ar="π_{a}(R)", sql="SELECT DISTINCT a FROM R")
    llm = FakeLLM(clasificacion="ejercicio_nuevo", solucion=sol)
    agent = _agent(llm)
    chunks = _run(agent, "Tengo R(a, b): quiero los valores de a")
    assert llm.kinds() == ["Clasificacion", "Solucion", "TutorTurn"]
    assert chunks[0]["content"] == "Resolviendo el ejercicio para poder orientarte…"
    assert "SELECT DISTINCT a FROM R" in _system_text(llm.calls[2][1])
    assert chunks[-1]["structured_response"]["modo"] == "ejercicio_propio"

    llm.calls.clear()
    llm.clasificacion = "seguimiento_ejercicio"
    _run(agent, "¿Y si uso proyección?")
    assert llm.kinds() == ["Clasificacion", "TutorTurn"]
    assert "SELECT DISTINCT a FROM R" in _system_text(llm.calls[1][1])


def test_conversation_memory_is_per_session():
    llm = FakeLLM()
    agent = _agent(llm)
    _run(agent, "primer mensaje", "1.1.a", session="a")
    _run(agent, "segundo mensaje", "1.1.a", session="a")
    historial = [m.content for m in llm.calls[-1][1] if m.type != "system"]
    assert historial == ["primer mensaje", "¿Qué operación filtra filas?", "segundo mensaje"]
    _run(agent, "otra sesión", "1.1.a", session="b")
    assert [m.content for m in llm.calls[-1][1] if m.type != "system"] == ["otra sesión"]


def test_unknown_exercise_falls_back_to_free_mode():
    llm = FakeLLM(clasificacion="teoria")
    final = _run(_agent(llm), "hola", "9.9.z")[-1]
    assert llm.kinds()[0] == "Clasificacion" and final["structured_response"]["modo"] == "teoria"


def test_executor_without_guardrails_passes_the_exercise():
    llm = FakeLLM()
    executor = TutorExecutor(agent=_agent(llm), enable_guardrails=False)

    async def collect():
        return [c async for c in executor.stream("ayuda", str(uuid.uuid4()), exercise_id="1.1.a")]

    assert asyncio.run(collect())[-1]["structured_response"]["exercise_id"] == "1.1.a"


@pytest.mark.parametrize("respuesta, filtra", [
    ("Pensá qué hace σ_{Ciudad=...} sobre CLIENTES.", False),
    ("Fijate: SELECT DISTINCT Nombre FROM CLIENTES", False),
    (f"```sql\n{SQL_REF.lower()};  -- listo\n```", True),
    (f"**{AR_REF}**", True),
    ("Paso 1: A ← π_{codigo_cliente,codigo_producto}(pedido ⋈ detalle_pedido)", True),
])
def test_leak_detection(respuesta, filtra):
    ar = [AR_REF, "A ← π_{codigo_cliente,codigo_producto}(pedido ⋈ detalle_pedido)\nC ← A ÷ B"]
    assert (leaked_fragment(respuesta, ar, SQL_REF) is not None) == filtra


def test_practice_repository_exercise_context(tmp_path: Path):
    path = tmp_path / "practicas.json"
    path.write_text(json.dumps({"materia": {"nombre": "BD", "unidades": []}, "practicas": [{
        "numero": "Extra", "titulo": "Extra", "descripcion": None, "objetivos": None, "criterios_correccion": "c",
        "teoria_relacionada": [], "tips": ["tp"], "apuntes_relacionados": ["a.pdf"],
        "secciones": [{"numero": "1", "enunciado": "S", "tips": [], "ejercicios": [{
            "numero": "a", "enunciado": "E", "respuestas": [], "tips": [], "deducir_respuesta": False,
            "solucion": {"ar": ["π_{x}(R)"], "sql": "SELECT DISTINCT x FROM R"}}]}],
    }]}))
    repo = PracticeRepository(path)
    ej = repo.get_exercise("Extra.1.a")
    assert ej["solucion_ar"] == ["π_{x}(R)"] and ej["solucion_sql"] == "SELECT DISTINCT x FROM R"
    assert ej["apuntes"] == ["a.pdf"] and ej["tips"]["practica"] == ["tp"]
    assert repo.get_exercise("Extra.1.zz") is None and repo.get_exercise("mal") is None


@pytest.mark.skipif(not Path("artifacts/practicas.json").exists(), reason="requiere python -m ingest")
def test_practices_tree_never_exposes_solutions():
    repo = PracticeRepository()  # real artifacts/practicas.json, built by `python -m ingest`
    tree = repo.tree()
    texto = json.dumps(tree, ensure_ascii=False)
    for clave in ("respuestas", "solucion", "tips", "criterios", "sql"):
        assert f'"{clave}' not in texto
    ejercicios = [e for p in tree for s in p["secciones"] for e in s["ejercicios"]]
    assert all(repo.get_exercise(e["id"]) for e in ejercicios)
    assert [p["numero"] for p in tree][-1] == "Extra"
