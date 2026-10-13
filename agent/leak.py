"""¿La respuesta al alumno revela la solución de referencia (AR o SQL)? Determinista, sin LLM."""

import re
from difflib import SequenceMatcher

MIN_FRAGMENT = 30  # shorter pieces (e.g. "SELECT DISTINCT nombre") are normal in a hint
MATCH_RATIO = 0.8


def _norm(text: str) -> str:
    text = re.sub(r"--[^\n]*", " ", text)  # SQL comments
    text = re.sub(r"[`*_]", "", text)  # markdown
    return re.sub(r"\s+", " ", text.lower()).strip(" ;")


def _fragments(ar: list[str], sql: str | None) -> list[str]:
    piezas = [s for s in (sql or "").split(";")]
    for expr in ar:
        # Each AR step on its own; "A ← expr" counts by its expression.
        piezas += [re.sub(r"^\s*\w+\s*(←|=)\s*", "", line) for line in expr.splitlines()]
    return [p for p in (_norm(p) for p in piezas) if len(p) >= MIN_FRAGMENT]


def _contains(texto: str, frag: str) -> bool:
    match = SequenceMatcher(None, frag, texto, autojunk=False).find_longest_match(0, len(frag), 0, len(texto))
    return match.size >= MATCH_RATIO * len(frag)


def leaked_fragment(respuesta: str, ar: list[str], sql: str | None, del_alumno: str = "") -> str | None:
    """The reference fragment the answer reproduces (≥80% of it, contiguous), or None.

    Fragments the student already wrote (del_alumno) don't count: repeating a correct attempt is fine.
    """
    texto, alumno = _norm(respuesta), _norm(del_alumno)
    for frag in _fragments(ar, sql):
        if _contains(texto, frag) and not _contains(alumno, frag):
            return frag
    return None
