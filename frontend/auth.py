"""Autenticación y títulos de conversación. Los datos viven en SQLite (storage/db.py)."""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import db

ABREVIATURAS = {
    "Álgebra Relacional": "A.R.",
    "Algebra Relacional": "A.R.",
    "Bases de Datos": "BD",
    "Base de Datos": "BD",
}


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    return db.authenticate(email, password)


def _abreviar(subject: str) -> str:
    for completo, abreviado in ABREVIATURAS.items():
        if completo.lower() in subject.lower():
            return subject.replace(completo, abreviado)
    return subject


@lru_cache(maxsize=1)
def _llm():
    from tools.llm_config import create_default_llm

    return create_default_llm()


def generate_conversation_title(message: str, subject: str) -> str:
    """Short descriptive title from the first message (LLM); falls back to a generic one."""
    prompt = f"""Generá un título descriptivo (máximo 60 caracteres) para una conversación educativa.

Materia: {_abreviar(subject or '')}
Primer mensaje: {message}

Instrucciones:
1. Si el mensaje menciona un ejercicio específico (ej: "ejercicio 2", "práctica 3", "punto 1.a"), incluilo.
2. Usá abreviaciones: "Álgebra Relacional" → "A.R.", "Bases de Datos" → "BD".
3. Respondé SÓLO con el título, sin comillas ni explicaciones."""
    try:
        title = _llm().invoke(prompt).content.strip().strip('"').strip("'")
    except Exception as e:
        print(f"Error generating conversation title: {e}")
        return f"Consulta sobre {_abreviar(subject or 'la materia')}"
    return title if len(title) <= 60 else title[:57] + "..."
