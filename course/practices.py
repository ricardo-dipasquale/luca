"""Read-only access to artifacts/practicas.json, with the same return shapes as kg.KGQueryInterface."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = PROJECT_ROOT / "artifacts" / "practicas.json"


class PracticeRepository:
    def __init__(self, path: Path = DEFAULT_PATH):
        if not path.exists():
            raise FileNotFoundError(
                f"No existe {path}. Generalo con: python -m ingest --only practicas"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        self._materia = data["materia"]
        self._practicas = {p["numero"]: p for p in data["practicas"]}
        self._known_topics = {t["descripcion"] for u in self._materia["unidades"] for t in u["temas"]}

    def _seccion(self, practice_number: int, section_number: str) -> Optional[dict]:
        practica = self._practicas.get(practice_number)
        if practica is None:
            return None
        return next((s for s in practica["secciones"] if s["numero"] == str(section_number)), None)

    def _ejercicio(self, practice_number: int, section_number: str, exercise_number: str) -> Optional[dict]:
        seccion = self._seccion(practice_number, section_number)
        if seccion is None:
            return None
        return next((e for e in seccion["ejercicios"] if e["numero"] == str(exercise_number)), None)

    def tree(self) -> List[Dict[str, Any]]:
        """Practices → sections → exercises with statements only, for the student's side panel.

        Never includes answers, tips or reference solutions: this goes to the browser.
        """
        return [
            {
                "numero": p["numero"],
                "titulo": p["titulo"],
                "secciones": [
                    {
                        "numero": s["numero"],
                        "enunciado": s["enunciado"],
                        "ejercicios": [
                            {"id": f"{p['numero']}.{s['numero']}.{e['numero']}", "numero": e["numero"], "enunciado": e["enunciado"]}
                            for e in s["ejercicios"]
                        ],
                    }
                    for s in p["secciones"]
                ],
            }
            for p in self._practicas.values()
        ]

    def get_exercise(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Everything the tutor needs about one exercise, by id "práctica.sección.ejercicio" (e.g. "4.1.12")."""
        try:
            practica_id, seccion_id, ejercicio_id = exercise_id.split(".", 2)
        except ValueError:
            return None
        practica = self._practicas.get(int(practica_id) if practica_id.isdigit() else practica_id)
        if practica is None:
            return None
        seccion = next((s for s in practica["secciones"] if s["numero"] == seccion_id), None)
        ejercicio = seccion and next((e for e in seccion["ejercicios"] if e["numero"] == ejercicio_id), None)
        if not ejercicio:
            return None
        solucion = ejercicio.get("solucion") or {}
        return {
            "id": exercise_id,
            "practica": {k: practica.get(k) for k in ("numero", "titulo", "descripcion", "objetivos", "criterios_correccion")},
            "seccion_enunciado": seccion["enunciado"],
            "enunciado": ejercicio["enunciado"],
            "tips": {"practica": practica["tips"], "seccion": seccion["tips"], "ejercicio": ejercicio["tips"]},
            "solucion_ar": solucion.get("ar") or ejercicio["respuestas"],
            "solucion_sql": solucion.get("sql"),
            "apuntes": practica.get("apuntes_relacionados", []),
        }

    def get_subjects(self) -> List[Dict[str, Any]]:
        return [{"name": self._materia["nombre"], "nombre": self._materia["nombre"]}]

    def get_practice_details(self, practice_number: int) -> Optional[Dict[str, Any]]:
        p = self._practicas.get(practice_number)
        if p is None:
            return None
        topics = [t for t in p["teoria_relacionada"] if t in self._known_topics]
        return {
            "number": p["numero"],
            "name": p["titulo"],
            "description": p["descripcion"],
            "objectives": p["objetivos"],
            "criteriocorreccion": p["criterios_correccion"],
            "topics": topics,
            "subjects": [self._materia["nombre"]] if topics else [],
        }

    def get_exercise_details(
        self, practice_number: int, section_number: str, exercise_identifier: str
    ) -> Optional[Dict[str, Any]]:
        e = self._ejercicio(practice_number, section_number, exercise_identifier)
        if e is None:
            return None
        s = self._seccion(practice_number, section_number)
        return {
            "practice_number": practice_number,
            "practice_name": self._practicas[practice_number]["titulo"],
            "section_number": s["numero"],
            "section_statement": s["enunciado"],
            "exercise_number": e["numero"],
            "exercise_statement": e["enunciado"],
            "answers": list(e["respuestas"]),
        }

    def get_practice_tips(
        self, practice_number: int, section_number: str = None, exercise_number: str = None
    ) -> List[Dict[str, Any]]:
        p = self._practicas.get(practice_number)
        if p is None:
            return []
        tips = [_tip("practice", None, None, t) for t in p["tips"]]
        if section_number is not None:
            s = self._seccion(practice_number, section_number)
            if s is not None:
                tips += [_tip("section", s["numero"], None, t) for t in s["tips"]]
                if exercise_number is not None:
                    e = self._ejercicio(practice_number, section_number, exercise_number)
                    if e is not None:
                        tips += [_tip("exercise", s["numero"], e["numero"], t) for t in e["tips"]]
        return tips


def _tip(level: str, section: Optional[str], exercise: Optional[str], text: str) -> Dict[str, Any]:
    return {"level": level, "section_number": section, "exercise_number": exercise, "tip_text": text}


@lru_cache(maxsize=1)
def get_practice_repository() -> PracticeRepository:
    return PracticeRepository(Path(os.environ.get("PRACTICAS_PATH", DEFAULT_PATH)))
