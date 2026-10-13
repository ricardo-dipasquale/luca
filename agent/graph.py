"""Agente tutor único (LangGraph).

Modo según la UI: con un ejercicio seleccionado se acompaña ese ejercicio; sin ejercicio, un clasificador
distingue teoría de un ejercicio propio del alumno (cuya solución de referencia se deduce en privado).
"""

import logging
from typing import Annotated, Any, AsyncIterator, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agent import prompts
from agent.leak import leaked_fragment
from ingest.soluciones import Solucion

logger = logging.getLogger(__name__)

HISTORIAL = 10
FRAGMENTOS = 4


class TutorTurn(BaseModel):
    calidad: Literal["correcta", "parcial", "incorrecta", "sin_intento", "consulta_teorica"]
    gaps: list[str] = Field(default_factory=list, description="Problemas concretos del intento (vacío si no hay)")
    respuesta: str = Field(description="Mensaje para el alumno")


class Clasificacion(BaseModel):
    tipo: Literal["teoria", "ejercicio_nuevo", "seguimiento_ejercicio"]


class TutorState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    exercise_id: Optional[str]
    modo: str
    ejercicio: Optional[dict]
    referencia: Optional[dict]  # solución deducida de un ejercicio propio; persiste entre turnos
    fragmentos: list[dict]
    analisis: Optional[dict]
    filtracion_corregida: bool
    respuesta: str


# Progress shown to the student when a node finishes, announcing what comes next.
SIGUIENTE_PASO = {"deducir": "Buscando en los apuntes…", "buscar": "Analizando tu consulta…"}


def _ultimo_mensaje(state: TutorState) -> str:
    return next(m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage))


def _mensajes_del_alumno(state: TutorState) -> str:
    return "\n".join(m.content for m in state["messages"] if isinstance(m, HumanMessage))


def _historial(state: TutorState) -> list[AnyMessage]:
    return state["messages"][-HISTORIAL:]


def build_graph(llm: Any, retriever: Any, practices: Any, checkpointer: Any = None):
    tutor_llm = llm.with_structured_output(TutorTurn)
    clasificador = llm.with_structured_output(Clasificacion)
    deductor = llm.with_structured_output(Solucion)

    async def preparar(state: TutorState) -> dict:
        if state.get("exercise_id"):
            ejercicio = practices.get_exercise(state["exercise_id"])
            if ejercicio:
                return {"modo": "ejercicio", "ejercicio": ejercicio}
            logger.warning(f"Ejercicio {state['exercise_id']} inexistente; se trata como consulta libre")
        tipo = (await clasificador.ainvoke(
            [SystemMessage(prompts.CLASIFICADOR_SYSTEM), *_historial(state)]
        )).tipo
        if tipo == "seguimiento_ejercicio" and state.get("referencia"):
            return {"modo": "ejercicio_propio", "ejercicio": None}
        if tipo in ("ejercicio_nuevo", "seguimiento_ejercicio"):
            return {"modo": "deducir", "ejercicio": None}
        return {"modo": "teoria", "ejercicio": None}

    async def deducir(state: TutorState) -> dict:
        sol = await deductor.ainvoke([SystemMessage(prompts.DEDUCCION_SYSTEM), *_historial(state)])
        return {"modo": "ejercicio_propio", "referencia": {"ar": [sol.ar] if sol.ar else [], "sql": sol.sql or None}}

    async def buscar(state: TutorState) -> dict:
        apuntes = state["ejercicio"]["apuntes"] if state.get("ejercicio") else None
        resultados = retriever.search(_ultimo_mensaje(state), k=FRAGMENTOS, apuntes=apuntes or None)
        return {"fragmentos": [
            {"texto": f.texto, "apunte": f.apunte, "pagina": f.pagina, "similitud": round(f.similitud, 3)}
            for f in resultados
        ]}

    def _referencia(state: TutorState) -> tuple[list[str], Optional[str]]:
        if state.get("ejercicio"):
            return state["ejercicio"]["solucion_ar"], state["ejercicio"]["solucion_sql"]
        ref = state.get("referencia") or {}
        return ref.get("ar", []), ref.get("sql")

    async def tutor(state: TutorState) -> dict:
        ar, sql = _referencia(state)
        contexto = (
            prompts.contexto_ejercicio(state["ejercicio"], ar, sql) if state.get("ejercicio")
            else prompts.contexto_ejercicio_propio(ar, sql)
        )
        mensajes = [
            SystemMessage(prompts.TUTOR_SYSTEM),
            SystemMessage(contexto + "\n\n" + prompts.contexto_apuntes(state.get("fragmentos", []))),
            *_historial(state),
        ]
        turno = await tutor_llm.ainvoke(mensajes)
        corregida = False
        if fragmento := leaked_fragment(turno.respuesta, ar, sql, _mensajes_del_alumno(state)):
            logger.warning(f"La respuesta filtraba la solución ({fragmento[:60]!r}); se reescribe")
            corregida = True
            turno = await tutor_llm.ainvoke(mensajes + [
                AIMessage(turno.respuesta), HumanMessage(prompts.REESCRITURA.format(fragmento=fragmento)),
            ])
            if leaked_fragment(turno.respuesta, ar, sql, _mensajes_del_alumno(state)):
                logger.error("La reescritura seguía filtrando la solución; se usa una respuesta segura")
                turno = TutorTurn(calidad=turno.calidad, gaps=turno.gaps, respuesta=prompts.RESPUESTA_SEGURA)
        return {
            "analisis": {"calidad": turno.calidad, "gaps": turno.gaps},
            "filtracion_corregida": corregida,
            "respuesta": turno.respuesta,
            "messages": [AIMessage(turno.respuesta)],
        }

    async def teoria(state: TutorState) -> dict:
        respuesta = await llm.ainvoke([
            SystemMessage(prompts.TEORIA_SYSTEM),
            SystemMessage(prompts.contexto_apuntes(state.get("fragmentos", []))),
            *_historial(state),
        ])
        return {"analisis": None, "respuesta": respuesta.content, "messages": [AIMessage(respuesta.content)]}

    graph = StateGraph(TutorState)
    for nombre, nodo in [("preparar", preparar), ("deducir", deducir), ("buscar", buscar), ("tutor", tutor), ("teoria", teoria)]:
        graph.add_node(nombre, nodo)
    graph.add_edge(START, "preparar")
    graph.add_conditional_edges("preparar", lambda s: "deducir" if s["modo"] == "deducir" else "buscar")
    graph.add_edge("deducir", "buscar")
    graph.add_conditional_edges("buscar", lambda s: "teoria" if s["modo"] == "teoria" else "tutor")
    graph.add_edge("tutor", END)
    graph.add_edge("teoria", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


class TutorAgent:
    def __init__(self, llm: Any = None, retriever: Any = None, practices: Any = None, checkpointer: Any = None):
        if llm is None:
            from tools.llm_config import create_default_llm
            llm = create_default_llm()
        if retriever is None:
            from course.rag import get_apuntes_retriever
            retriever = get_apuntes_retriever()
        if practices is None:
            from course.practices import get_practice_repository
            practices = get_practice_repository()
        self.graph = build_graph(llm, retriever, practices, checkpointer)

    async def stream(self, message: str, session_id: str, exercise_id: Optional[str] = None) -> AsyncIterator[dict]:
        entrada = {
            "messages": [HumanMessage(message)], "exercise_id": exercise_id,
            "fragmentos": [], "analisis": None, "filtracion_corregida": False, "respuesta": "",
        }
        config = {"configurable": {"thread_id": session_id}}
        async for update in self.graph.astream(entrada, config, stream_mode="updates"):
            for nodo, cambios in update.items():
                if nodo == "preparar":
                    paso = ("Resolviendo el ejercicio para poder orientarte…" if (cambios or {}).get("modo") == "deducir"
                            else "Buscando en los apuntes…")
                else:
                    paso = SIGUIENTE_PASO.get(nodo)
                if paso:
                    yield {"is_task_complete": False, "require_user_input": False, "content": paso}
        estado = (await self.graph.aget_state(config)).values
        yield {
            "is_task_complete": True,
            "require_user_input": True,
            "content": estado["respuesta"],
            "structured_response": {
                "modo": estado.get("modo"),
                "exercise_id": exercise_id,
                "analisis": estado.get("analisis"),
                "filtracion_corregida": estado.get("filtracion_corregida", False),
                "fuentes": [f"{f['apunte']}, p. {f['pagina']}" for f in estado.get("fragmentos", [])],
            },
        }
